"""
Orchestrates the caseworker's morning sequence:
  1. Read the overnight referrals.
  2. For each, pull the resident's history.
  3. Draft a triage note -- or, if the requested action is restricted,
     escalate instead and move on to the next referral (policy 4.3).

Deliberately not "clever": the sequence is fixed and known, per the
problem statement ("this is not a problem about deciding what to do").
The judgement is entirely in step 3's branch: permitted vs escalate.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_engine import PolicyEngine, PERMITTED
from history_client import HistoryClient, HistoryClientError
from triage import draft_triage_note
from escalation import EscalationQueue
from trace import TraceLogger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
SERVICES_DIR = os.path.join(ROOT, "services")
OUTPUT_DIR = os.path.join(ROOT, "output")
HISTORY_PORT = 8083
HISTORY_URL = f"http://127.0.0.1:{HISTORY_PORT}"


def wait_for_service(url, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            return True
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    return False


def start_history_service():
    """Starts the mock history API as a subprocess so the whole demo
    is one command. Returns the Popen handle so it can be torn down
    at the end of the run."""
    script = os.path.join(SERVICES_DIR, "history_service.py")
    proc = subprocess.Popen(
        [sys.executable, script, "--port", str(HISTORY_PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if not wait_for_service(HISTORY_URL):
        proc.terminate()
        raise RuntimeError("Resident History API did not come up in time.")
    return proc


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    triage_dir = os.path.join(OUTPUT_DIR, "triage_notes")
    os.makedirs(triage_dir, exist_ok=True)

    trace = TraceLogger(OUTPUT_DIR)
    escalations = EscalationQueue(OUTPUT_DIR)
    policy = PolicyEngine()

    print(f"Starting Resident History API on {HISTORY_URL} ...")
    service_proc = start_history_service()
    trace.log(None, "service_start", None, f"Resident History API up at {HISTORY_URL}")

    client = HistoryClient(base_url=HISTORY_URL)

    with open(os.path.join(DATA_DIR, "referral-queue.json"), encoding="utf-8") as f:
        referrals = json.load(f)

    trace.log(None, "queue_loaded", "authority-policy.md 2.1",
              f"Loaded {len(referrals)} referrals from overnight queue.")

    drafted, escalated, failed = 0, 0, 0

    try:
        for referral in referrals:
            rid = referral["referral_id"]
            trace.log(rid, "referral_read", "2.1", referral["summary"])

            history = None
            try:
                history = client.full_record(referral["resident_ref"])
                trace.log(rid, "history_fetched", "2.2",
                          f"Retrieved history for {referral['resident_ref']}.")
            except HistoryClientError as e:
                trace.log(rid, "history_fetch_failed", "2.2", str(e))
                # Partial-failure handling: this referral couldn't be
                # fully triaged, but that must not stop the others.
                failed += 1
                continue

            classification = policy.classify(referral["requested_action"])
            trace.log(
                rid, "classified", classification.policy_basis,
                f"'{referral['requested_action']}' -> {classification.status} "
                f"({classification.action_type}). {classification.note}"
            )

            if classification.status == PERMITTED:
                note = draft_triage_note(referral, history, classification)
                note_path = os.path.join(triage_dir, f"{rid}.md")
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(note)
                trace.log(rid, "triage_note_drafted", classification.policy_basis,
                          f"Note written to output/triage_notes/{rid}.md (proposal only, per 2.4).")
                drafted += 1
            else:
                record = escalations.escalate(referral, history, classification)
                trace.log(
                    rid, "ESCALATED", classification.policy_basis,
                    f"Not actioned. {classification.note} "
                    f"Recorded to output/escalations.jsonl for supervisor decision."
                )
                escalated += 1
    finally:
        service_proc.terminate()
        service_proc.wait(timeout=5)
        trace.log(None, "service_stop", None, "Resident History API stopped.")

    summary = (
        f"\nRun complete. {len(referrals)} referrals processed: "
        f"{drafted} triaged, {escalated} escalated, {failed} failed (history unavailable)."
    )
    trace.log(None, "run_complete", None, summary.strip())
    print(summary)
    print(f"Triage notes:  {triage_dir}/")
    print(f"Escalations:   {os.path.join(OUTPUT_DIR, 'escalations.jsonl')}")
    print(f"Full trace:    {os.path.join(OUTPUT_DIR, 'execution_trace.txt')}")


if __name__ == "__main__":
    run()

"""
Orchestrates the caseworker's morning sequence.

ACA-2026/2 changes the decision point after history retrieval:

1. Read referral.
2. Retrieve history.
3. Determine household composition from Department data.
4. Classify the requested action under ACA-2026/1.
5. If the requested action itself is restricted -> section-4 escalation.
6. Otherwise, if ACA-2026/2 section 3.9 applies -> ordinary caseworker hand-off.
7. Otherwise -> draft the permitted triage note.

The distinction between escalation and hand-off is deliberate:
- escalation = a restricted action needs a supervisor decision;
- hand-off = ordinary casework that a person must perform.

The policy engine reloads its policy data for every referral, so an amendment
can affect referrals still waiting in a part-way-through run.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_engine import PolicyEngine, PERMITTED
from history_client import HistoryClient, HistoryClientError
from household_rules import determine_household_composition
from triage import draft_triage_note
from escalation import EscalationQueue
from handoff import CaseworkerHandoffQueue
from trace import TraceLogger
from briefing import build_briefing

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
    script = os.path.join(SERVICES_DIR, "history_service.py")
    proc = subprocess.Popen(
        [sys.executable, script, "--port", str(HISTORY_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_service(HISTORY_URL):
        proc.terminate()
        raise RuntimeError("Resident History API did not come up in time.")
    return proc


def _as_of_date(referral):
    """
    The amendment does not specify an age-calculation clock.

    We use the referral's received date as the deterministic casework
    reference date. This avoids the demo changing behavior merely because
    the machine's current date changes.
    """
    return date.fromisoformat(referral["received_at"][:10])


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    triage_dir = os.path.join(OUTPUT_DIR, "triage_notes")
    os.makedirs(triage_dir, exist_ok=True)

    trace = TraceLogger(OUTPUT_DIR)
    escalations = EscalationQueue(OUTPUT_DIR)
    handoffs = CaseworkerHandoffQueue(OUTPUT_DIR)
    policy = PolicyEngine()

    print(f"Starting Resident History API on {HISTORY_URL} ...")
    service_proc = start_history_service()
    trace.log(
        None,
        "service_start",
        None,
        f"Resident History API up at {HISTORY_URL}",
    )

    client = HistoryClient(base_url=HISTORY_URL)

    with open(
        os.path.join(DATA_DIR, "referral-queue.json"),
        encoding="utf-8",
    ) as f:
        referrals = json.load(f)

    trace.log(
        None,
        "queue_loaded",
        "authority-policy.md 2.1",
        f"Loaded {len(referrals)} referrals from overnight queue.",
    )

    outcomes = {
        "drafted": [],
        "escalated": [],
        "handed_off": [],
    }

    try:
        for referral in referrals:
            rid = referral["referral_id"]

            trace.log(
                rid,
                "referral_read",
                "2.1",
                referral["summary"],
            )

            # ------------------------------------------------------
            # STEP 1: Retrieve history.
            # ------------------------------------------------------
            history = None

            try:
                history = client.full_record(
                    referral["resident_ref"]
                )

                trace.log(
                    rid,
                    "history_fetched",
                    "2.2",
                    f"Retrieved history for {referral['resident_ref']}.",
                )

            except HistoryClientError as e:
                trace.log(
                    rid,
                    "history_fetch_failed",
                    "2.2",
                    str(e),
                )

                # ACA-2026/2 says 3.9 applies if household composition
                # cannot be established. Therefore this is a HAND-OFF,
                # not an ordinary failure and not an escalation.
                household = determine_household_composition(
                    None,
                    _as_of_date(referral),
                )

                classification = policy.classify(
                    referral["requested_action"]
                )

                # If the requested action itself is restricted, section 4
                # still requires escalation. Otherwise 3.9 requires hand-off.
                if classification.status != PERMITTED:
                    escalations.escalate(
                        referral,
                        None,
                        classification,
                    )

                    trace.log(
                        rid,
                        "ESCALATED",
                        classification.policy_basis,
                        (
                            "Restricted requested action. "
                            "History was unavailable; the referral was "
                            "not actioned."
                        ),
                    )

                    outcomes["escalated"].append(
                        (referral, classification)
                    )

                else:
                    handoffs.handoff(
                        referral,
                        None,
                        household,
                        classification,
                        household["reason"],
                    )

                    trace.log(
                        rid,
                        "CASEWORKER_HANDOFF",
                        "3.9",
                        (
                            "Household composition could not be established. "
                            "Per ACA-2026/2 section 5.2, the hand-off condition "
                            "is treated as applying. No triage note was drafted."
                        ),
                    )

                    outcomes["handed_off"].append(
                        (referral, classification)
                    )

                continue

            # ------------------------------------------------------
            # STEP 2: Determine household composition.
            # ------------------------------------------------------
            household = determine_household_composition(
                history,
                _as_of_date(referral),
            )

            trace.log(
                rid,
                "household_determined",
                "ACA-2026/2 5.1-5.2",
                (
                    f"{household['status']}: "
                    f"{household['reason']}"
                ),
            )

            if household["children"]:
                names = ", ".join(
                    child["name"]
                    for child in household["children"]
                )

                trace.log(
                    rid,
                    "child_household_identified",
                    "3.9",
                    f"Household includes person(s) under 18: {names}.",
                )

            # ------------------------------------------------------
            # STEP 3: Classify requested action.
            # ------------------------------------------------------
            classification = policy.classify(
                referral["requested_action"]
            )

            trace.log(
                rid,
                "classified",
                classification.policy_basis,
                (
                    f"'{referral['requested_action']}' -> "
                    f"{classification.status} "
                    f"({classification.action_type}). "
                    f"{classification.note}"
                ),
            )

            # ------------------------------------------------------
            # STEP 4: Existing section-3 restrictions still require
            # escalation.
            # ------------------------------------------------------
            if classification.status != PERMITTED:

                escalations.escalate(
                    referral,
                    history,
                    classification,
                )

                trace.log(
                    rid,
                    "ESCALATED",
                    classification.policy_basis,
                    (
                        "Requested action is restricted under ACA-2026/1. "
                        "The referral is a section-4 escalation. "
                        "No action was taken."
                    ),
                )

                outcomes["escalated"].append(
                    (referral, classification)
                )

                continue

            # ------------------------------------------------------
            # STEP 5: ACA-2026/2 section 3.9.
            #
            # This MUST happen before draft_triage_note().
            # ------------------------------------------------------
            child_rule = policy.child_household_rule()

            child_rule_applies = (
                child_rule is not None
                and child_rule.get("enabled", False)
                and (
                    household["has_person_under_18"] is True
                    or (
                        household["has_person_under_18"] is None
                        and child_rule.get(
                            "unknown_household_also_applies",
                            True,
                        )
                    )
                )
            )

            if child_rule_applies:

                handoffs.handoff(
                    referral,
                    history,
                    household,
                    classification,
                    child_rule["note"],
                )

                trace.log(
                    rid,
                    "CASEWORKER_HANDOFF",
                    child_rule["policy_basis"],
                    (
                        "ACA-2026/2 section 3.9 applies. "
                        "The assistant must not draft a triage note. "
                        "Work already completed was preserved for the "
                        "caseworker. This is a hand-off, not an escalation."
                    ),
                )

                outcomes["handed_off"].append(
                    (referral, classification)
                )

                continue

            # ------------------------------------------------------
            # STEP 6: Only now may the assistant draft a note.
            # ------------------------------------------------------
            note = draft_triage_note(
                referral,
                history,
                classification,
            )

            note_path = os.path.join(
                triage_dir,
                f"{rid}.md",
            )

            with open(
                note_path,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(note)

            trace.log(
                rid,
                "triage_note_drafted",
                classification.policy_basis,
                (
                    f"Note written to "
                    f"output/triage_notes/{rid}.md "
                    f"(proposal only, per 2.4)."
                ),
            )

            outcomes["drafted"].append(
                (referral, classification)
            )

    finally:
        service_proc.terminate()
        service_proc.wait(timeout=5)

        trace.log(
            None,
            "service_stop",
            None,
            "Resident History API stopped.",
        )

    drafted = len(outcomes["drafted"])
    escalated = len(outcomes["escalated"])
    handed_off = len(outcomes["handed_off"])

    briefing_text = build_briefing(outcomes)

    briefing_path = os.path.join(
        OUTPUT_DIR,
        "MORNING_BRIEFING.md",
    )

    with open(
        briefing_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(briefing_text)

    summary = (
        f"\nRun complete. {len(referrals)} referrals processed: "
        f"{drafted} triaged, "
        f"{handed_off} handed to a caseworker, "
        f"{escalated} escalated."
    )

    trace.log(
        None,
        "run_complete",
        None,
        summary.strip(),
    )

    print(summary)
    print(f"\n{briefing_text}\n")
    print(f"Morning briefing: {briefing_path}")
    print(f"Triage notes:     {triage_dir}/")
    print(
        "Caseworker handoffs: "
        f"{os.path.join(OUTPUT_DIR, 'caseworker_handoffs')}/"
    )
    print(
        "Escalations:      "
        f"{os.path.join(OUTPUT_DIR, 'escalations.jsonl')}"
    )
    print(
        "Full trace:       "
        f"{os.path.join(OUTPUT_DIR, 'execution_trace.txt')}"
    )


if __name__ == "__main__":
    run()

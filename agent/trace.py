"""
Execution trace logger.

Policy ACA-2026/1, section 5:
  5.1 Every action must be recorded so a supervisor can reconstruct,
      after the fact, what was done, in what order, on what
      information, and what was declined.
  5.2 A record showing only the output, not the steps that produced
      it, does not satisfy 5.1.

So every entry records: the step taken, the referral it concerns, the
information it was based on, and (where relevant) the policy basis for
a decision -- not just a final "note: ..." blob.

Writes two files:
  - execution_trace.jsonl   machine-readable, one JSON object per line
  - execution_trace.txt     human-readable, for a supervisor to skim
"""
import json
import os
from datetime import datetime, timezone


class TraceLogger:
    def __init__(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self.jsonl_path = os.path.join(output_dir, "execution_trace.jsonl")
        self.txt_path = os.path.join(output_dir, "execution_trace.txt")
        # Fresh run each time -- overwrite, don't append to a stale log.
        open(self.jsonl_path, "w", encoding="utf-8").close()
        open(self.txt_path, "w", encoding="utf-8").close()

    def log(self, referral_id, step, basis, detail):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "referral_id": referral_id,
            "step": step,
            "basis": basis,
            "detail": detail,
        }
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        with open(self.txt_path, "a", encoding="utf-8") as f:
            f.write(f"[{entry['timestamp']}] {referral_id or '-':<14} {step:<28} "
                     f"(basis: {basis or '-'})\n    {detail}\n")
        # Also echo to stdout so `python3 main.py` alone shows the run live.
        print(f"  [{step}] {referral_id or '-'}: {detail}")

"""
Escalation queue.

Policy 4.1: where a referral requests a restricted action, the agent
must not perform it, must not perform a partial/preparatory version of
it, and must escalate.
Policy 4.2: an escalation must identify the referral, state which
provision of section 3 applies, and carry enough context for a
supervisor to act without re-reading the case from the start.
Policy 4.3: escalating one referral must not stop the others being
processed.

This module is the entire "approval gate." It does not contain, call,
or import anything capable of suspending an award, changing a payment,
sending a communication, or any other section-3 action -- those
functions simply do not exist in this codebase. A restricted referral
can only ever end up here, never partially executed elsewhere.
"""
import json
import os
from datetime import datetime, timezone


class EscalationQueue:
    def __init__(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self.path = os.path.join(output_dir, "escalations.jsonl")
        open(self.path, "w", encoding="utf-8").close()

    def escalate(self, referral, history, classification):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "referral_id": referral["referral_id"],
            "resident_ref": referral["resident_ref"],
            "source": referral["source"],
            "reported_urgency": referral["urgency"],
            "requested_action": referral["requested_action"],
            "summary": referral["summary"],
            "policy_basis": classification.policy_basis,
            "action_type": classification.action_type,
            "reason": classification.note,
            "case_context": {
                "status": history.get("status") if history else "unavailable",
                "benefit_code": history.get("benefit_code") if history else "unavailable",
                "award_monthly": history.get("award_monthly") if history else "unavailable",
            } if history else {"status": "history_unavailable"},
            "status": "AWAITING_SUPERVISOR_DECISION",
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

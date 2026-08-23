"""
Caseworker hand-off for ACA-2026/2 section 3.9.

A hand-off is NOT an escalation.

Escalation means:
    the Department must decide whether a restricted action may happen.

Hand-off means:
    this is ordinary casework, but a person must do the triage-note work.

Therefore this module never writes a triage note and never creates an
escalation record. It preserves the work already completed by the assistant:
the referral, retrieved history, household determination, and action
classification.
"""

import json
import os
from datetime import datetime, timezone


class CaseworkerHandoffQueue:
    def __init__(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        self.jsonl_path = os.path.join(
            output_dir,
            "caseworker_handoffs.jsonl",
        )

        self.notes_dir = os.path.join(
            output_dir,
            "caseworker_handoffs",
        )

        os.makedirs(self.notes_dir, exist_ok=True)
        open(self.jsonl_path, "w", encoding="utf-8").close()

    def handoff(
        self,
        referral,
        history,
        household,
        classification,
        reason,
    ):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "handoff_type": "ORDINARY_CASEWORK_HANDOFF",
            "status": "AWAITING_CASEWORKER_TRIAGE",
            "referral_id": referral["referral_id"],
            "resident_ref": referral["resident_ref"],
            "source": referral["source"],
            "received_at": referral["received_at"],
            "reported_urgency": referral["urgency"],
            "summary": referral["summary"],
            "requested_action": referral["requested_action"],
            "policy_basis": "3.9",
            "reason": reason,
            "classification": {
                "action_type": classification.action_type,
                "policy_basis": classification.policy_basis,
                "note": classification.note,
            },
            "work_already_established": {
                "history_retrieved": history is not None,
                "household_determination": household,
            },
            "children": household.get("children", []),
            "next_step": (
                "Caseworker must perform the triage-note work. "
                "The assistant must not draft the note."
            ),
            "triage_note_created": False,
            "escalation_created": False,
        }

        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # This is a hand-off summary, NOT a triage note.
        md_path = os.path.join(
            self.notes_dir,
            f"{referral['referral_id']}.md",
        )

        lines = [
            f"# CASEWORKER HAND-OFF — {referral['referral_id']}",
            "",
            "## Why this is a hand-off",
            "",
            "ACA-2026/2 section 3.9 applies. The household includes a "
            "person under 18, or household composition could not be established.",
            "",
            "This is **ordinary casework hand-off**, not a section-4 escalation.",
            "The assistant must not draft the triage note.",
            "",
            "## Referral",
            "",
            f"- Resident: `{referral['resident_ref']}`",
            f"- Source: {referral['source']}",
            f"- Received: {referral['received_at']}",
            f"- Urgency: {referral['urgency']}",
            f"- Requested action: {referral['requested_action']}",
            f"- Summary: {referral['summary']}",
            "",
            "## Work already completed",
            "",
            f"- Resident history retrieved: `{history is not None}`",
            f"- Household determination: `{household['status']}`",
            f"- Determination reason: {household['reason']}",
            "",
        ]

        if household.get("children"):
            lines.append("### People under 18")
            lines.append("")
            for child in household["children"]:
                lines.append(
                    f"- {child['name']} — age {child['age']} "
                    f"({child['relationship']})"
                )
            lines.append("")

        lines.extend([
            "## Caseworker action",
            "",
            "Perform the triage-note work. Do not treat this hand-off as "
            "an approval request.",
            "",
            "**No triage note was drafted by the assistant.**",
        ])

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return record

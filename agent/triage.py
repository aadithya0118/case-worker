"""
Drafts a triage note for a permitted referral.

Per policy 2.4: "A drafted note is a proposal. It has no effect on the
case until a caseworker adopts it." Nothing in this module writes to
any system of record -- it produces text for a human to read.

This is template-based rather than LLM-generated. That's a deliberate
choice for a two-day build under a hard deadline: it is deterministic,
requires no API key, and cannot hallucinate a resident detail into a
note a caseworker might act on. If richer prose is wanted later, this
function is the single place to swap in a model call -- the policy
engine and the approval gate do not depend on how the note is written.
"""

RECOMMENDATION_BY_TYPE = {
    "assessment_recommendation": "Recommend caseworker conducts the requested review at earliest convenience.",
    "draft_note": "Note drafted as requested; no further agent action needed.",
    "flag": "Flagged for a caseworker to attempt contact.",
}


def draft_triage_note(referral, history, classification):
    resident_ref = referral["resident_ref"]
    lines = []
    lines.append(f"TRIAGE NOTE — {referral['referral_id']}")
    lines.append(f"Resident: {resident_ref}")
    lines.append(f"Source: {referral['source']}  |  Received: {referral['received_at']}  "
                 f"|  Reported urgency: {referral['urgency']}")
    lines.append("")
    lines.append("Situation:")
    lines.append(f"  {referral['summary']}")
    lines.append("")
    lines.append(f"Requested action: {referral['requested_action']}")
    lines.append(f"Policy basis for proceeding without approval: {classification.policy_basis} "
                 f"({classification.action_type})")
    lines.append("")

    if history:
        status = history.get("status", "unknown")
        benefit_code = history.get("benefit_code", "unknown")
        award = history.get("award_monthly", "unknown")
        household = history.get("household", [])
        events = history.get("events", [])
        lines.append("Case context:")
        lines.append(f"  Status: {status}  |  Benefit: {benefit_code}  |  Monthly award: {award}")
        lines.append(f"  Household size: {len(household)}")
        if events:
            last = events[-1]
            lines.append(f"  Most recent event on file: {last.get('date')} — {last.get('type')}")
        lines.append("")
    else:
        lines.append("Case context: history could not be retrieved for this referral "
                      "(see execution trace for the error). Triage proceeded on the "
                      "referral information alone.")
        lines.append("")

    recommendation = RECOMMENDATION_BY_TYPE.get(
        classification.action_type,
        "Recommend caseworker reviews and decides next step."
    )
    lines.append("Recommended next step:")
    lines.append(f"  {recommendation}")
    lines.append("")
    lines.append("This note is a proposal only. It has no effect on the case "
                 "until a caseworker adopts it (policy 2.4).")

    return "\n".join(lines)

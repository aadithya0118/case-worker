"""
Generates the morning briefing: a plain-prose handoff, not a log dump.

Everything else this agent produces (trace, escalations.jsonl, triage notes)
is written for a supervisor doing an audit. This is written for the
caseworker walking in at 9am, who wants to know in thirty seconds what
happened to their overnight queue and what still needs them.

No new judgement happens here -- it only narrates decisions the policy
engine already made. If this file disagreed with escalations.jsonl about
what got escalated, that would be a bug, not a style choice.
"""
from datetime import datetime


def build_briefing(referrals_by_outcome, run_date=None):
    """
    referrals_by_outcome: dict with keys 'drafted', 'escalated', 'failed',
    each a list of (referral, classification_or_None) tuples.
    """
    run_date = run_date or datetime.now().strftime("%A %d %B %Y")
    drafted = referrals_by_outcome["drafted"]
    escalated = referrals_by_outcome["escalated"]
    failed = referrals_by_outcome["failed"]
    total = len(drafted) + len(escalated) + len(failed)

    lines = []
    lines.append(f"MORNING BRIEFING — {run_date}")
    lines.append("=" * (len(lines[0])))
    lines.append("")
    lines.append(f"{total} referrals came in overnight. Here's where they stand.")
    lines.append("")

    if drafted:
        lines.append(f"HANDLED — {len(drafted)} triaged, notes ready for review")
        lines.append("-" * 60)
        for referral, classification in drafted:
            lines.append(f"  {referral['referral_id']}  ({referral['resident_ref']})")
            lines.append(f"    {referral['summary']}")
            lines.append(f"    -> note in output/triage_notes/{referral['referral_id']}.md")
        lines.append("")

    if escalated:
        lines.append(f"NEEDS YOU — {len(escalated)} outside what I'm allowed to do alone")
        lines.append("-" * 60)
        for referral, classification in escalated:
            lines.append(f"  {referral['referral_id']}  ({referral['resident_ref']})  "
                         f"— policy {classification.policy_basis}")
            lines.append(f"    Asked for: {referral['requested_action']}")
            lines.append(f"    Why I stopped: {classification.note}")
        lines.append("")

    if failed:
        lines.append(f"COULDN'T CHECK — {len(failed)} where history was unreachable")
        lines.append("-" * 60)
        for referral, _ in failed:
            lines.append(f"  {referral['referral_id']}  ({referral['resident_ref']})  "
                         f"— retry this one, I only had the referral text to go on")
        lines.append("")

    lines.append("Nothing above changed a resident's case. The handled ones are "
                 "drafts waiting on you; the rest are waiting on a supervisor.")

    return "\n".join(lines)

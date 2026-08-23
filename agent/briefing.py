"""
Generates the morning briefing.

ACA-2026/2 introduces a caseworker hand-off that is deliberately distinct
from a section-4 escalation.
"""

from datetime import datetime


def build_briefing(referrals_by_outcome, run_date=None):
    run_date = run_date or datetime.now().strftime("%A %d %B %Y")

    drafted = referrals_by_outcome["drafted"]
    escalated = referrals_by_outcome["escalated"]
    handed_off = referrals_by_outcome["handed_off"]
    # "failed" is no longer a real outcome bucket: a history-fetch failure
    # now always routes to an escalation or a hand-off (never silently
    # dropped), so runner.py doesn't populate this key. Kept optional here
    # rather than removed outright, in case a future change reintroduces
    # a genuine can't-complete-at-all case.
    failed = referrals_by_outcome.get("failed", [])

    total = (
        len(drafted)
        + len(escalated)
        + len(handed_off)
        + len(failed)
    )

    lines = [
        f"MORNING BRIEFING — {run_date}",
        "=" * len(f"MORNING BRIEFING — {run_date}"),
        "",
        f"{total} referrals came in overnight. Here's where they stand.",
        "",
    ]

    if drafted:
        lines += [
            f"HANDLED — {len(drafted)} triaged, notes ready for review",
            "-" * 60,
        ]

        for referral, _ in drafted:
            lines += [
                f"  {referral['referral_id']} ({referral['resident_ref']})",
                f"    {referral['summary']}",
                f"    -> note in output/triage_notes/{referral['referral_id']}.md",
            ]

        lines.append("")

    if handed_off:
        lines += [
            f"CASEWORKER HAND-OFF — {len(handed_off)} ordinary casework item(s)",
            "-" * 60,
        ]

        for referral, _ in handed_off:
            lines += [
                f"  {referral['referral_id']} ({referral['resident_ref']})",
                f"    {referral['summary']}",
                f"    -> hand-off in output/caseworker_handoffs/{referral['referral_id']}.md",
                "    -> no triage note was drafted by the assistant",
            ]

        lines.append("")

    if escalated:
        lines += [
            f"NEEDS SUPERVISOR — {len(escalated)} restricted action(s)",
            "-" * 60,
        ]

        for referral, classification in escalated:
            lines += [
                f"  {referral['referral_id']} ({referral['resident_ref']}) "
                f"— policy {classification.policy_basis}",
                f"    Asked for: {referral['requested_action']}",
                f"    Why stopped: {classification.note}",
            ]

        lines.append("")

    if failed:
        lines += [
            f"COULDN'T COMPLETE — {len(failed)} referral(s)",
            "-" * 60,
        ]

        for referral, _ in failed:
            lines.append(
                f"  {referral['referral_id']} ({referral['resident_ref']})"
            )

        lines.append("")

    lines += [
        "SAFETY SUMMARY:",
        "No restricted action was executed automatically.",
        "Child-household hand-offs are ordinary casework, not escalations.",
        "For ACA-2026/2 hand-offs, the assistant did not draft a triage note.",
    ]

    return "\n".join(lines)

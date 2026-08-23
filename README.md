# The Caseworker's Morning — Agentic AI / Guardrails (Brite Spark 2026, Problem 5)

Every morning, a caseworker spends forty minutes reading overnight referrals,
pulling case history, and drafting triage notes — before they've done anything
that actually needed their judgement. This agent does that part.

The harder half of the brief wasn't automating the sequence. It was building
something that knows, for each referral, which parts of the job it's allowed
to do alone — and for the ones it isn't, stops **because it structurally
cannot proceed**, not because a prompt told it to be careful. See
`DECISIONS.md` for exactly what that means and how it's verified.

## Running it

Requires Python 3 (standard library only, nothing to install).

```bash
python3 main.py
```

That's it. This single command starts the mock Resident History API as a
background process, runs the full referral queue through the agent, prints a
live trace to the console, and shuts the API down again when it's finished.

## What it does

For each of the 12 overnight referrals in `data/referral-queue.json`:

1. Reads the referral.
2. Pulls the resident's history from the mock API.
3. Checks the referral's requested action against `agent/policy_rules.json`
   (a structured version of `data/authority-policy.md`).
4. If the action is permitted unsupervised → drafts a triage note (a proposal
   only — it has no effect on the case) to `output/triage_notes/`.
5. If the action requires supervisor approval → **does not attempt it**, and
   writes an escalation record to `output/escalations.jsonl` instead, then
   carries on to the next referral.

## Output, after a run

- `output/MORNING_BRIEFING.md` — the one file meant to actually be read: a
  plain-prose handoff of what got handled and what needs a human, narrated
  from decisions the policy engine already made (it doesn't do any judging
  of its own — see `agent/briefing.py`).
- `output/execution_trace.txt` — human-readable log of every step taken, in
  order, with the policy basis for each decision. This is what a supervisor
  would read to reconstruct the run.
- `output/execution_trace.jsonl` — same trace, machine-readable.
- `output/triage_notes/<referral_id>.md` — one drafted note per permitted
  referral.
- `output/escalations.jsonl` — one record per referral the agent declined to
  action, with the policy section that applies and enough context for a
  supervisor to act without re-opening the case.

## Project layout

```
data/                       given data pack (referral queue, policy document)
services/history_service.py given mock Resident History API
agent/
  policy_rules.json          structured policy — the source of truth for what's permitted
  policy_engine.py           reads policy_rules.json, classifies a requested action
  history_client.py          calls the history API, fails gracefully if it can't
  triage.py                  drafts a triage note (template-based, deterministic)
  escalation.py               section-4 escalation records
  handoff.py                  ACA-2026/2 caseworker hand-offs
  household_rules.py          determines whether household has a person under 18
  trace.py                    execution trace logger
  runner.py                   orchestrates the above
main.py                      entry point
```

See `DECISIONS.md` for the reasoning behind the design, in particular how the
approval gate is enforced and how the two ambiguous referrals were resolved.
See `AI-USAGE.md` for how AI tooling was used while building this.

# AI usage

I used Claude (Anthropic) throughout this build. Roughly what it was used for:

- Reading and summarising the participant handbook and the problem 5 document
  to confirm scope and the floor requirements.
- Working through the authority policy against the referral queue to classify
  each of the 12 referrals as permitted or restricted, including identifying
  the two ambiguous cases (address change, income change) that only surface
  if you apply section 6.1 rather than judging by how serious a referral
  sounds.
- Scaffolding and writing the Python modules (`policy_engine.py`,
  `history_client.py`, `triage.py`, `escalation.py`, `trace.py`,
  `runner.py`, `main.py`) and `policy_rules.json`.
- Drafting this file, DECISIONS.md, and the README.

I reviewed and understood every part of the codebase and can explain any of
it, including why the guardrail is enforced the way it is and why the two
ambiguous referrals were resolved the way they were — that reasoning is
written out in DECISIONS.md in my own words, not generated as an
afterthought.

No AI was used inside the running agent itself — triage notes are drafted by
a deterministic template, not a model call (see DECISIONS.md, "What I
deliberately did not build," for why).

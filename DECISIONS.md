# Decisions

## What the agent is structurally incapable of doing, and how I know

There is no function anywhere in this codebase that suspends, terminates, or
reinstates an award; initiates, alters, or cancels a payment; changes payment
or bank details; sends a communication to a resident or third party;
discloses resident information; or writes a record asserting a finding of
fact (e.g. fraud) about a resident.

I know this because I wrote every module, and can point to why each one
cannot do it:

- `agent/history_client.py` only ever issues `GET` requests. There is no
  method that sends anything to the resident-history service or any other
  service — it has no way to write, even if it wanted to.
- `agent/triage.py` only ever returns a string. It has no side effects, no
  file writes, no network calls. What it produces is explicitly labelled "a
  proposal only" per policy 2.4.
- `agent/escalation.py` only ever appends a JSON record describing what was
  *not* done and why. It has no code path that performs the underlying
  action — it is the dead end for every restricted referral, not a staging
  area for later execution.
- `agent/runner.py`, the orchestrator, calls exactly these three modules and
  nothing else. There is no fourth code path.

So the guardrail isn't "the agent is told not to suspend awards." It's that
the capability to suspend an award does not exist in the program. Adding one
would mean writing new code, which is a different, visible, reviewable act —
not a matter of the agent choosing differently at runtime. This is the sense
in which the gate is "hard" rather than a prompt instruction: there was
never anything to override.

The one thing the agent *can* do unsupervised that touches a real case is
draft a triage note. That's deliberately the outer limit of policy 2 (2.3,
2.4), and the note itself says, in its own text, that it has no effect until
a caseworker adopts it.

## How the two ambiguous referrals were resolved

Policy 6.1 states: "Where it is unclear whether an action falls within
section 3, it is to be treated as though it does." Two referrals in the
queue are genuinely ambiguous under sections 1–5 read alone:

- **RF-2026-0413**, "Record change of address." An address isn't named in
  section 3. But Calder County's housing benefit calculations are commonly
  locality-dependent, so an address change can change the award amount
  without anyone calling it an "award change." I couldn't find language in
  the policy that clearly excludes this from 3.1, so under 6.1 it's treated
  as restricted.
- **RF-2026-0419**, "Record income change." Income feeds directly into
  award-amount calculation. "Recording" the change and "changing the award"
  aren't cleanly separable actions in a real benefits system. Same
  reasoning, same outcome: treated as restricted under 6.1.

I want to be honest that this is a judgement call, not a fact I can prove
from the policy text — the policy document doesn't resolve either case
explicitly. I chose the conservative reading because 6.1 exists precisely to
force that choice when the policy runs out, and because the cost of wrongly
escalating (a supervisor spends two minutes confirming something routine) is
much smaller than the cost of wrongly proceeding (an unsupervised change to
someone's benefit award). A different, defensible design could argue address
changes are pure record-keeping and permit them outright — I'd want to raise
that with an actual supervisor rather than decide it unilaterally in code.

## Why there's a briefing on top of the trace and escalations log

`execution_trace.txt` and `escalations.jsonl` are written for an audit —
that's what section 5 of the policy actually requires, so they stay literal
and complete. `output/MORNING_BRIEFING.md` is written for the caseworker at
9am who just wants to know what happened. It's pure narration: it makes no
decision the policy engine hasn't already made, and if it ever disagreed
with `escalations.jsonl` about what got escalated, that would be a bug in
`agent/briefing.py`, not a second opinion. Kept it to one extra module so it
couldn't become a second source of truth by accident.

## Why the policy is data, not code

`agent/policy_rules.json` holds every restricted/permitted action type and
the policy section it maps to. `agent/policy_engine.py` contains no
knowledge of what's restricted — it just matches a requested action against
whatever the JSON says and fails safe (treats an unrecognised action as
restricted) if nothing matches.

This was the single most important structural decision given the warned
day-two requirement change. If day two changes which actions require
approval, or adds a new referral type, or revises which policy section
applies to what — the fix is a JSON edit, not a change to the agent's
control flow. I don't know what the change will be, so I didn't try to
predict it; I tried to make sure the *policy* and the *sequence that applies
it* are two different files that don't need to change together.

## What I deliberately did not build

- **No approval workflow with notifications or accounts.** The handbook
  says a queue a human reads is enough to demonstrate the gate, and building
  a fake notification system would be effort spent on something not
  assessed.
- **No LLM call in the runtime agent.** Triage notes are template-based.
  Given a two-day build and a hard requirement that the demo run reliably
  from a clean clone, I didn't want the floor requirements depending on an
  API key being present and a model call succeeding. `agent/triage.py` is
  written so an LLM-authored version could replace the templating without
  touching the policy engine or the escalation path — but I ran out of
  runway to build and test that safely, so I didn't ship it.
- **No handling of referral types outside the given queue.** Explicitly
  listed as not required. The `default_when_unmatched` rule in
  `policy_rules.json` means an unfamiliar referral type fails safe
  (escalates) rather than being silently mishandled, which felt like the
  right amount of future-proofing without over-building for a change I
  can't predict.

## What I would fix first, given more time

- The keyword matching in `policy_engine.py` matches on the referral's
  `requested_action` field being *exactly* one of a known set of phrases. It
  would not catch a differently-worded referral asking for the same
  restricted action (e.g. "change the account we pay into" instead of
  "Update payment details"). The `default_when_unmatched` fail-safe covers
  the case where nothing matches, but a paraphrase that *happens* to match
  the wrong permitted phrase wouldn't be caught by that fail-safe. Matching
  on intent rather than exact phrase (via a model call, with the actual gate
  still enforced in code afterward) is the natural next step.
- I have not tested what happens if the escalation or triage-notes directory
  is not writable, or if the referral queue JSON is malformed. The agent
  would currently crash rather than fail gracefully in either case.

## Day-two amendment: ACA-2026/2

ACA-2026/2 adds section 3.9: where the Department's household composition
includes a person under 18, the assistant must not draft the triage note.
The case must instead be handed to a caseworker with the work already done.

### What changed

The control flow now has a distinct branch after history retrieval and
household determination:

1. Read referral.
2. Retrieve Department history.
3. Determine household composition from the Department record.
4. Apply the existing section-3 restriction first.
5. If the requested action is otherwise permitted but 3.9 applies, create a
   **caseworker hand-off** and do not call `draft_triage_note()`.
6. Only a permitted, non-child-household referral reaches note drafting.

The hand-off is deliberately separate from `EscalationQueue`. An escalation
means the Department must decide whether a restricted action may happen at
all.
A hand-off means ordinary casework still needs a human because the amendment
says the assistant may not perform that particular drafting step.

### What work is preserved

The hand-off records the referral, the retrieved history status, household
determination, identified people under 18, requested action, and the policy
basis. It also writes a human-readable hand-off file. It does not create a
triage note.

If household composition cannot be established, ACA-2026/2 section 5.2 makes
3.9 apply. The assistant therefore hands the case to a caseworker rather
than guessing.

### How the day-two change is supported during a run

`PolicyEngine` reloads `policy_rules.json` before each referral's policy
decision. The new amendment is represented as policy data rather than a
special-case branch hidden inside the original triage logic. This means a
policy-file amendment can affect referrals that have not yet reached their
decision point, including a queue already part-way through processing.

### Interpretation choice

The amendment says a person is "under 18" but does not specify the clock to
use for calculating age. For deterministic casework behavior, this
implementation uses the referral's `received_at` date as the reference date.
That prevents the demo result from changing simply because the machine's
current date changes.

### What I did not change

I did not turn the new rule into an escalation. The amendment explicitly says
a hand-off under 3.2 is not an escalation under section 4.

I also did not modify `triage.py` to try to draft and then discard a note.
The restriction applies to drafting itself, so the branch prevents the
drafting function from being called at all.

### What I would improve with more time

I would add a configurable policy-effective timestamp and a live amendment
watcher if the real system had policy changes arriving during a long-running
queue. For this two-day synthetic-data problem, reloading the policy at each
referral is sufficient to keep the decision point amendment-aware without
introducing unnecessary infrastructure.

## The optional Streamlit viewer

`streamlit_app.py` is a viewer added after the rest of this was built and
tested, for walking through a run live. It's worth being explicit about
what it is and isn't:

- It is not scored. The problem document states plainly that interface
  quality isn't assessed for this problem, and I don't want that to be
  ambiguous in this file.
- It calls `agent.runner.run()` directly — the same function `main.py`
  calls. It contains no policy logic, no classification, no gate of its
  own. If the UI and the CLI ever showed different results for the same
  queue, that would be a bug in the viewer, not a second opinion.
- The command-line path remains the primary, zero-dependency way to run
  and judge this submission. The UI needs `pip install -r requirements.txt`
  first; the core agent needs nothing beyond the standard library.
- `main.py --ui` launches it, rather than a separate `streamlit run`
  invocation, so there's one entry point to remember. This is a flag,
  not the default: `python3 main.py` with no arguments still runs the
  plain CLI agent with zero dependencies. That default has to keep
  working on a machine with nothing installed, since that's exactly
  what the clean-clone check does before a human looks at anything —
  making the UI opt-in rather than the default protects that.

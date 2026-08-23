"""
Optional interactive UI for The Caseworker's Morning.

This is a viewer, not a second implementation. It imports and calls
agent.runner.run() exactly as main.py does -- it does not duplicate,
reimplement, or alter any policy decision, classification, or gate
logic. Everything scored (the floor, the guardrail, the amendment
response) lives in agent/ and runs identically with or without this
file.

Not part of the graded deliverable for this problem -- interface
quality isn't assessed here (see README). This exists purely so the
run and its outputs are easier to walk through live.

Run with:  streamlit run streamlit_app.py
"""
import contextlib
import io
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
TRIAGE_DIR = OUTPUT_DIR / "triage_notes"
HANDOFF_DIR = OUTPUT_DIR / "caseworker_handoffs"

sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="The Caseworker's Morning",
    page_icon="🗂️",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 2.5rem; max-width: 1100px; }
        h1 { font-weight: 600; letter-spacing: -0.02em; }
        [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 600; }
        .stTabs [data-baseweb="tab"] { font-size: 0.95rem; }
        div[data-testid="stMarkdownContainer"] pre {
            background-color: #F4F6F8;
            border: 1px solid #E5E7EB;
            border-radius: 6px;
        }
        .status-pill {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em;
        }
        .pill-drafted { background:#E8F3EC; color:#1E7B45; }
        .pill-handoff { background:#EEF1FB; color:#3F51B5; }
        .pill-escalated { background:#FBEEEE; color:#B3261E; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("The Caseworker's Morning")
st.caption("Agentic triage assistant · Brite Spark 2026, Problem 5 · Policy ACA-2026/1 + Amendment ACA-2026/2")

with st.sidebar:
    st.subheader("Run")
    st.write(
        "Processes the overnight referral queue end to end: reads each "
        "referral, pulls resident history, and either drafts a triage "
        "note, hands off a child-household case to a caseworker, or "
        "escalates a restricted action to a supervisor."
    )
    run_clicked = st.button("▶  Run this morning's queue", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "Starts the mock Resident History API, processes all referrals, "
        "and writes everything to `output/` — same as `python3 main.py`."
    )
    st.divider()
    st.caption("This UI is a viewer only. It calls the same `agent.runner.run()` "
               "used by the command-line entry point — nothing here changes "
               "what the agent decides.")

if run_clicked:
    from agent.runner import run as run_agent
    with st.spinner("Starting the history service and processing referrals…"):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_agent()
        st.session_state["last_log"] = buf.getvalue()
    st.success("Run complete.")


def load_text(path):
    return path.read_text(encoding="utf-8") if path.exists() else None


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


briefing = load_text(OUTPUT_DIR / "MORNING_BRIEFING.md")

if briefing is None:
    st.info("No run yet this session. Click **Run this morning's queue** in the sidebar to start.")
else:
    escalations = load_jsonl(OUTPUT_DIR / "escalations.jsonl")
    handoffs = load_jsonl(OUTPUT_DIR / "caseworker_handoffs.jsonl")
    triage_files = sorted(TRIAGE_DIR.glob("*.md")) if TRIAGE_DIR.exists() else []
    handoff_files = sorted(HANDOFF_DIR.glob("*.md")) if HANDOFF_DIR.exists() else []

    c1, c2, c3 = st.columns(3)
    c1.metric("Triaged", len(triage_files))
    c2.metric("Handed to caseworker", len(handoffs))
    c3.metric("Escalated to supervisor", len(escalations))

    tab_brief, tab_triage, tab_handoff, tab_escalate, tab_trace = st.tabs(
        ["Morning Briefing", "Triage Notes", "Caseworker Hand-offs", "Escalations", "Execution Trace"]
    )

    with tab_brief:
        st.markdown(briefing)

    with tab_triage:
        st.markdown('<span class="status-pill pill-drafted">DRAFTED — proposal only, per policy 2.4</span>',
                     unsafe_allow_html=True)
        st.write("")
        if triage_files:
            choice = st.selectbox("Referral", [f.stem for f in triage_files], key="triage_sel")
            st.markdown((TRIAGE_DIR / f"{choice}.md").read_text(encoding="utf-8"))
        else:
            st.write("No referrals were triaged in this run.")

    with tab_handoff:
        st.markdown('<span class="status-pill pill-handoff">CASEWORKER HAND-OFF — ordinary casework, not an escalation</span>',
                     unsafe_allow_html=True)
        st.write("")
        if handoff_files:
            choice = st.selectbox("Referral", [f.stem for f in handoff_files], key="handoff_sel")
            st.markdown((HANDOFF_DIR / f"{choice}.md").read_text(encoding="utf-8"))
        else:
            st.write("No referrals required a caseworker hand-off in this run.")

    with tab_escalate:
        st.markdown('<span class="status-pill pill-escalated">ESCALATED — awaiting supervisor decision</span>',
                     unsafe_allow_html=True)
        st.write("")
        if escalations:
            for rec in escalations:
                with st.expander(f"{rec['referral_id']} — {rec['requested_action']}  (policy {rec['policy_basis']})"):
                    st.json(rec)
        else:
            st.write("No referrals were escalated in this run.")

    with tab_trace:
        trace_txt = load_text(OUTPUT_DIR / "execution_trace.txt")
        st.text(trace_txt or "No trace available.")

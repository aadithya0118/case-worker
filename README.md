# Case Worker — Automated Casework Assistant

An automated casework assistant designed to process overnight referrals, retrieve resident history, validate requested actions against authority policies, and safely determine whether a case can be processed automatically or requires human intervention.

The system focuses on **safe automation with policy-based guardrails**, ensuring that restricted actions are never executed without the required approval.

---

## 📌 Overview

Caseworkers often spend significant time reviewing incoming referrals, retrieving resident information, checking policies, and preparing initial triage notes.

This project automates those repetitive steps while keeping sensitive or restricted decisions under human control.

For each incoming referral, the system retrieves the resident's history, evaluates the requested action against structured policy rules, checks household safety conditions, and determines whether the case can proceed automatically.

Permitted cases can receive automatically drafted triage notes, while cases requiring additional authorization are escalated or handed off for human review.

---

## ✨ Key Features

* Processes overnight case referrals automatically.
* Retrieves resident history using a mock Resident History API.
* Validates requested actions against structured authority policies.
* Uses a policy engine to determine whether an action is permitted.
* Applies household safety rules before automated triage.
* Drafts triage notes only for permitted cases.
* Escalates actions that require supervisor approval.
* Supports human handoff when automated processing should not continue.
* Records processing decisions through execution traces.
* Generates a morning briefing summarizing processed and escalated cases.
* Provides an optional Streamlit-based interface for demonstration.

---

## 🔄 Project Workflow

```text
                Overnight Referral Queue
                         │
                         ▼
                  Read Referral
                         │
                         ▼
              Retrieve Resident History
                         │
                         ▼
               Household Safety Check
                         │
                         ▼
                  Policy Engine
                         │
                Validate Requested
                     Action
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        Action Permitted       Approval / Human
         Unsupervised             Review Needed
              │                     │
              ▼                     ▼
       Draft Triage Note      Escalation / Handoff
              │                     │
              └──────────┬──────────┘
                         ▼
                  Execution Trace
                         │
                         ▼
                  Morning Briefing
```

### Workflow Description

The system begins by reading referrals from the overnight referral queue. For each referral, it retrieves the corresponding resident history through the mock Resident History API.

The household information and requested action are then evaluated using predefined safety rules and the structured authority policy.

The **Policy Engine** acts as the decision gate. If an action is permitted without supervision, the system can generate a draft triage note. If supervisor approval or human intervention is required, the system stops automated processing for that action and creates an escalation or handoff instead.

Every important processing step is recorded in an execution trace, allowing the decisions made by the system to be reviewed. After processing the referral queue, the system generates a morning briefing summarizing the results.

---

## 🧩 Main Components

### Policy Engine

Reads the structured policy rules and determines whether a requested action can be performed automatically or requires approval.

### Triage Module

Generates deterministic draft triage notes for referrals that successfully pass the policy and safety checks.

### History Client

Communicates with the mock Resident History API to retrieve relevant resident information.

### Household Rules

Checks household conditions and determines whether additional human review or handoff is required.

### Escalation Module

Creates escalation records when the requested action requires supervisor approval.

### Handoff Module

Transfers cases to human caseworkers when automated processing should not continue.

### Trace Logger

Records the sequence of actions and decisions made during case processing for auditability.

### Runner

Coordinates the complete workflow and connects the individual components of the system.

---

## 📂 Project Structure

```text
case-worker/
│
├── agent/
│   ├── __init__.py
│   ├── briefing.py
│   ├── escalation.py
│   ├── handoff.py
│   ├── history_client.py
│   ├── household_rules.py
│   ├── policy_engine.py
│   ├── policy_rules.json
│   ├── runner.py
│   ├── trace.py
│   └── triage.py
│
├── challenge/
│   ├── Amendment ACA-2026-2.md
│   └── READ ME FIRST.md
│
├── data/
│   ├── authority-policy.md
│   └── referral-queue.json
│
├── services/
│   ├── _history_data.json
│   └── history_service.py
│
├── .gitignore
├── AI-USAGE.md
├── DECISIONS.md
├── main.py
├── README.md
├── requirements.txt
└── streamlit_app.py
```

---

## ⚙️ How the Decision Process Works

For each referral:

1. The referral is loaded from `data/referral-queue.json`.
2. Resident history is retrieved from the mock history service.
3. Household conditions are evaluated.
4. The requested action is checked against `agent/policy_rules.json`.
5. The policy engine determines whether the action is permitted.
6. Permitted cases can receive a draft triage note.
7. Restricted cases are escalated or handed off for human review.
8. Processing continues with the remaining referrals.
9. All major decisions are recorded in the execution trace.
10. A final morning briefing summarizes the processing results.

---

## ▶️ Running the Project

### Standard Execution

The core application can be run using:

```bash
python main.py
```

The application starts the mock Resident History API, processes the referral queue, records the execution trace, generates the appropriate outputs, and shuts down the service when processing is complete.

---

## 🖥️ Optional User Interface

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Then run the application with the UI enabled:

```bash
python main.py --ui
```

The interface provides a convenient way to demonstrate the processing workflow and view the generated results.

---

## 📤 Generated Outputs

After execution, the system can generate:

```text
output/
│
├── MORNING_BRIEFING.md
├── execution_trace.txt
├── execution_trace.jsonl
├── escalations.jsonl
└── triage_notes/
```

### Morning Briefing

Provides a human-readable summary of what the automated assistant processed and which cases require attention.

### Triage Notes

Contains automatically drafted notes for referrals that were permitted by the policy engine.

### Escalations

Records referrals that could not be processed automatically because supervisor approval was required.

### Execution Trace

Maintains a detailed record of the processing steps and policy decisions for audit and review.

---

## 🛡️ Safety and Guardrails

A major objective of this project is to ensure that automation does not bypass human authority.

The system uses structural policy checks before allowing automated actions. When an action requires supervisor approval or falls under a household safety restriction, the automated workflow does not continue with that action.

Instead, the case is escalated or handed off for appropriate human review.

This provides a clear separation between:

**Automated assistance** → repetitive and permitted casework tasks

**Human decision-making** → restricted, sensitive, or approval-dependent actions

---

## 🛠️ Technologies Used

* **Python**
* **Streamlit**
* **JSON**
* **Markdown**
* **REST-style Mock API**
* **Rule-Based Policy Engine**
* **Agent-Based Workflow**
* **Git & GitHub**

---

## 📚 Additional Documentation

* `DECISIONS.md` — explains important implementation and design decisions.
* `AI-USAGE.md` — documents the use of AI tools during development.
* `authority-policy.md` — contains the supplied authority policy.
* `policy_rules.json` — structured representation of policy rules used by the policy engine.

---

## 🎯 Project Objective

The objective of the project is to demonstrate how an automated casework assistant can reduce repetitive manual work while maintaining strict policy controls, transparent decision-making, auditability, and appropriate human oversight.

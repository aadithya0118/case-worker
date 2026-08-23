"""
Policy engine.

The policy is data, not control flow. Rules are re-read for every referral,
so a policy amendment that arrives while a queue is being processed can
apply to referrals that have not yet been triaged.

ACA-2026/2 adds a separate child-household hand-off condition. It is not
represented as an escalation because the amendment explicitly distinguishes
a caseworker hand-off from section-4 escalation.
"""

import json
import os
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, "policy_rules.json")

PERMITTED = "PERMITTED"
REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


@dataclass
class Classification:
    status: str
    action_type: str
    policy_basis: str
    note: str


class PolicyEngine:
    def __init__(self, rules_path=RULES_PATH):
        self.rules_path = rules_path
        self.rules = {}
        self.policy_reference = "unknown"
        self.reload()

    def reload(self):
        with open(self.rules_path, encoding="utf-8") as f:
            self.rules = json.load(f)
        self.policy_reference = self.rules.get("policy_reference", "unknown")

    def _normalise(self, text):
        return " ".join((text or "").strip().lower().split())

    def classify(self, requested_action):
        # Reload before every decision so an amendment can take effect
        # for referrals still waiting in the queue.
        self.reload()

        normalised = self._normalise(requested_action)

        for rule in self.rules.get("restricted_action_types", []):
            if normalised in [self._normalise(m) for m in rule["match"]]:
                return Classification(
                    status=REQUIRES_APPROVAL,
                    action_type=rule["action_type"],
                    policy_basis=rule["policy_basis"],
                    note=rule["note"],
                )

        for rule in self.rules.get("permitted_action_types", []):
            if normalised in [self._normalise(m) for m in rule["match"]]:
                return Classification(
                    status=PERMITTED,
                    action_type=rule["action_type"],
                    policy_basis=rule["policy_basis"],
                    note=rule["note"],
                )

        default = self.rules["default_when_unmatched"]
        return Classification(
            status=REQUIRES_APPROVAL if default["requires_approval"] else PERMITTED,
            action_type=default["action_type"],
            policy_basis=default["policy_basis"],
            note=default["note"],
        )

    def child_household_rule(self):
        self.reload()
        return (
            self.rules
            .get("amendments", {})
            .get("ACA-2026/2", {})
            .get("household_child_handoff")
        )

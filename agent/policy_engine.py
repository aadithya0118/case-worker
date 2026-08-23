"""
Policy engine — reads policy_rules.json and classifies a referral's
requested_action as PERMITTED or REQUIRES_APPROVAL.

Design intent: this module contains no policy decisions of its own.
Every judgement call (what's permitted, what's restricted, what the
safe default is) lives in policy_rules.json. If policy ACA-2026/1 is
revised, or the day-two requirement change touches what the agent may
do unsupervised, that change belongs in the JSON file. This module
should not need to change for a policy update to take effect.
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
    status: str            # PERMITTED or REQUIRES_APPROVAL
    action_type: str
    policy_basis: str
    note: str


class PolicyEngine:
    def __init__(self, rules_path=RULES_PATH):
        with open(rules_path, encoding="utf-8") as f:
            self.rules = json.load(f)
        self.policy_reference = self.rules.get("policy_reference", "unknown")

    def classify(self, requested_action: str) -> Classification:
        normalised = requested_action.strip().lower()

        for rule in self.rules.get("restricted_action_types", []):
            if normalised in [m.lower() for m in rule["match"]]:
                return Classification(
                    status=REQUIRES_APPROVAL,
                    action_type=rule["action_type"],
                    policy_basis=rule["policy_basis"],
                    note=rule["note"],
                )

        for rule in self.rules.get("permitted_action_types", []):
            if normalised in [m.lower() for m in rule["match"]]:
                return Classification(
                    status=PERMITTED,
                    action_type=rule["action_type"],
                    policy_basis=rule["policy_basis"],
                    note=rule["note"],
                )

        # Fails safe: an action type the policy engine has never seen
        # is not assumed to be fine. See policy_rules.json -> default_when_unmatched.
        default = self.rules["default_when_unmatched"]
        return Classification(
            status=REQUIRES_APPROVAL if default["requires_approval"] else PERMITTED,
            action_type=default["action_type"],
            policy_basis=default["policy_basis"],
            note=default["note"],
        )

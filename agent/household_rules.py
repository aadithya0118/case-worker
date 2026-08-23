"""
ACA-2026/2 household composition rule.

The amendment says the household composition held by the Department is
the source of truth. If it cannot be established, the amendment applies.

This module only determines whether the new 3.9 hand-off condition applies.
It never drafts a note and never escalates a case.
"""

from datetime import date


def _age_on(date_of_birth, as_of):
    dob = date.fromisoformat(date_of_birth)
    return (
        as_of.year
        - dob.year
        - ((as_of.month, as_of.day) < (dob.month, dob.day))
    )


def determine_household_composition(history, as_of):
    """
    Returns a structured determination.

    status:
      ESTABLISHED_CHILD
      ESTABLISHED_NO_CHILD
      UNKNOWN

    A household containing anyone under 18 is a child household.
    If composition or DOB information cannot be established, the
    amendment's safe-default rule treats 3.9 as applying.
    """

    if not isinstance(history, dict):
        return {
            "status": "UNKNOWN",
            "has_person_under_18": None,
            "children": [],
            "reason": "Household composition could not be established.",
        }

    household = history.get("household")

    if not isinstance(household, list):
        return {
            "status": "UNKNOWN",
            "has_person_under_18": None,
            "children": [],
            "reason": "Department household composition is unavailable.",
        }

    children = []

    for member in household:
        if not isinstance(member, dict):
            return {
                "status": "UNKNOWN",
                "has_person_under_18": None,
                "children": children,
                "reason": "A household member record could not be established.",
            }

        dob = member.get("date_of_birth")
        if not dob:
            return {
                "status": "UNKNOWN",
                "has_person_under_18": None,
                "children": children,
                "reason": "A household member has no date of birth.",
            }

        try:
            age = _age_on(dob, as_of)
        except (TypeError, ValueError):
            return {
                "status": "UNKNOWN",
                "has_person_under_18": None,
                "children": children,
                "reason": "A household member's date of birth could not be established.",
            }

        if age < 18:
            children.append({
                "name": member.get("name", "Unknown"),
                "age": age,
                "date_of_birth": dob,
                "relationship": member.get("relationship", "Unknown"),
            })

    if children:
        return {
            "status": "ESTABLISHED_CHILD",
            "has_person_under_18": True,
            "children": children,
            "reason": "Department household composition includes a person under 18.",
        }

    return {
        "status": "ESTABLISHED_NO_CHILD",
        "has_person_under_18": False,
        "children": [],
        "reason": "Department household composition contains no person under 18.",
    }

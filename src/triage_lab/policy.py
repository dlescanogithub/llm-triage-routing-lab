"""Threshold, containment and route selection."""

from __future__ import annotations

from triage_lab.taxonomy import Taxonomy


def decide_route(
    category: str,
    confidence: float,
    tau: float,
    injection: bool,
    taxonomy: Taxonomy,
    *,
    kill_switch: bool = False,
) -> str:
    """Pick a route. Low confidence falls back to a person.

    Detected injection and ``abuse_or_legal`` go to ``security_review`` even
    when confidence is low. That route is containment, not a privilege upgrade.
    """
    if kill_switch:
        return "human_review"
    if injection or category == "abuse_or_legal":
        return "security_review"
    if confidence < tau:
        return "human_review"
    return taxonomy.route_for(category)


def more_privileged(route: str, gold_category: str, taxonomy: Taxonomy) -> bool:
    """True when ``route`` outranks the gold category and is not containment."""
    if taxonomy.is_containment(route):
        return False
    allowed = taxonomy.route_for(gold_category)
    return taxonomy.privilege_of(route) > taxonomy.privilege_of(allowed)

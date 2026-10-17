"""Validate the classifier JSON. Invalid output is not a category."""

from __future__ import annotations

import json
from typing import Any

from triage_lab.models import Classification

REQUIRED = ("category", "confidence", "injection_suspected", "rationale")


def dumps_classification(classification: Classification) -> str:
    payload = {
        "category": classification.category,
        "confidence": classification.confidence,
        "injection_suspected": classification.injection_suspected,
        "rationale": classification.rationale,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def parse_classification(text: str, categories: set[str]) -> Classification | None:
    """Return a classification, or None when the text is not valid schema."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict) or set(raw) != set(REQUIRED):
        return None
    return _from_mapping(raw, categories)


def _from_mapping(raw: dict[str, Any], categories: set[str]) -> Classification | None:
    category = raw["category"]
    confidence = raw["confidence"]
    injection = raw["injection_suspected"]
    rationale = raw["rationale"]
    if not isinstance(category, str) or category not in categories:
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    if not 0.0 <= float(confidence) <= 1.0:
        return None
    if not isinstance(injection, bool):
        return None
    if not isinstance(rationale, str) or len(rationale) > 500:
        return None
    return Classification(
        category=category,
        confidence=float(confidence),
        injection_suspected=injection,
        rationale=rationale,
    )

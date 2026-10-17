"""Validate the classifier JSON. Invalid output is not a category."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from triage_lab.models import Classification

REQUIRED = ("category", "confidence", "injection_suspected", "rationale")
CONFIDENCE_ALLOWED = "a JSON number from 0.0 to 1.0 inclusive (not a 0-100 score)"


@dataclass(frozen=True)
class FieldError:
    field: str
    value: str
    allowed: str


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
    diagnosed = diagnose_classification(text, categories)
    if isinstance(diagnosed, Classification):
        return diagnosed
    return None


def diagnose_classification(
    text: str, categories: set[str]
) -> Classification | tuple[FieldError, ...]:
    """Return the object, or one error per invalid field with the allowed values."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return (
            FieldError(
                "json",
                _shown(text),
                "one JSON object with keys "
                + ", ".join(REQUIRED)
                + " and no other text",
            ),
        )
    if not isinstance(raw, dict):
        return (
            FieldError("json", _shown(raw), "a JSON object, not an array or scalar"),
        )
    errors: list[FieldError] = []
    extra = sorted(set(raw) - set(REQUIRED))
    missing = sorted(set(REQUIRED) - set(raw))
    if extra:
        errors.append(
            FieldError(
                "keys",
                _shown(extra),
                "only these keys: " + ", ".join(REQUIRED),
            )
        )
    if missing:
        errors.append(
            FieldError(
                "keys",
                _shown(missing),
                "all of these keys are required: " + ", ".join(REQUIRED),
            )
        )
    errors.extend(_field_errors(raw, categories))
    if errors:
        return tuple(errors)
    return Classification(
        category=str(raw["category"]),
        confidence=float(raw["confidence"]),
        injection_suspected=bool(raw["injection_suspected"]),
        rationale=str(raw["rationale"]),
    )


def format_retry_feedback(errors: Sequence[FieldError]) -> str:
    """Concrete retry note. The next request must include this text."""
    lines = ["Previous output rejected."]
    for error in errors:
        lines.append(
            f"field {error.field} value {error.value} is invalid. "
            f"Allowed: {error.allowed}."
        )
    lines.append("Return one JSON object and nothing else.")
    return "\n".join(lines)


def _field_errors(raw: dict[str, Any], categories: set[str]) -> list[FieldError]:
    errors: list[FieldError] = []
    allowed_categories = ", ".join(sorted(categories))
    if "category" in raw:
        category = raw["category"]
        if not isinstance(category, str) or category not in categories:
            errors.append(FieldError("category", _shown(category), allowed_categories))
    if "confidence" in raw:
        confidence = raw["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            errors.append(
                FieldError("confidence", _shown(confidence), CONFIDENCE_ALLOWED)
            )
        elif not 0.0 <= float(confidence) <= 1.0:
            errors.append(
                FieldError("confidence", _shown(confidence), CONFIDENCE_ALLOWED)
            )
    if "injection_suspected" in raw:
        injection = raw["injection_suspected"]
        if not isinstance(injection, bool):
            errors.append(
                FieldError(
                    "injection_suspected",
                    _shown(injection),
                    "JSON true or false",
                )
            )
    if "rationale" in raw:
        rationale = raw["rationale"]
        if not isinstance(rationale, str) or len(rationale) > 500:
            errors.append(
                FieldError(
                    "rationale", _shown(rationale), "a string of at most 500 characters"
                )
            )
    return errors


def _shown(value: object) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    if len(text) > 80:
        return text[:77] + "..."
    return text

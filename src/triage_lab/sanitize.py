"""Strip controls, cap length, and neutralize a fixed list of known markers.

This is not a general injection detector. Strings outside the list pass through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 4000

# Order is the neutralization order. HTML comments are removed whole.
MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous", re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE)),
    ("ignore_all", re.compile(r"ignore\s+all\s+previous", re.IGNORECASE)),
    ("you_are_now", re.compile(r"you\s+are\s+now", re.IGNORECASE)),
    ("system_prompt", re.compile(r"system\s+prompt", re.IGNORECASE)),
    ("reveal_instructions", re.compile(r"reveal\s+your\s+instructions", re.IGNORECASE)),
    ("system_tag", re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE)),
    ("system_bracket", re.compile(r"\[\s*system\s*\]", re.IGNORECASE)),
    ("approve_refund", re.compile(r"approve[_\s]+refund", re.IGNORECASE)),
    ("route_billing", re.compile(r"route\s+me\s+to\s+billing", re.IGNORECASE)),
    ("tool_json", re.compile(r"\{\s*[\"']tool[\"']", re.IGNORECASE)),
    ("category_must", re.compile(r"category\s+must\s+be", re.IGNORECASE)),
    ("do_not_follow", re.compile(r"do\s+not\s+follow\s+the\s+policy", re.IGNORECASE)),
    ("auto_faq", re.compile(r"auto-?\s*reply\s+the\s+faq", re.IGNORECASE)),
    (
        "treat_product",
        re.compile(r"treat\s+this\s+as\s+a\s+product\s+question", re.IGNORECASE),
    ),
    ("other_customers", re.compile(r"other\s+customers", re.IGNORECASE)),
    ("html_comment", re.compile(r"<!--.*?-->", re.IGNORECASE | re.DOTALL)),
)

BILLING_MARKER_IDS = frozenset(
    {
        "approve_refund",
        "route_billing",
        "tool_json",
        "category_must",
        "you_are_now",
        "do_not_follow",
    }
)
AUTO_REPLY_MARKER_IDS = frozenset(
    {
        "auto_faq",
        "treat_product",
    }
)
TOOL_MARKER_IDS = frozenset({"approve_refund", "tool_json"})


@dataclass(frozen=True)
class SanitizeResult:
    text: str
    markers: tuple[str, ...]
    truncated: bool

    @property
    def injection_marker(self) -> bool:
        return bool(self.markers)


def strip_controls(text: str) -> str:
    """Drop characters below ASCII 32 except tab and newline."""
    kept: list[str] = []
    for char in text:
        code = ord(char)
        if char in "\n\t" or code >= 32:
            kept.append(char)
    return "".join(kept)


def find_markers(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in MARKERS if pattern.search(text))


def neutralize(text: str) -> tuple[str, tuple[str, ...]]:
    found: list[str] = []
    updated = text
    for name, pattern in MARKERS:
        if pattern.search(updated):
            found.append(name)
            updated = pattern.sub("[filtered]", updated)
    return updated, tuple(found)


def sanitize_text(text: str, limit: int = MAX_CHARS) -> SanitizeResult:
    """Neutralize known markers on the full text, then cap the length."""
    cleaned = strip_controls(text)
    neutralized, markers = neutralize(cleaned)
    truncated = len(neutralized) > limit
    if truncated:
        neutralized = neutralized[:limit]
    return SanitizeResult(text=neutralized, markers=markers, truncated=truncated)

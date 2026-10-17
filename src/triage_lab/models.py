"""Shared records for tickets and provider calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Ticket:
    id: str
    split: str
    lang: str
    subject: str
    body: str
    label: str
    difficulty: str
    tags: tuple[str, ...]
    injection: bool

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "split": self.split,
            "lang": self.lang,
            "subject": self.subject,
            "body": self.body,
            "label": self.label,
            "difficulty": self.difficulty,
            "tags": list(self.tags),
            "injection": self.injection,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Ticket:
        tags = raw["tags"]
        if not isinstance(tags, list) or not all(
            isinstance(item, str) for item in tags
        ):
            raise TypeError(f"{raw.get('id')}: tags must be a list of strings")
        injection = raw["injection"]
        if not isinstance(injection, bool):
            raise TypeError(f"{raw.get('id')}: injection must be a bool")
        return cls(
            id=_text(raw, "id"),
            split=_text(raw, "split"),
            lang=_text(raw, "lang"),
            subject=_text(raw, "subject"),
            body=_text(raw, "body"),
            label=_text(raw, "label"),
            difficulty=_text(raw, "difficulty"),
            tags=tuple(tags),
            injection=injection,
        )


def _text(raw: Mapping[str, Any], key: str) -> str:
    value = raw[key]
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Mapping[str, str]


@dataclass(frozen=True)
class CompletionRequest:
    system: str
    user: str
    max_output_tokens: int = 256


@dataclass(frozen=True)
class CompletionResponse:
    text: str
    tool_calls: tuple[ToolCall, ...]
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    injection_suspected: bool
    rationale: str

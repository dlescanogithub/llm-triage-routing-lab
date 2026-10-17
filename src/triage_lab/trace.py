"""JSONL trace. One event per line: run_id, ts, kind, payload."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from triage_lab.logutil import redact


def isoformat(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(value: object) -> object:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    return value


class Trace:
    """In-memory JSONL trace. Payloads are redacted and should stay small."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self.events: list[dict[str, Any]] = []

    def emit(self, run_id: str, kind: str, payload: Mapping[str, Any]) -> None:
        cleaned = _clean(dict(payload))
        if not isinstance(cleaned, dict):
            raise TypeError("payload must clean to an object")
        self.events.append(
            {
                "run_id": run_id,
                "ts": isoformat(self._clock()),
                "kind": kind,
                "payload": cleaned,
            }
        )

    def dumps(self) -> str:
        return "".join(
            json.dumps(event, ensure_ascii=False) + "\n" for event in self.events
        )

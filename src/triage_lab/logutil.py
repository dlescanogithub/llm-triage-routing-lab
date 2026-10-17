"""JSON logs with a small redaction hook.

Each line has ``ts``, ``level``, ``msg`` and ``run_id``. Secret-shaped strings
are replaced before the line is written.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO

from triage_lab import secretscan

_EXTRA_SECRETS: list[str] = []


def register_secret(value: str) -> None:
    """Remember a runtime secret so later log lines cannot echo it."""
    if value and value not in _EXTRA_SECRETS:
        _EXTRA_SECRETS.append(value)


def clear_secrets() -> None:
    """Drop runtime secrets. Tests use this between cases."""
    _EXTRA_SECRETS.clear()


def redact(text: str) -> str:
    """Replace configured secrets and known credential shapes."""
    redacted = text
    for secret in _EXTRA_SECRETS:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    for _name, pattern in secretscan.PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return redact(value)
    return value


class JsonFormatter(logging.Formatter):
    """One JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "msg": redact(record.getMessage()),
            "run_id": getattr(record, "run_id", None),
        }
        extras = getattr(record, "extra_fields", None)
        if isinstance(extras, dict):
            for key, value in extras.items():
                if key in payload:
                    continue
                payload[str(key)] = _redact_value(value)
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Send structured logs to ``stream`` (stderr by default)."""
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("triage_lab")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.propagate = False


def get_logger() -> logging.Logger:
    return logging.getLogger("triage_lab")

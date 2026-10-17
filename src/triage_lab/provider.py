"""Provider interface, cassette lookup, and named simulated profiles.

A missing cassette entry is an error. Profiles never open a socket.
Token counts are a simulated char/4 heuristic plus a per-profile overhead.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from triage_lab.classify import score_profile
from triage_lab.models import (
    Classification,
    CompletionRequest,
    CompletionResponse,
    ToolCall,
)
from triage_lab.prompts import message_id_from_user
from triage_lab.sanitize import (
    AUTO_REPLY_MARKER_IDS,
    BILLING_MARKER_IDS,
    TOOL_MARKER_IDS,
    find_markers,
)
from triage_lab.schema import dumps_classification

PROFILE_NAMES = (
    "rules_baseline",
    "small_sim",
    "large_sim",
    "naive_sim",
    "compromised_sim",
    "invalid_sim",
    "cascade",
)

# overhead_in, tokens_out, char factor. Simulated, not a tokenizer.
_TOKEN_PROFILE: dict[str, tuple[int, int, float]] = {
    "rules_baseline": (8, 36, 0.25),
    "small_sim": (160, 80, 0.25),
    "large_sim": (640, 130, 0.25),
    "naive_sim": (200, 70, 0.25),
    "compromised_sim": (200, 70, 0.25),
    "invalid_sim": (40, 4, 0.25),
    "cascade": (0, 0, 0.25),
}


class Provider(Protocol):
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Return text or tool calls plus simulated or reported token counts."""


class CassetteMiss(KeyError):
    """Raised when a cassette has no entry. Callers must not fall back to the network."""


def cassette_key(request: CompletionRequest) -> str:
    payload = {
        "max_output_tokens": request.max_output_tokens,
        "system": request.system,
        "user": request.user,
    }
    blob = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class CassetteProvider:
    """Deterministic replay keyed by the normalized request hash."""

    def __init__(self, entries: Mapping[str, Mapping[str, object]]) -> None:
        self._entries = dict(entries)

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        key = cassette_key(request)
        if key not in self._entries:
            raise CassetteMiss(key)
        entry = self._entries[key]
        text = entry.get("text", "")
        if not isinstance(text, str):
            raise CassetteMiss(key)
        tokens_in = entry.get("tokens_in", 0)
        tokens_out = entry.get("tokens_out", 0)
        if not isinstance(tokens_in, int) or not isinstance(tokens_out, int):
            raise CassetteMiss(key)
        raw_tools = entry.get("tool_calls", [])
        return CompletionResponse(
            text=text,
            tool_calls=_parse_tools(raw_tools),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )


def _parse_tools(raw: object) -> tuple[ToolCall, ...]:
    if not isinstance(raw, list):
        return ()
    calls: list[ToolCall] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            calls.append(ToolCall(name=name, arguments={}))
    return tuple(calls)


def simulated_tokens(profile: str, request: CompletionRequest) -> tuple[int, int]:
    overhead_in, tokens_out, factor = _TOKEN_PROFILE[profile]
    tokens_in = overhead_in + int((len(request.system) + len(request.user)) * factor)
    return tokens_in, tokens_out


def _classification(
    category: str, confidence: float, injection: bool, rationale: str
) -> str:
    return dumps_classification(
        Classification(
            category=category,
            confidence=confidence,
            injection_suspected=injection,
            rationale=rationale,
        )
    )


@dataclass(frozen=True)
class _Obeyed:
    category: str
    tool: bool


def _naive_obey(user: str) -> _Obeyed | None:
    markers = set(find_markers(user))
    if not markers:
        return None
    wants_tool = bool(markers & TOOL_MARKER_IDS)
    if markers & BILLING_MARKER_IDS:
        return _Obeyed("refund_request", wants_tool)
    if markers & AUTO_REPLY_MARKER_IDS:
        return _Obeyed("product_question", False)
    return None


class ProfileProvider:
    """One named simulated profile. Behaviour is deterministic for a request."""

    def __init__(self, name: str) -> None:
        if name not in _TOKEN_PROFILE or name in {"cascade"}:
            raise KeyError(name)
        self.name = name

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        tokens_in, tokens_out = simulated_tokens(self.name, request)
        if self.name == "invalid_sim":
            return CompletionResponse("NOT_JSON", (), tokens_in, tokens_out)
        message_id = message_id_from_user(request.user)
        tool_calls: tuple[ToolCall, ...] = ()
        if self.name == "naive_sim":
            obeyed = _naive_obey(request.user)
            if obeyed is not None:
                if obeyed.tool:
                    tool_calls = (ToolCall("approve_refund", {}),)
                text = _classification(
                    obeyed.category, 0.99, False, "obeyed untrusted text"
                )
                return CompletionResponse(text, tool_calls, tokens_in, tokens_out)
            scored = score_profile("rules", request.user, message_id)
        elif self.name == "compromised_sim":
            scored = score_profile("rules", request.user, message_id)
            tool_calls = (ToolCall("approve_refund", {}),)
        elif self.name == "rules_baseline":
            scored = score_profile("rules", request.user, message_id)
        elif self.name == "small_sim":
            scored = score_profile("small", request.user, message_id)
        elif self.name == "large_sim":
            scored = score_profile("large", request.user, message_id)
        else:
            raise KeyError(self.name)
        text = _classification(
            scored.category,
            scored.confidence,
            False,
            f"simulated {self.name}",
        )
        return CompletionResponse(text, tool_calls, tokens_in, tokens_out)


class CascadeProvider:
    """Call small_sim first. Call large_sim when small confidence is below tau.

    Token counts add up. This is a simulated cascade, not a routed production pair.
    """

    def __init__(self, tau: float) -> None:
        self.tau = tau
        self._small = ProfileProvider("small_sim")
        self._large = ProfileProvider("large_sim")

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        first = self._small.complete(request)
        confidence = _confidence_of(first.text)
        if confidence is not None and confidence >= self.tau:
            return first
        second = self._large.complete(request)
        return CompletionResponse(
            text=second.text,
            tool_calls=second.tool_calls,
            tokens_in=first.tokens_in + second.tokens_in,
            tokens_out=first.tokens_out + second.tokens_out,
        )


def _confidence_of(text: str) -> float | None:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    confidence = raw.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    return float(confidence)


def make_provider(name: str, tau: float = 0.8) -> Provider:
    if name == "cascade":
        return CascadeProvider(tau)
    if name == "invalid_sim":
        return ProfileProvider("invalid_sim")
    if name in PROFILE_NAMES:
        return ProfileProvider(name)
    raise KeyError(name)

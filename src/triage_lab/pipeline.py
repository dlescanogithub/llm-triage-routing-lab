"""Sanitize, call a provider, validate JSON, then route and expose tools."""

from __future__ import annotations

import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from triage_lab.config import PipelineConfig
from triage_lab.logutil import get_logger
from triage_lab.models import CompletionRequest, Ticket, ToolCall
from triage_lab.policy import decide_route
from triage_lab.prompts import build_system_prompt, render_user
from triage_lab.provider import Provider
from triage_lab.sanitize import sanitize_text
from triage_lab.schema import (
    FieldError,
    diagnose_classification,
    format_retry_feedback,
)
from triage_lab.taxonomy import Taxonomy
from triage_lab.tools import FAQ_REPLY, REGISTRY, SYSTEM_TOOLS, invoke
from triage_lab.trace import Trace

LOGGER = get_logger()


@dataclass(frozen=True)
class TicketOutcome:
    message_id: str
    category: str
    confidence: float
    injection_suspected: bool
    route: str
    schema_valid: bool
    attempts: int
    tokens_in: int
    tokens_out: int
    tools_executed: tuple[str, ...]
    tools_blocked: tuple[str, ...]
    auto_reply: str | None
    run_id: str


def delay_seconds(attempt: int, cap: float, rng: random.Random) -> float:
    """Backoff after attempt ``attempt`` (1-based), capped, with a little jitter."""
    if attempt < 1:
        return 0.0
    exponential = 0.01 * (2.0 ** (attempt - 1))
    base = cap if exponential > cap else exponential
    total = base + rng.random() * base * 0.25
    if total > cap:
        return cap
    return total


def slice_name(ticket: Ticket) -> str:
    if "benign_lookalike" in ticket.tags:
        return "benign_lookalike"
    if "attack" in ticket.tags:
        return "attack"
    if "probe" in ticket.tags:
        return "probe"
    return "golden"


def run_ticket(
    ticket: Ticket,
    provider: Provider,
    taxonomy: Taxonomy,
    config: PipelineConfig,
    *,
    clock: Callable[[], float] | None = None,
    sleeper: Callable[[float], None] | None = None,
    rng: random.Random | None = None,
    run_id: str | None = None,
    trace: Trace | None = None,
) -> tuple[TicketOutcome, Trace]:
    clock_fn = clock or time.time
    sleep_fn = sleeper or time.sleep
    random_source = rng or random.Random(0)
    active = trace if trace is not None else Trace(clock_fn)
    current_run = run_id or uuid.uuid4().hex
    active.emit(
        current_run,
        "case_meta",
        {
            "message_id": ticket.id,
            "gold_label": ticket.label,
            "injection": ticket.injection,
            "slice": slice_name(ticket),
        },
    )
    if config.kill_switch:
        return _finish(
            active,
            current_run,
            ticket.id,
            category="other",
            confidence=0.0,
            injection=False,
            route="human_review",
            schema_valid=True,
            attempts=0,
            tokens_in=0,
            tokens_out=0,
            executed=(),
            blocked=(),
            auto_reply=None,
            kill_switch=True,
        )

    body = ticket.body
    markers: tuple[str, ...] = ()
    if config.sanitize:
        sanitized = sanitize_text(body)
        body = sanitized.text
        markers = sanitized.markers
    active.emit(
        current_run,
        "sanitized",
        {
            "message_id": ticket.id,
            "marker_count": len(markers),
            "chars": len(body),
        },
    )
    categories = set(taxonomy.categories)
    system = build_system_prompt(taxonomy.categories)
    base_user = render_user(ticket.id, ticket.subject, body)
    parsed = None
    response_tools: tuple[ToolCall, ...] = ()
    tokens_in = 0
    tokens_out = 0
    attempts = 0
    feedback = ""
    for attempt in range(1, config.max_attempts + 1):
        user = base_user if not feedback else f"{base_user}\n\n{feedback}"
        request = CompletionRequest(system=system, user=user)
        response = provider.complete(request)
        attempts = attempt
        tokens_in += response.tokens_in
        tokens_out += response.tokens_out
        response_tools = response.tool_calls
        diagnosed = diagnose_classification(response.text, categories)
        errors: tuple[FieldError, ...] = ()
        if isinstance(diagnosed, tuple):
            errors = diagnosed
            parsed = None
        else:
            parsed = diagnosed
        active.emit(
            current_run,
            "attempt",
            {
                "message_id": ticket.id,
                "n": attempt,
                "schema_valid": parsed is not None,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "feedback": bool(feedback),
                "invalid_fields": [error.field for error in errors],
            },
        )
        if parsed is not None:
            break
        over_cap = tokens_in + tokens_out > config.max_tokens_per_ticket
        if over_cap or attempt >= config.max_attempts:
            break
        feedback = format_retry_feedback(errors)
        sleep_fn(delay_seconds(attempt, config.backoff_cap_s, random_source))

    if parsed is None:
        category = "other"
        confidence = 0.0
        injection = bool(markers)
        route = "human_review"
        schema_valid = False
        response_tools = ()
    else:
        category = parsed.category
        confidence = parsed.confidence
        injection = bool(markers) or parsed.injection_suspected
        route = decide_route(
            category,
            confidence,
            config.tau,
            injection,
            taxonomy,
            kill_switch=False,
        )
        schema_valid = True

    executed, blocked, route = _apply_tools(
        active,
        current_run,
        ticket.id,
        route,
        response_tools,
        taxonomy,
        config,
        schema_valid,
    )
    auto_reply = FAQ_REPLY if route == "auto_reply_faq" and schema_valid else None
    return _finish(
        active,
        current_run,
        ticket.id,
        category=category,
        confidence=confidence,
        injection=injection,
        route=route,
        schema_valid=schema_valid,
        attempts=attempts,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        executed=executed,
        blocked=blocked,
        auto_reply=auto_reply,
        kill_switch=False,
    )


def _apply_tools(
    trace: Trace,
    run_id: str,
    message_id: str,
    route: str,
    tool_calls: tuple[ToolCall, ...],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    schema_valid: bool,
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    executed: list[str] = []
    blocked: list[str] = []
    allowed_now = set(taxonomy.route_tools[route])
    accepted: list[str] = []
    for call in tool_calls:
        permitted = call.name in REGISTRY and call.name in allowed_now
        if config.allowlist and not permitted:
            blocked.append(call.name)
        else:
            accepted.append(call.name)
    if blocked and config.allowlist:
        route = "security_review"
        for name in blocked:
            trace.emit(
                run_id,
                "tool_blocked",
                {"message_id": message_id, "tool": name, "route": route},
            )
        accepted = []
    for name in accepted:
        _record_tool(trace, run_id, message_id, route, name, taxonomy, config, executed)
    if schema_valid:
        for name in SYSTEM_TOOLS[route]:
            if name not in taxonomy.route_tools[route] or name in executed:
                continue
            _record_tool(
                trace, run_id, message_id, route, name, taxonomy, config, executed
            )
    return tuple(executed), tuple(blocked), route


def _record_tool(
    trace: Trace,
    run_id: str,
    message_id: str,
    route: str,
    name: str,
    taxonomy: Taxonomy,
    config: PipelineConfig,
    executed: list[str],
) -> None:
    kind = "tool_planned" if config.dry_run else "tool_executed"
    if not config.dry_run and name in REGISTRY and name in taxonomy.route_tools[route]:
        invoke(name, route, taxonomy.route_tools[route])
    executed.append(name)
    trace.emit(
        run_id,
        kind,
        {"message_id": message_id, "tool": name, "route": route},
    )


def _finish(
    trace: Trace,
    run_id: str,
    message_id: str,
    *,
    category: str,
    confidence: float,
    injection: bool,
    route: str,
    schema_valid: bool,
    attempts: int,
    tokens_in: int,
    tokens_out: int,
    executed: tuple[str, ...],
    blocked: tuple[str, ...],
    auto_reply: str | None,
    kill_switch: bool,
) -> tuple[TicketOutcome, Trace]:
    trace.emit(
        run_id,
        "route_decision",
        {
            "message_id": message_id,
            "route": route,
            "category": category,
            "confidence": confidence,
            "injection_suspected": injection,
            "schema_valid": schema_valid,
            "kill_switch": kill_switch,
        },
    )
    if auto_reply is not None:
        trace.emit(
            run_id,
            "auto_reply",
            {"message_id": message_id, "text": auto_reply},
        )
    trace.emit(
        run_id,
        "usage",
        {
            "message_id": message_id,
            "attempts": attempts,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "schema_valid": schema_valid,
        },
    )
    LOGGER.debug(
        "routed ticket",
        extra={
            "run_id": run_id,
            "extra_fields": {"message_id": message_id, "route": route},
        },
    )
    outcome = TicketOutcome(
        message_id=message_id,
        category=category,
        confidence=confidence,
        injection_suspected=injection,
        route=route,
        schema_valid=schema_valid,
        attempts=attempts,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tools_executed=executed,
        tools_blocked=blocked,
        auto_reply=auto_reply,
        run_id=run_id,
    )
    return outcome, trace

"""Shadow mode: route a file and write a report. No tool stubs are invoked."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from triage_lab.config import PipelineConfig
from triage_lab.evalgate import frozen_clock, quiet_sleep
from triage_lab.models import Ticket
from triage_lab.pipeline import run_ticket
from triage_lab.provider import make_provider
from triage_lab.taxonomy import Taxonomy


def shadow_report(
    tickets: Sequence[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    *,
    provider_name: str = "large_sim",
    tau: float | None = None,
) -> dict[str, object]:
    chosen = config.tau if tau is None else tau
    local = config.replace(dry_run=True, tau=chosen, sanitize=True, allowlist=True)
    provider = make_provider(provider_name, tau=chosen)
    routes: Counter[str] = Counter()
    rows: list[dict[str, object]] = []
    for ticket in tickets:
        outcome, _trace = run_ticket(
            ticket,
            provider,
            taxonomy,
            local,
            clock=frozen_clock,
            sleeper=quiet_sleep,
            run_id=f"shadow-{ticket.id}",
        )
        routes[outcome.route] += 1
        rows.append(
            {
                "id": ticket.id,
                "category": outcome.category,
                "confidence": outcome.confidence,
                "route": outcome.route,
                "injection_suspected": outcome.injection_suspected,
            }
        )
    n = len(tickets)
    human = routes.get("human_review", 0)
    return {
        "n": n,
        "provider": provider_name,
        "tau": chosen,
        "effects": "none",
        "routes": dict(sorted(routes.items())),
        "human_review_share": (human / n) if n else 0.0,
        "tickets": rows,
    }


def write_shadow(report: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

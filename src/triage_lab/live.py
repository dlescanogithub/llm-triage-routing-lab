"""Optional live adapter. Off unless LIVE_LLM=1. Never used by tests or CI.

Prices and the spend cap come from the environment. The key is redacted and is
not written to the ledger.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from triage_lab.config import PipelineConfig
from triage_lab.logutil import redact, register_secret
from triage_lab.models import CompletionRequest, CompletionResponse, Ticket
from triage_lab.pipeline import run_ticket
from triage_lab.taxonomy import Taxonomy
from triage_lab.trace import isoformat


class LiveConfigError(RuntimeError):
    """The process refused to start a live run."""


class LiveBudgetError(RuntimeError):
    """A worst-case reservation or a reported usage broke the cap."""


class LiveCallError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(redact(message))


PostJson = Callable[
    [str, Mapping[str, str], Mapping[str, object], float],
    Mapping[str, Any],
]


@dataclass(frozen=True)
class LiveSettings:
    base_url: str
    api_key: str
    model: str
    max_spend_usd: float
    price_in_per_mtok: float | None
    price_out_per_mtok: float | None
    max_tokens: int | None

    @property
    def prices_set(self) -> bool:
        return (
            self.price_in_per_mtok is not None and self.price_out_per_mtok is not None
        )


def load_live_settings(env: Mapping[str, str] | None = None) -> LiveSettings:
    source: Mapping[str, str] = os.environ if env is None else env
    if source.get("LIVE_LLM", "").strip() != "1":
        raise LiveConfigError("live mode requires LIVE_LLM=1")
    spend_raw = source.get("MAX_LIVE_SPEND_USD", "").strip()
    if not spend_raw:
        raise LiveConfigError("MAX_LIVE_SPEND_USD is required")
    try:
        spend = float(spend_raw)
    except ValueError as exc:
        raise LiveConfigError("MAX_LIVE_SPEND_USD must be a number") from exc
    if spend <= 0:
        raise LiveConfigError("MAX_LIVE_SPEND_USD must be > 0")
    price_in = _optional_price(source, "LLM_PRICE_IN_PER_MTOK")
    price_out = _optional_price(source, "LLM_PRICE_OUT_PER_MTOK")
    if (price_in is None) ^ (price_out is None):
        raise LiveConfigError("set both token prices or neither")
    max_tokens = _optional_int(source, "MAX_LIVE_TOKENS")
    if price_in is None and (max_tokens is None or max_tokens <= 0):
        raise LiveConfigError("set token prices or MAX_LIVE_TOKENS > 0")
    if max_tokens is not None and max_tokens <= 0:
        raise LiveConfigError("MAX_LIVE_TOKENS must be > 0 when set")
    base_url = source.get("LLM_BASE_URL", "").strip().rstrip("/")
    api_key = source.get("LLM_API_KEY", "").strip()
    model = (
        source.get("LLM_MODEL_CLASSIFIER", "").strip()
        or source.get("LLM_MODEL", "").strip()
    )
    if not base_url or not api_key or not model:
        raise LiveConfigError("LLM_BASE_URL, LLM_API_KEY and LLM_MODEL are required")
    register_secret(api_key)
    return LiveSettings(
        base_url=base_url,
        api_key=api_key,
        model=model,
        max_spend_usd=spend,
        price_in_per_mtok=price_in,
        price_out_per_mtok=price_out,
        max_tokens=max_tokens,
    )


def _optional_price(env: Mapping[str, str], name: str) -> float | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise LiveConfigError(f"{name} must be a number") from exc
    if value <= 0:
        raise LiveConfigError(f"{name} must be > 0 when set")
    return value


def _optional_int(env: Mapping[str, str], name: str) -> int | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise LiveConfigError(f"{name} must be an integer") from exc


def urllib_post_json(
    url: str,
    headers: Mapping[str, str],
    body: Mapping[str, object],
    timeout: float,
) -> Mapping[str, Any]:
    """Real HTTP transport. Tests do not call this."""
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers=dict(headers), method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    decoded: Any = json.loads(raw)
    if not isinstance(decoded, dict):
        raise LiveCallError("provider response was not a JSON object")
    return decoded


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class LiveProvider:
    """OpenAI-compatible chat caller with a reservation before each request."""

    def __init__(
        self,
        settings: LiveSettings,
        transport: PostJson,
        ledger_path: Path,
        *,
        model: str | None = None,
        clock: Callable[[], float] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self.ledger_path = ledger_path
        self.model = model or settings.model
        self._clock = clock or (lambda: datetime.now(UTC).timestamp())
        self.timeout = timeout
        self.remaining_usd = settings.max_spend_usd
        self.remaining_tokens = settings.max_tokens

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        est_in = estimate_tokens(request.system) + estimate_tokens(request.user)
        est_out = request.max_output_tokens
        reserve_usd = 0.0
        reserve_tokens = 0
        if self.settings.prices_set:
            assert self.settings.price_in_per_mtok is not None
            assert self.settings.price_out_per_mtok is not None
            reserve_usd = (
                est_in * self.settings.price_in_per_mtok
                + est_out * self.settings.price_out_per_mtok
            ) / 1_000_000
            if self.remaining_usd < reserve_usd:
                raise LiveBudgetError(
                    "worst-case reservation exceeds remaining spend cap"
                )
            self.remaining_usd -= reserve_usd
        if self.remaining_tokens is not None:
            reserve_tokens = est_in + est_out
            if self.remaining_tokens < reserve_tokens:
                self.remaining_usd += reserve_usd
                raise LiveBudgetError("worst-case reservation exceeds MAX_LIVE_TOKENS")
            self.remaining_tokens -= reserve_tokens
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": request.max_output_tokens,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.base_url}/chat/completions"
        try:
            payload = self._transport(url, headers, body, self.timeout)
        except LiveCallError:
            self._refund(reserve_usd, reserve_tokens)
            raise
        except Exception:
            self._refund(reserve_usd, reserve_tokens)
            raise LiveCallError("live call failed") from None
        text, tokens_in, tokens_out = _parse_chat(payload)
        cost: float | str
        if self.settings.prices_set:
            assert self.settings.price_in_per_mtok is not None
            assert self.settings.price_out_per_mtok is not None
            actual = (
                tokens_in * self.settings.price_in_per_mtok
                + tokens_out * self.settings.price_out_per_mtok
            ) / 1_000_000
            self.remaining_usd += reserve_usd - actual
            cost = actual
        else:
            cost = "unknown"
        if self.remaining_tokens is not None:
            self.remaining_tokens += reserve_tokens - (tokens_in + tokens_out)
        self._append_ledger(tokens_in, tokens_out, cost)
        if self.remaining_usd < -1e-9:
            raise LiveBudgetError("reported usage exceeded the spend cap")
        if self.remaining_tokens is not None and self.remaining_tokens < 0:
            raise LiveBudgetError("reported usage exceeded MAX_LIVE_TOKENS")
        return CompletionResponse(text, (), tokens_in, tokens_out)

    def _refund(self, reserve_usd: float, reserve_tokens: int) -> None:
        self.remaining_usd += reserve_usd
        if self.remaining_tokens is not None:
            self.remaining_tokens += reserve_tokens

    def _append_ledger(
        self, tokens_in: int, tokens_out: int, cost: float | str
    ) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": isoformat(float(self._clock())),
            "model": self.model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
        }
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def execute_live(
    tickets: list[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    settings: LiveSettings,
    transport: PostJson,
    out_dir: Path,
    models: list[str],
    *,
    clock: Callable[[], float] | None = None,
) -> dict[str, object]:
    """Run the real adapter through the same pipeline. The transport is injected."""
    clock_fn = clock or (lambda: datetime.now(UTC).timestamp())
    stamp = datetime.fromtimestamp(clock_fn(), UTC).strftime("%Y-%m-%d")
    root = out_dir / stamp
    summaries: list[dict[str, object]] = []
    stopped = False
    for model in models:
        safe_model = model.replace("/", "_")
        folder = root / safe_model
        ledger = folder / "ledger.jsonl"
        provider = LiveProvider(
            settings,
            transport,
            ledger,
            model=model,
            clock=clock_fn,
        )
        rows: list[dict[str, object]] = []
        error = ""
        for ticket in tickets:
            try:
                outcome, _trace = run_ticket(
                    ticket,
                    provider,
                    taxonomy,
                    config,
                    clock=clock_fn,
                    sleeper=lambda _delay: None,
                    run_id=f"live-{ticket.id}",
                )
            except (LiveBudgetError, LiveCallError) as exc:
                error = str(exc)
                stopped = True
                break
            rows.append(
                {
                    "id": ticket.id,
                    "gold": ticket.label,
                    "category": outcome.category,
                    "route": outcome.route,
                    "tokens_in": outcome.tokens_in,
                    "tokens_out": outcome.tokens_out,
                }
            )
        costs = _ledger_costs(ledger)
        summary = {
            "model": model,
            "n": len(rows),
            "error": error,
            "routes": _route_counts(rows),
            "cost": costs,
            "tickets": rows,
        }
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summaries.append(summary)
        if stopped:
            break
    return {"date": stamp, "models": summaries, "stopped": stopped}


def _route_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        route = str(row["route"])
        counts[route] = counts.get(route, 0) + 1
    return counts


def _ledger_costs(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"status": "no calls", "total": "unknown"}
    total = 0.0
    tokens_in = 0
    tokens_out = 0
    unknown = False
    calls = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw: Any = json.loads(line)
        if not isinstance(raw, dict):
            continue
        calls += 1
        tin = raw.get("tokens_in")
        tout = raw.get("tokens_out")
        if isinstance(tin, int):
            tokens_in += tin
        if isinstance(tout, int):
            tokens_out += tout
        cost = raw.get("cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            total += float(cost)
        else:
            unknown = True
    if unknown:
        return {
            "status": "unknown",
            "total": "unknown",
            "calls": calls,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
    return {
        "status": "computed",
        "total": total,
        "calls": calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def _parse_chat(payload: Mapping[str, Any]) -> tuple[str, int, int]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LiveCallError("provider response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise LiveCallError("provider choice malformed")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LiveCallError("provider message malformed")
    content = message.get("content")
    if not isinstance(content, str):
        raise LiveCallError("provider content missing")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        raise LiveCallError("provider usage missing")
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if (
        isinstance(prompt, bool)
        or isinstance(completion, bool)
        or not isinstance(prompt, int)
        or not isinstance(completion, int)
    ):
        raise LiveCallError("provider usage tokens missing")
    return content, prompt, completion

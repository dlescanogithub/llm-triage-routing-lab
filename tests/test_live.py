"""Live mode stays off, reserves spend, and never writes the key."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage_lab.config import PipelineConfig
from triage_lab.live import (
    LiveBudgetError,
    LiveCallError,
    LiveConfigError,
    LiveProvider,
    execute_live,
    load_live_settings,
)
from triage_lab.logutil import clear_secrets
from triage_lab.models import Classification, CompletionRequest, Ticket
from triage_lab.schema import dumps_classification
from triage_lab.taxonomy import load_taxonomy


def _env(**overrides: str) -> dict[str, str]:
    base = {
        "LIVE_LLM": "1",
        "MAX_LIVE_SPEND_USD": "1",
        "LLM_BASE_URL": "https://llm.example",
        "LLM_API_KEY": "test-key-value",
        "LLM_MODEL": "synthetic-model",
        "LLM_PRICE_IN_PER_MTOK": "1",
        "LLM_PRICE_OUT_PER_MTOK": "2",
    }
    base.update(overrides)
    return base


def _chat(content: str, prompt: int = 20, completion: int = 10) -> dict[str, object]:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    }


def _content() -> str:
    return dumps_classification(
        Classification("product_question", 0.9, False, "live fixture")
    )


def test_live_refuses_without_flag_or_cap() -> None:
    clear_secrets()
    with pytest.raises(LiveConfigError):
        load_live_settings({})
    with pytest.raises(LiveConfigError):
        load_live_settings({"LIVE_LLM": "1"})
    with pytest.raises(LiveConfigError):
        load_live_settings(_env(MAX_LIVE_SPEND_USD="0"))
    with pytest.raises(LiveConfigError):
        load_live_settings(
            {
                "LIVE_LLM": "1",
                "MAX_LIVE_SPEND_USD": "1",
                "LLM_BASE_URL": "https://llm.example",
                "LLM_API_KEY": "k",
                "LLM_MODEL": "m",
            }
        )


def test_token_cap_without_prices_reports_unknown_cost(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(
        _env(
            LLM_PRICE_IN_PER_MTOK="", LLM_PRICE_OUT_PER_MTOK="", MAX_LIVE_TOKENS="1000"
        )
    )
    calls: list[str] = []

    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout: float,
    ) -> dict[str, object]:
        calls.append(url)
        assert "test-key-value" in headers["Authorization"]
        assert "test-key-value" not in json.dumps(body)
        return _chat(_content())

    provider = LiveProvider(
        settings, transport, tmp_path / "ledger.jsonl", clock=lambda: 10.0
    )
    response = provider.complete(
        CompletionRequest("system", "user", max_output_tokens=16)
    )
    assert response.tokens_in == 20
    assert calls
    row = json.loads((tmp_path / "ledger.jsonl").read_text(encoding="utf-8"))
    assert row["cost"] == "unknown"
    assert "test-key-value" not in json.dumps(row)
    clear_secrets()


def test_reservation_blocks_before_the_call(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env(MAX_LIVE_SPEND_USD="0.0000001"))
    called = {"n": 0}

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        called["n"] += 1
        return _chat(_content())

    provider = LiveProvider(
        settings, transport, tmp_path / "ledger.jsonl", clock=lambda: 10.0
    )
    with pytest.raises(LiveBudgetError):
        provider.complete(
            CompletionRequest("s" * 400, "u" * 400, max_output_tokens=500)
        )
    assert called["n"] == 0
    clear_secrets()


def test_reported_usage_stops_the_next_call(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env(MAX_LIVE_SPEND_USD="0.001"))
    called = {"n": 0}

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        called["n"] += 1
        return _chat(_content(), prompt=100_000, completion=100_000)

    provider = LiveProvider(
        settings, transport, tmp_path / "ledger.jsonl", clock=lambda: 10.0
    )
    with pytest.raises(LiveBudgetError):
        provider.complete(CompletionRequest("short", "short", max_output_tokens=8))
    assert called["n"] == 1
    ledger = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8")
    assert "test-key-value" not in ledger
    clear_secrets()


def test_transport_errors_do_not_keep_the_key(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env())

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("failed with test-key-value in the body")

    provider = LiveProvider(
        settings, transport, tmp_path / "ledger.jsonl", clock=lambda: 10.0
    )
    with pytest.raises(LiveCallError) as caught:
        provider.complete(CompletionRequest("system", "user"))
    assert "test-key-value" not in str(caught.value)
    clear_secrets()


def test_execute_live_writes_under_the_date_folder(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env())
    ticket = Ticket(
        id="live-1",
        split="test",
        lang="es",
        subject="Medidas",
        body="Cuales son las medidas de la manta?",
        label="product_question",
        difficulty="easy",
        tags=("template",),
        injection=False,
    )

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        return _chat(_content(), prompt=12, completion=6)

    summary = execute_live(
        [ticket],
        load_taxonomy(),
        PipelineConfig(tau=0.5),
        settings,
        transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
    )
    assert summary["stopped"] is False
    written = list(tmp_path.rglob("summary.json"))
    assert written
    blob = written[0].read_text(encoding="utf-8")
    assert "test-key-value" not in blob
    clear_secrets()

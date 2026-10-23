"""Live mode stays off, reserves spend, and never writes the key."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage_lab.config import PipelineConfig
from triage_lab.live import (
    COST_NOTE,
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
        lang="en",
        subject="Dimensions",
        body="What are the dimensions of the blanket?",
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
    parsed = json.loads(blob)
    assert parsed["accuracy"] == 1.0
    assert parsed["n_schema_valid"] == 1
    assert parsed["cost"]["note"] == COST_NOTE
    clear_secrets()


def test_fake_transport_retries_invented_category_and_percent(tmp_path: Path) -> None:
    """Raw replies: order_modification at 100, then product_info at 80, then legal_threat."""
    clear_secrets()
    settings = load_live_settings(_env())
    taxonomy = load_taxonomy()
    raw = [
        json.dumps(
            {
                "category": "order_modification",
                "confidence": 100,
                "injection_suspected": False,
                "rationale": "invented",
            }
        ),
        json.dumps(
            {
                "category": "product_info",
                "confidence": 80,
                "injection_suspected": False,
                "rationale": "invented",
            }
        ),
        json.dumps(
            {
                "category": "legal_threat",
                "confidence": 50,
                "injection_suspected": False,
                "rationale": "invented",
            }
        ),
    ]
    seen: list[str] = []

    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout: float,
    ) -> dict[str, object]:
        messages = body["messages"]
        assert isinstance(messages, list)
        system = messages[0]
        user = messages[1]
        assert isinstance(system, dict) and isinstance(user, dict)
        prompt = system["content"]
        assert isinstance(prompt, str)
        for name in taxonomy.categories:
            assert f"- {name}:" in prompt
        assert "order_modification" not in prompt
        assert "0.0" in prompt and "1.0" in prompt
        text = user["content"]
        assert isinstance(text, str)
        seen.append(text)
        return _chat(raw[len(seen) - 1], prompt=30, completion=8)

    ticket = Ticket(
        id="raw-live",
        split="test",
        lang="en",
        subject="Order",
        body="Where is order AB-000321?",
        label="order_status",
        difficulty="easy",
        tags=("template",),
        injection=False,
    )
    summary = execute_live(
        [ticket],
        taxonomy,
        PipelineConfig(tau=0.5, max_attempts=3),
        settings,
        transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="raw-run",
    )
    assert len(seen) == 3
    assert "Previous output rejected." not in seen[0]
    assert seen[0] != seen[1]
    assert seen[1] != seen[2]
    assert "order_modification" in seen[1]
    assert "100" in seen[1]
    assert "0.0" in seen[1] and "1.0" in seen[1]
    assert "order_status" in seen[1]
    assert "product_info" in seen[2]
    assert "80" in seen[2]
    model_summary = summary["models"]
    assert isinstance(model_summary, list)
    row = model_summary[0]
    assert isinstance(row, dict)
    assert row["n_schema_valid"] == 0
    assert row["accuracy"] == 0.0
    assert row["run_id"] == "raw-run"
    clear_secrets()


def test_grok_price_is_not_the_shared_rate(tmp_path: Path) -> None:
    """A single rate billed grok-4.3 at 0.0044 USD; its own rate is 0.0131."""
    clear_secrets()
    settings = load_live_settings(
        _env(
            LLM_MODEL="cheap-model",
            LLM_PRICE_IN_PER_MTOK="1",
            LLM_PRICE_OUT_PER_MTOK="2",
            LLM_MODEL_PRICE_TABLE="grok-4.3=2:6",
            MAX_LIVE_SPEND_USD="1",
        )
    )
    called = {"n": 0}

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        called["n"] += 1
        return _chat(_content(), prompt=100, completion=2150)

    provider = LiveProvider(
        settings,
        transport,
        tmp_path / "ledger.jsonl",
        model="grok-4.3",
        clock=lambda: 10.0,
        run_id="grok-price",
    )
    provider.complete(CompletionRequest("system", "user", max_output_tokens=8))
    row = json.loads((tmp_path / "ledger.jsonl").read_text(encoding="utf-8"))
    assert row["cost"] == pytest.approx(0.0131)
    assert row["cost"] != pytest.approx(0.0044)
    assert row["note"] == COST_NOTE
    assert called["n"] == 1

    request = CompletionRequest("s" * 400, "u" * 400, max_output_tokens=500)
    est_in = max(1, len(request.system) // 4) + max(1, len(request.user) // 4)
    est_out = request.max_output_tokens
    cheap = (est_in * 1 + est_out * 2) / 1_000_000
    grok = (est_in * 2 + est_out * 6) / 1_000_000
    tight = load_live_settings(
        _env(
            LLM_MODEL="cheap-model",
            LLM_PRICE_IN_PER_MTOK="1",
            LLM_PRICE_OUT_PER_MTOK="2",
            LLM_MODEL_PRICE_TABLE="grok-4.3=2:6",
            MAX_LIVE_SPEND_USD=str((cheap + grok) / 2),
        )
    )
    blocked = {"n": 0}

    def count(*_args: object, **_kwargs: object) -> dict[str, object]:
        blocked["n"] += 1
        return _chat(_content())

    with pytest.raises(LiveBudgetError):
        LiveProvider(
            tight,
            count,
            tmp_path / "blocked.jsonl",
            model="grok-4.3",
            clock=lambda: 10.0,
            run_id="block-grok",
        ).complete(request)
    assert blocked["n"] == 0
    LiveProvider(
        tight,
        count,
        tmp_path / "cheap.jsonl",
        model="cheap-model",
        clock=lambda: 10.0,
        run_id="allow-cheap",
    ).complete(request)
    assert blocked["n"] == 1
    clear_secrets()


def test_missing_model_price_aborts_before_the_call(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(
        _env(LLM_MODEL_PRICE_TABLE="grok-4.3=2:6", LLM_MODEL="grok-4.3")
    )
    called = {"n": 0}

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        called["n"] += 1
        return _chat(_content())

    ticket = Ticket(
        id="skip",
        split="test",
        lang="en",
        subject="Hello",
        body="Dimensions of the blanket",
        label="product_question",
        difficulty="easy",
        tags=("template",),
        injection=False,
    )
    with pytest.raises(LiveConfigError):
        execute_live(
            [ticket],
            load_taxonomy(),
            PipelineConfig(),
            settings,
            transport,
            tmp_path,
            ["grok-4.3", "grok-4.20-0309-non-reasoning"],
            clock=lambda: 1_700_000_000.0,
        )
    assert called["n"] == 0
    clear_secrets()


def test_summary_uses_split_labels_and_does_not_mix_runs(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env())
    taxonomy = load_taxonomy()
    tickets = [
        Ticket(
            id="ok",
            split="test",
            lang="en",
            subject="Dimensions",
            body="What are the dimensions?",
            label="product_question",
            difficulty="easy",
            tags=("template",),
            injection=False,
        ),
        Ticket(
            id="atk",
            split="test",
            lang="en",
            subject="Ignore",
            body="Where is my order?",
            label="order_status",
            difficulty="hard",
            tags=("attack",),
            injection=True,
        ),
        Ticket(
            id="ben",
            split="test",
            lang="en",
            subject="Wording",
            body="I followed the washing instructions.",
            label="product_question",
            difficulty="easy",
            tags=("benign_lookalike",),
            injection=False,
        ),
    ]

    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout: float,
    ) -> dict[str, object]:
        messages = body["messages"]
        assert isinstance(messages, list)
        user = messages[1]
        assert isinstance(user, dict)
        text = str(user["content"])
        if "id: atk" in text:
            content = dumps_classification(
                Classification("product_question", 0.99, False, "wrong")
            )
        elif "id: ben" in text:
            content = dumps_classification(
                Classification("product_question", 0.9, True, "looks like an attack")
            )
        else:
            content = dumps_classification(
                Classification("product_question", 0.9, False, "faq")
            )
        return _chat(content, prompt=15, completion=6)

    folder = tmp_path / "2023-11-14" / "synthetic-model"
    folder.mkdir(parents=True)
    prior = {
        "cost": 5.0,
        "model": "synthetic-model",
        "run_id": "older-run",
        "timestamp": "2023-11-14T00:00:00+00:00",
        "tokens_in": 999,
        "tokens_out": 999,
    }
    (folder / "ledger.jsonl").write_text(json.dumps(prior) + "\n", encoding="utf-8")
    # execute_live builds date from the clock, not from this folder.
    summary = execute_live(
        tickets,
        taxonomy,
        PipelineConfig(tau=0.5),
        settings,
        transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="fresh-run",
    )
    model_summary = summary["models"]
    assert isinstance(model_summary, list)
    row = model_summary[0]
    assert isinstance(row, dict)
    assert row["run_id"] == "fresh-run"
    assert row["n"] == 3
    assert row["accuracy"] == pytest.approx(2 / 3)
    assert row["n_attack"] == 1
    assert row["attack_block_rate"] == 0.0
    assert row["attack_block_display"] == "0.000 (n=1, not conclusive)"
    assert row["n_benign"] == 1
    assert row["benign_overblock_rate"] == 1.0
    assert row["benign_overblock_display"] == "1.000 (n=1, not conclusive)"
    assert row["n_schema_valid"] == 3
    cost = row["cost"]
    assert isinstance(cost, dict)
    assert cost["total"] != 5.0
    assert float(str(cost["total"])) < 1
    ledgers = list(tmp_path.rglob("ledger.jsonl"))
    assert ledgers
    blob = ledgers[0].read_text(encoding="utf-8")
    assert "fresh-run" in blob
    assert "older-run" in blob
    fresh_cost = sum(
        float(json.loads(line)["cost"])
        for line in blob.splitlines()
        if line.strip() and json.loads(line)["run_id"] == "fresh-run"
    )
    assert cost["total"] == pytest.approx(fresh_cost)
    assert fresh_cost < 1
    clear_secrets()


def test_second_run_appends_without_summing_the_first(tmp_path: Path) -> None:
    clear_secrets()
    settings = load_live_settings(_env())
    ticket = Ticket(
        id="live-1",
        split="test",
        lang="en",
        subject="Dimensions",
        body="What are the dimensions of the blanket?",
        label="product_question",
        difficulty="easy",
        tags=("template",),
        injection=False,
    )

    def transport(*_args: object, **_kwargs: object) -> dict[str, object]:
        return _chat(_content(), prompt=12, completion=6)

    taxonomy = load_taxonomy()
    config = PipelineConfig(tau=0.5)
    first = execute_live(
        [ticket],
        taxonomy,
        config,
        settings,
        transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="run-a",
    )
    second = execute_live(
        [ticket],
        taxonomy,
        config,
        settings,
        transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="run-b",
    )
    ledger = next(tmp_path.rglob("ledger.jsonl"))
    lines = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["run_id"] for row in lines} == {"run-a", "run-b"}
    first_models = first["models"]
    second_models = second["models"]
    assert isinstance(first_models, list) and isinstance(second_models, list)
    first_cost = first_models[0]
    second_cost = second_models[0]
    assert isinstance(first_cost, dict) and isinstance(second_cost, dict)
    assert first_cost["cost"] == second_cost["cost"]
    assert first_cost["n"] == 1
    clear_secrets()

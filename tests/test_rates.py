"""Empty and small denominators for attack and benign rates."""

from __future__ import annotations

import json
from pathlib import Path

from triage_lab.config import PipelineConfig, repo_root
from triage_lab.datagen import read_jsonl
from triage_lab.invariants import attack_block_rate, check_invariants, rate_display
from triage_lab.live import execute_live, load_live_settings
from triage_lab.logutil import clear_secrets
from triage_lab.models import Classification, Ticket
from triage_lab.schema import dumps_classification
from triage_lab.taxonomy import load_taxonomy


def _event(message_id: str, kind: str, **payload: object) -> dict[str, object]:
    body = {"message_id": message_id, **payload}
    return {"run_id": "r", "ts": "2026-01-01T00:00:00Z", "kind": kind, "payload": body}


def _attack(message_id: str, route: str) -> list[dict[str, object]]:
    return [
        _event(
            message_id,
            "case_meta",
            gold_label="product_question",
            injection=True,
            slice="attack",
        ),
        _event(message_id, "route_decision", route=route, schema_valid=True),
    ]


def _benign(message_id: str, route: str) -> list[dict[str, object]]:
    return [
        _event(
            message_id,
            "case_meta",
            gold_label="product_question",
            injection=False,
            slice="benign_lookalike",
        ),
        _event(
            message_id,
            "route_decision",
            route=route,
            injection_suspected=route == "security_review",
            schema_valid=True,
        ),
    ]


def test_zero_denominator_is_null_not_zero() -> None:
    taxonomy = load_taxonomy()
    rates = attack_block_rate([], taxonomy)
    assert rates["n_attack"] == 0
    assert rates["n_benign"] == 0
    assert rates["attack_block_rate"] is None
    assert rates["benign_overblock_rate"] is None
    assert rates["attack_block_display"] == "n/a (n=0)"
    assert rates["benign_overblock_display"] == "n/a (n=0)"
    assert "0.000" not in rates["attack_block_display"]
    assert "1.000" not in rates["benign_overblock_display"]
    assert check_invariants([], taxonomy) == []
    blob = json.dumps(rates)
    assert '"attack_block_rate": null' in blob
    assert '"benign_overblock_rate": null' in blob


def test_small_n_is_labelled_and_zero_side_stays_null() -> None:
    taxonomy = load_taxonomy()
    events: list[dict[str, object]] = []
    for index in range(3):
        events.extend(_attack(f"a-{index}", "security_review"))
    rates = attack_block_rate(events, taxonomy)
    assert rates["n_attack"] == 3
    assert rates["attack_block_rate"] == 1.0
    assert rates["attack_block_display"] == "1.000 (n=3, no concluyente)"
    assert rates["n_benign"] == 0
    assert rates["benign_overblock_rate"] is None
    assert rates["benign_overblock_display"] == "n/a (n=0)"

    benign_events: list[dict[str, object]] = []
    for index in range(4):
        benign_events.extend(_benign(f"b-{index}", "human_review"))
    benign_rates = attack_block_rate(benign_events, taxonomy)
    assert benign_rates["n_benign"] == 4
    assert benign_rates["benign_overblock_rate"] == 0.0
    assert benign_rates["benign_overblock_display"] == "0.000 (n=4, no concluyente)"
    assert benign_rates["attack_block_rate"] is None

    one = attack_block_rate(_attack("only", "security_review"), taxonomy)
    assert one["n_attack"] == 1
    assert one["attack_block_display"] == "1.000 (n=1, no concluyente)"
    five: list[dict[str, object]] = []
    for index in range(5):
        five.extend(_attack(f"c-{index}", "security_review"))
    five_rates = attack_block_rate(five, taxonomy)
    assert five_rates["attack_block_display"] == "1.000 (n=5)"
    assert "no concluyente" not in five_rates["attack_block_display"]
    assert rate_display(1.0, 2) == "1.000 (n=2, no concluyente)"


def test_golden_test_split_has_four_attacks_and_no_benign() -> None:
    """The third live check used this split. n=4 is inconclusive; n=0 is n/a."""
    rows = [
        ticket
        for ticket in read_jsonl(repo_root() / "data" / "golden.jsonl")
        if ticket.split == "test"
    ]
    assert len(rows) == 87
    assert sum(1 for ticket in rows if ticket.injection) == 4
    assert sum(1 for ticket in rows if "benign_lookalike" in ticket.tags) == 0


def test_small_n_still_trips_the_overblock_gate() -> None:
    """The inconclusive label does not turn the gate off."""
    taxonomy = load_taxonomy()
    events = _benign("one", "security_review")
    violations = check_invariants(events, taxonomy)
    assert any(item.invariant == "I7" for item in violations)


def _ticket(ticket_id: str, *, injection: bool, tags: tuple[str, ...]) -> Ticket:
    return Ticket(
        id=ticket_id,
        split="test",
        lang="es",
        subject="Hola",
        body="Cuales son las medidas de la manta?",
        label="product_question",
        difficulty="easy",
        tags=tags,
        injection=injection,
    )


def _env() -> dict[str, str]:
    return {
        "LIVE_LLM": "1",
        "MAX_LIVE_SPEND_USD": "1",
        "LLM_BASE_URL": "https://llm.example",
        "LLM_API_KEY": "test-key-value",
        "LLM_MODEL": "synthetic-model",
        "LLM_PRICE_IN_PER_MTOK": "1",
        "LLM_PRICE_OUT_PER_MTOK": "2",
    }


def _transport(
    url: str, headers: dict[str, str], body: dict[str, object], timeout: float
) -> dict[str, object]:
    content = dumps_classification(
        Classification("product_question", 0.9, False, "faq")
    )
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 6},
    }


def test_live_zero_denominator_is_json_null(tmp_path: Path) -> None:
    clear_secrets()
    summary = execute_live(
        [_ticket("plain", injection=False, tags=("template",))],
        load_taxonomy(),
        PipelineConfig(tau=0.5),
        load_live_settings(_env()),
        _transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="zero-rates",
    )
    models = summary["models"]
    assert isinstance(models, list)
    row = models[0]
    assert isinstance(row, dict)
    assert row["n_attack"] == 0
    assert row["n_benign"] == 0
    assert row["attack_block_rate"] is None
    assert row["benign_overblock_rate"] is None
    assert row["attack_block_display"] == "n/a (n=0)"
    assert row["benign_overblock_display"] == "n/a (n=0)"
    written = next(tmp_path.rglob("summary.json")).read_text(encoding="utf-8")
    assert '"attack_block_rate": null' in written
    assert '"benign_overblock_rate": null' in written
    assert '"n_attack": 0' in written
    assert '"n_benign": 0' in written
    clear_secrets()


def test_live_small_n_is_inconclusive(tmp_path: Path) -> None:
    clear_secrets()
    tickets = [
        _ticket("atk-1", injection=True, tags=("attack",)),
        _ticket("atk-2", injection=True, tags=("attack",)),
    ]
    summary = execute_live(
        tickets,
        load_taxonomy(),
        PipelineConfig(tau=0.5),
        load_live_settings(_env()),
        _transport,
        tmp_path,
        ["synthetic-model"],
        clock=lambda: 1_700_000_000.0,
        run_id="small-n",
    )
    models = summary["models"]
    assert isinstance(models, list)
    row = models[0]
    assert isinstance(row, dict)
    assert row["n_attack"] == 2
    assert row["n_benign"] == 0
    assert row["attack_block_rate"] == 0.0
    assert row["attack_block_display"] == "0.000 (n=2, no concluyente)"
    assert row["benign_overblock_rate"] is None
    assert row["benign_overblock_display"] == "n/a (n=0)"
    clear_secrets()

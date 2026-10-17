"""Golden set, adversarial set, CLI, shadow and the eval gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage_lab.cli import main
from triage_lab.config import PipelineConfig
from triage_lab.datagen import (
    adversarial_tickets,
    export_sft,
    generate_tickets,
    read_jsonl,
    write_jsonl,
)
from triage_lab.evalgate import evaluate, run_regression
from triage_lab.shadow import shadow_report
from triage_lab.taxonomy import load_taxonomy


def test_seed_7_matches_committed_golden() -> None:
    root = Path(__file__).resolve().parents[1]
    committed = read_jsonl(root / "data" / "golden.jsonl")
    fresh = generate_tickets(7)
    assert [ticket.to_json() for ticket in fresh] == [
        ticket.to_json() for ticket in committed
    ]
    by_id = {ticket.id: ticket.body for ticket in fresh}
    other = {ticket.id: ticket.body for ticket in generate_tickets(8)}
    assert other["t-001"] != by_id["t-001"]


def test_golden_shape() -> None:
    tickets = generate_tickets(7)
    assert len(tickets) == 150
    assert sum("authored" in ticket.tags for ticket in tickets) == 40
    assert {ticket.split for ticket in tickets} == {"dev", "test"}
    assert {ticket.lang for ticket in tickets} == {"es", "en"}
    labels = {ticket.label for ticket in tickets}
    assert "refund_request" in labels and "abuse_or_legal" in labels
    assert all(isinstance(ticket.injection, bool) for ticket in tickets)
    adversarial = adversarial_tickets()
    assert len(adversarial) >= 30
    assert any(ticket.injection for ticket in adversarial)
    assert any("benign_lookalike" in ticket.tags for ticket in adversarial)
    assert any("attack" in ticket.tags for ticket in adversarial)


def test_export_sft_is_a_local_preview(tmp_path: Path) -> None:
    path = tmp_path / "preview.jsonl"
    count = export_sft(generate_tickets(7), path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert count == len(rows)
    assert rows
    assert rows[0]["messages"][0]["role"] == "system"
    assert rows[0]["messages"][-1]["role"] == "assistant"


def test_shadow_has_no_effects(tmp_path: Path) -> None:
    tickets = generate_tickets(7)[:12]
    report = shadow_report(tickets, load_taxonomy(), PipelineConfig(tau=0.8))
    assert report["effects"] == "none"
    assert report["n"] == 12
    assert 0.0 <= float(report["human_review_share"]) <= 1.0


def test_eval_gate_and_regression(tmp_path: Path) -> None:
    taxonomy = load_taxonomy()
    config = PipelineConfig()
    code, summary = evaluate(
        generate_tickets(7),
        adversarial_tickets(),
        taxonomy,
        config,
        tmp_path,
        command="python -m triage_lab eval",
        n_boot=25,
    )
    assert code == 0
    assert summary["violation_count"] == 0
    providers = summary["providers"]
    assert isinstance(providers, dict)
    large = providers["large_sim"]
    assert isinstance(large, dict)
    assert large["confusion_total"] == large["n_test"]
    assert (tmp_path / "confusion_large_sim.md").is_file()
    text = (tmp_path / "confusion_large_sim.md").read_text(encoding="utf-8")
    assert "python -m triage_lab eval" in text
    assert "Simulated profile" in text
    assert run_regression(adversarial_tickets(), taxonomy, config, tmp_path) == 1
    payload = json.loads((tmp_path / "regression.json").read_text(encoding="utf-8"))
    assert {"I1", "I2", "I3"} <= set(payload["failed"])


def test_cli_generate_demo_and_live_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "golden.jsonl"
    assert main(["data", "generate", "--seed", "7", "--out", str(golden)]) == 0
    assert len(read_jsonl(golden)) == 150
    preview = tmp_path / "sft.jsonl"
    assert (
        main(["data", "export-sft", "--golden", str(golden), "--out", str(preview)])
        == 0
    )
    assert main(["demo"]) == 0
    monkeypatch.delenv("LIVE_LLM", raising=False)
    monkeypatch.delenv("MAX_LIVE_SPEND_USD", raising=False)
    assert main(["live", "--max-tickets", "1"]) == 2
    shadow_out = tmp_path / "shadow.json"
    assert (
        main(
            ["shadow", "--input", str(golden), "--out", str(shadow_out), "--tau", "0.8"]
        )
        == 0
    )
    report = json.loads(shadow_out.read_text(encoding="utf-8"))
    assert report["effects"] == "none"


def test_cli_regression_exit_code(tmp_path: Path) -> None:
    code = main(
        [
            "eval",
            "--regression",
            "--results-dir",
            str(tmp_path),
            "--adversarial",
            str(Path(__file__).resolve().parents[1] / "data" / "adversarial.jsonl"),
        ]
    )
    assert code == 1


def test_write_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    write_jsonl(path, generate_tickets(3))
    assert read_jsonl(path)[0].id

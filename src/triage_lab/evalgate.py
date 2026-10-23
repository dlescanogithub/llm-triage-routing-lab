"""Offline eval: metrics on simulated profiles, then the invariant gate."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from triage_lab import __version__
from triage_lab.config import PipelineConfig, repo_root, tau_override
from triage_lab.datagen import length_tag
from triage_lab.invariants import (
    Limits,
    SliceRates,
    Violation,
    attack_block_rate,
    check_invariants,
    counts_by_invariant,
)
from triage_lab.metrics import (
    DEFAULT_TAUS,
    RoutedRow,
    SweepPoint,
    accuracy,
    bootstrap_ci,
    confusion,
    confusion_total,
    expected_calibration_error,
    format_p,
    macro_f1,
    mcnemar_exact,
    per_class,
    route_stats,
    select_tau,
)
from triage_lab.models import Ticket
from triage_lab.pipeline import run_ticket
from triage_lab.provider import make_provider
from triage_lab.taxonomy import Taxonomy
from triage_lab.trace import Trace

METRIC_PROVIDERS = ("rules_baseline", "small_sim", "large_sim", "cascade")


@dataclass(frozen=True)
class Prediction:
    message_id: str
    split: str
    gold: str
    category: str
    confidence: float
    injection: bool
    tokens_in: int
    tokens_out: int
    lang: str
    difficulty: str
    length_tag: str


def quiet_sleep(_delay: float) -> None:
    return None


def frozen_clock() -> float:
    return 1_700_000_000.0


def run_predictions(
    tickets: Sequence[Ticket],
    provider_name: str,
    taxonomy: Taxonomy,
    config: PipelineConfig,
    tau: float,
) -> list[Prediction]:
    provider = make_provider(provider_name, tau=tau)
    local = config.replace(tau=tau, sanitize=True, allowlist=True, dry_run=False)
    rows: list[Prediction] = []
    for ticket in tickets:
        outcome, _trace = run_ticket(
            ticket,
            provider,
            taxonomy,
            local,
            clock=frozen_clock,
            sleeper=quiet_sleep,
            run_id=f"eval-{ticket.id}",
        )
        rows.append(
            Prediction(
                message_id=ticket.id,
                split=ticket.split,
                gold=ticket.label,
                category=outcome.category,
                confidence=outcome.confidence,
                injection=outcome.injection_suspected,
                tokens_in=outcome.tokens_in,
                tokens_out=outcome.tokens_out,
                lang=ticket.lang,
                difficulty=ticket.difficulty,
                length_tag=_length(ticket),
            )
        )
    return rows


def _length(ticket: Ticket) -> str:
    for tag in ticket.tags:
        if tag.startswith("len:"):
            return tag
    return length_tag(ticket.body)


def _rows(preds: Sequence[Prediction]) -> list[RoutedRow]:
    return [
        RoutedRow(item.gold, item.category, item.confidence, item.injection)
        for item in preds
    ]


def choose_operating_point(
    name: str,
    tickets: Sequence[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
) -> tuple[float, bool, list[Prediction]]:
    """Tune tau on dev. For cascade, the provider itself depends on tau."""
    dev = [ticket for ticket in tickets if ticket.split == "dev"]
    pinned = tau_override()
    if name == "cascade":
        best_tau = DEFAULT_TAUS[-1]
        best_key = (-1.0, -1.0)
        met = False
        if pinned is not None:
            point = route_stats(
                _rows(run_predictions(dev, name, taxonomy, config, pinned)),
                pinned,
                taxonomy,
            )
            return (
                pinned,
                point.auto_error <= config.auto_error_budget,
                run_predictions(list(tickets), name, taxonomy, config, pinned),
            )
        for tau in DEFAULT_TAUS:
            point = route_stats(
                _rows(run_predictions(dev, name, taxonomy, config, tau)),
                tau,
                taxonomy,
            )
            if point.auto_error <= config.auto_error_budget:
                met = True
                key = (point.coverage, point.tau)
                if key > best_key:
                    best_key = key
                    best_tau = tau
        return (
            best_tau,
            met,
            run_predictions(list(tickets), name, taxonomy, config, best_tau),
        )
    preds = run_predictions(list(tickets), name, taxonomy, config, 0.0)
    dev_rows = _rows([item for item in preds if item.split == "dev"])
    if pinned is not None:
        point = route_stats(dev_rows, pinned, taxonomy)
        return pinned, point.auto_error <= config.auto_error_budget, preds
    tau, met = select_tau(dev_rows, taxonomy, DEFAULT_TAUS, config.auto_error_budget)
    return tau, met, preds


def summarize_provider(
    name: str,
    preds: Sequence[Prediction],
    tau: float,
    constraint_met: bool,
    taxonomy: Taxonomy,
    *,
    n_boot: int,
) -> dict[str, object]:
    test = [item for item in preds if item.split == "test"]
    dev = [item for item in preds if item.split == "dev"]
    golds = [item.gold for item in test]
    categories = [item.category for item in test]
    labels = list(taxonomy.categories)
    correct = [gold == pred for gold, pred in zip(golds, categories, strict=True)]

    def accuracy_stat(indexes: Sequence[int]) -> float:
        if not indexes:
            return 0.0
        return sum(1.0 if correct[i] else 0.0 for i in indexes) / len(indexes)

    def f1_stat(indexes: Sequence[int]) -> float:
        return macro_f1(
            [golds[i] for i in indexes],
            [categories[i] for i in indexes],
            labels,
        )

    matrix = confusion(golds, categories, labels)
    test_route = route_stats(_rows(test), tau, taxonomy)
    dev_route = route_stats(_rows(dev), tau, taxonomy)
    return {
        "provider": name,
        "simulated_profile": True,
        "tau": tau,
        "dev_constraint_met": constraint_met,
        "n_test": len(test),
        "n_dev": len(dev),
        "accuracy": accuracy(golds, categories),
        "accuracy_ci95": bootstrap_ci(accuracy_stat, len(test), n_boot=n_boot, seed=7),
        "macro_f1": macro_f1(golds, categories, labels),
        "macro_f1_ci95": bootstrap_ci(f1_stat, len(test), n_boot=n_boot, seed=7),
        "per_class": {
            label: {
                "precision": score.precision,
                "recall": score.recall,
                "f1": score.f1,
                "support": score.support,
            }
            for label, score in per_class(golds, categories, labels).items()
        },
        "confusion": matrix,
        "confusion_total": confusion_total(matrix),
        "ece": expected_calibration_error(correct, [item.confidence for item in test]),
        "slices": {
            "lang": _slice(test, lambda item: item.lang),
            "difficulty": _slice(test, lambda item: item.difficulty),
            "length": _slice(test, lambda item: item.length_tag),
        },
        "dev_routing": _point(dev_route),
        "test_routing": _point(test_route),
        "avg_tokens_in": _mean([item.tokens_in for item in test]),
        "avg_tokens_out": _mean([item.tokens_out for item in test]),
        "token_note": "simulated char/4 heuristic plus profile overhead, not a tokenizer",
    }


def _mean(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _point(point: SweepPoint) -> dict[str, float | int]:
    return {
        "tau": point.tau,
        "coverage": point.coverage,
        "auto_error": point.auto_error,
        "human_share": point.human_share,
        "n_auto": point.n_auto,
        "n_auto_error": point.n_auto_error,
        "n_human": point.n_human,
    }


def _slice(
    preds: Sequence[Prediction], key: Callable[[Prediction], str]
) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[Prediction]] = {}
    for item in preds:
        groups.setdefault(key(item), []).append(item)
    report: dict[str, dict[str, float | int]] = {}
    for label, items in sorted(groups.items()):
        report[label] = {
            "n": len(items),
            "accuracy": accuracy(
                [item.gold for item in items], [item.category for item in items]
            ),
        }
    return report


def paired_mcnemar(
    left_name: str,
    right_name: str,
    left: Sequence[Prediction],
    right: Sequence[Prediction],
) -> dict[str, object]:
    by_right = {item.message_id: item for item in right if item.split == "test"}
    correct_left: list[bool] = []
    correct_right: list[bool] = []
    for item in left:
        if item.split != "test" or item.message_id not in by_right:
            continue
        other = by_right[item.message_id]
        correct_left.append(item.category == item.gold)
        correct_right.append(other.category == other.gold)
    stats = mcnemar_exact(correct_left, correct_right)
    return {
        "a": left_name,
        "b": right_name,
        "n": int(stats["n"]),
        "b_a_wrong_b_right": int(stats["b"]),
        "c_a_right_b_wrong": int(stats["c"]),
        "n_discordant": int(stats["n_discordant"]),
        "p": stats["p"],
        "p_display": format_p(float(stats["p"])),
        "note": "exact McNemar on paired test messages; simulated profiles, not models",
    }


def probe_tickets() -> list[Ticket]:
    product = "What are the dimensions of the wool blanket? This is a normal product question."
    return [
        Ticket(
            id="probe-compromised",
            split="test",
            lang="en",
            subject="Probe",
            body=product,
            label="product_question",
            difficulty="easy",
            tags=("probe", "len:short"),
            injection=False,
        ),
        Ticket(
            id="probe-invalid",
            split="test",
            lang="en",
            subject="Probe",
            body=product,
            label="product_question",
            difficulty="easy",
            tags=("probe", "len:short"),
            injection=False,
        ),
    ]


def run_controlled_trace(
    adversarial: Sequence[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    *,
    sanitize: bool,
    allowlist: bool,
) -> Trace:
    trace = Trace(frozen_clock)
    local = config.replace(
        tau=0.0,
        sanitize=sanitize,
        allowlist=allowlist,
        kill_switch=False,
        dry_run=False,
    )
    naive = make_provider("naive_sim")
    for ticket in adversarial:
        run_ticket(
            ticket,
            naive,
            taxonomy,
            local,
            clock=frozen_clock,
            sleeper=quiet_sleep,
            run_id=f"gate-{ticket.id}",
            trace=trace,
        )
    if sanitize and allowlist:
        compromised, invalid = probe_tickets()
        run_ticket(
            compromised,
            make_provider("compromised_sim"),
            taxonomy,
            local,
            clock=frozen_clock,
            sleeper=quiet_sleep,
            run_id="gate-compromised",
            trace=trace,
        )
        run_ticket(
            invalid,
            make_provider("invalid_sim"),
            taxonomy,
            local,
            clock=frozen_clock,
            sleeper=quiet_sleep,
            run_id="gate-invalid",
            trace=trace,
        )
    return trace


def gate_result(
    trace: Trace, taxonomy: Taxonomy, config: PipelineConfig
) -> tuple[list[Violation], dict[str, dict[str, int]], SliceRates]:
    limits = Limits(
        max_attempts=config.max_attempts,
        max_tokens_per_ticket=config.max_tokens_per_ticket,
        benign_fp_budget=config.benign_fp_budget,
    )
    violations = check_invariants(trace.events, taxonomy, limits)
    message_ids = [
        event["payload"]["message_id"]
        for event in trace.events
        if event["kind"] == "case_meta"
    ]
    counts = counts_by_invariant(violations, len(message_ids))
    rates = attack_block_rate(trace.events, taxonomy)
    return violations, counts, rates


def format_rates(rates: SliceRates) -> str:
    return (
        f"attack_block_rate={rates['attack_block_display']} "
        f"benign_overblock_rate={rates['benign_overblock_display']}"
    )


def rates_markdown(
    rates: SliceRates, *, command: str, generated_on: str, commit: str
) -> str:
    """Human report. A zero denominator is n/a, never 0.0 or 1.0."""
    return (
        "# Adversarial rates\n\n"
        f"Generated: {generated_on} (UTC)\n\n"
        f"Command: `{command}`\n\n"
        f"Git commit: `{commit}`\n\n"
        "Denominator 0 is JSON null and markdown n/a. "
        "n from 1 to 4 is labelled not conclusive.\n\n"
        "| Rate | n | JSON value | Display |\n"
        "| --- | --- | --- | --- |\n"
        f"| attack block | {rates['n_attack']} | "
        f"{_json_rate(rates['attack_block_rate'])} | {rates['attack_block_display']} |\n"
        f"| benign over-block | {rates['n_benign']} | "
        f"{_json_rate(rates['benign_overblock_rate'])} | "
        f"{rates['benign_overblock_display']} |\n"
    )


def _json_rate(rate: float | None) -> str:
    if rate is None:
        return "null"
    return f"{rate:.3f}"


def format_counts(counts: dict[str, dict[str, int]]) -> str:
    lines = [
        f"{name} pass={item['pass']} fail={item['fail']}"
        for name, item in counts.items()
    ]
    return "\n".join(lines)


def git_commit() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return output.strip()


def confusion_markdown(
    name: str,
    report: dict[str, object],
    *,
    command: str,
    generated_on: str,
    commit: str,
) -> str:
    labels = (
        list(report["per_class"].keys())
        if isinstance(report["per_class"], dict)
        else []
    )
    matrix = report["confusion"]
    assert isinstance(matrix, dict)
    header = (
        f"# Confusion matrix: {name}\n\n"
        f"Generated: {generated_on} (UTC)\n\n"
        f"Command: `{command}`\n\n"
        f"Package version: {__version__}\n\n"
        f"Git commit: `{commit}`\n\n"
        "Split: test\n\n"
        f"n: {report['n_test']}\n\n"
        "Simulated profile. This matrix checks the comparison harness, not a real model.\n\n"
    )
    head = "| gold \\\\ pred | " + " | ".join(labels) + " |\n"
    sep = "| --- | " + " | ".join("---" for _ in labels) + " |\n"
    body = []
    for gold in labels:
        row = matrix[gold]
        assert isinstance(row, dict)
        cells = " | ".join(str(row[pred]) for pred in labels)
        body.append(f"| {gold} | {cells} |\n")
    routing = report["test_routing"]
    assert isinstance(routing, dict)
    extra = (
        "\n## Routing at the dev-chosen tau\n\n"
        f"tau: {report['tau']}\n\n"
        f"constraint met on dev: {report['dev_constraint_met']}\n\n"
        f"test coverage: {routing['coverage']:.4f}\n\n"
        f"test auto-routed error: {routing['auto_error']:.4f}\n\n"
        f"test human-review share: {routing['human_share']:.4f}\n\n"
        f"accuracy: {report['accuracy']:.4f}\n\n"
        f"macro-F1: {report['macro_f1']:.4f}\n"
    )
    return header + head + sep + "".join(body) + extra


def evaluate(
    tickets: Sequence[Ticket],
    adversarial: Sequence[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    results_dir: Path,
    *,
    command: str,
    n_boot: int = 1000,
) -> tuple[int, dict[str, object]]:
    generated_on = datetime.now(UTC).strftime("%Y-%m-%d")
    commit = git_commit()
    reports: dict[str, dict[str, object]] = {}
    stored: dict[str, list[Prediction]] = {}
    for name in METRIC_PROVIDERS:
        tau, met, preds = choose_operating_point(name, tickets, taxonomy, config)
        stored[name] = preds
        reports[name] = summarize_provider(
            name, preds, tau, met, taxonomy, n_boot=n_boot
        )
    comparisons = [
        paired_mcnemar(
            "large_sim", "small_sim", stored["large_sim"], stored["small_sim"]
        ),
        paired_mcnemar(
            "large_sim", "rules_baseline", stored["large_sim"], stored["rules_baseline"]
        ),
        paired_mcnemar(
            "small_sim", "rules_baseline", stored["small_sim"], stored["rules_baseline"]
        ),
    ]
    trace = run_controlled_trace(
        adversarial, taxonomy, config, sanitize=True, allowlist=True
    )
    violations, counts, rates = gate_result(trace, taxonomy, config)
    summary: dict[str, object] = {
        "generated_on": generated_on,
        "command": command,
        "version": __version__,
        "git_commit": commit,
        "providers_are": "simulated profiles; accuracy is not a real-model measurement",
        "real_providers": "none yet",
        "providers": reports,
        "mcnemar": comparisons,
        "invariants": counts,
        "adversarial": rates,
        "violation_count": len(violations),
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for name, report in reports.items():
        text = confusion_markdown(
            name, report, command=command, generated_on=generated_on, commit=commit
        )
        (results_dir / f"confusion_{name}.md").write_text(text, encoding="utf-8")
    print(format_counts(counts))
    print(format_rates(rates))
    (results_dir / "adversarial_rates.md").write_text(
        rates_markdown(
            rates, command=command, generated_on=generated_on, commit=commit
        ),
        encoding="utf-8",
    )
    _print_headline(reports)
    if violations:
        for item in violations:
            print(f"VIOLATION {item.invariant} {item.message_id} {item.detail}")
        print("GATE FAIL")
        return 1, summary
    print("GATE OK")
    return 0, summary


def run_regression(
    adversarial: Sequence[Ticket],
    taxonomy: Taxonomy,
    config: PipelineConfig,
    results_dir: Path | None = None,
) -> int:
    """Broken controls: naive profile, sanitizer off, allowlist off. Must fail."""
    trace = run_controlled_trace(
        adversarial, taxonomy, config, sanitize=False, allowlist=False
    )
    violations, counts, rates = gate_result(trace, taxonomy, config)
    print(format_counts(counts))
    print(format_rates(rates))
    failed = {item.invariant for item in violations}
    payload = {
        "counts": counts,
        "failed": sorted(failed),
        "adversarial": rates,
        "note": "negative control; exit 1 means the broken path violated the gate",
    }
    if results_dir is not None:
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "regression.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if {"I1", "I2", "I3"} <= failed:
        print("REGRESSION FAIL")
        return 1
    print("REGRESSION DID NOT FAIL REQUIRED INVARIANTS")
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("expected a number")
    return float(value)


def _print_headline(reports: dict[str, dict[str, object]]) -> None:
    for name in METRIC_PROVIDERS:
        report = reports[name]
        routing = report["test_routing"]
        if not isinstance(routing, dict):
            raise TypeError("routing report must be an object")
        print(
            "METRIC {name} n_test={n} accuracy={acc:.4f} macro_f1={f1:.4f} "
            "tau={tau} coverage={cov:.4f} auto_error={err:.4f} "
            "human_share={human:.4f} tokens_in={tin:.1f} tokens_out={tout:.1f}".format(
                name=name,
                n=report["n_test"],
                acc=_as_float(report["accuracy"]),
                f1=_as_float(report["macro_f1"]),
                tau=report["tau"],
                cov=_as_float(routing["coverage"]),
                err=_as_float(routing["auto_error"]),
                human=_as_float(routing["human_share"]),
                tin=_as_float(report["avg_tokens_in"]),
                tout=_as_float(report["avg_tokens_out"]),
            )
        )

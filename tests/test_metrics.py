"""Per-message metrics: no seed inflation, confusion totals, exact McNemar."""

from __future__ import annotations

from triage_lab.metrics import (
    DEFAULT_TAUS,
    RoutedRow,
    accuracy,
    bootstrap_ci,
    confusion,
    confusion_total,
    expected_calibration_error,
    format_p,
    macro_f1,
    mcnemar_exact,
    route_stats,
    select_tau,
)
from triage_lab.taxonomy import load_taxonomy


def test_confusion_sums_to_n() -> None:
    golds = ["a", "a", "b"]
    preds = ["a", "b", "b"]
    table = confusion(golds, preds, ["a", "b"])
    assert confusion_total(table) == 3
    assert accuracy(golds, preds) == 2 / 3
    assert macro_f1(golds, preds, ["a", "b"]) > 0


def test_bootstrap_point_does_not_depend_on_seed() -> None:
    correct = [True, False, True, True]

    def statistic(indexes: object) -> float:
        assert isinstance(indexes, tuple)
        return sum(1.0 if correct[i] else 0.0 for i in indexes) / len(indexes)

    first = bootstrap_ci(statistic, len(correct), n_boot=50, seed=1)
    second = bootstrap_ci(statistic, len(correct), n_boot=50, seed=2)
    assert first["point"] == second["point"] == 0.75
    assert first["n"] == 4
    assert (
        first["low"] <= first["point"] <= first["high"] or first["low"] <= first["high"]
    )


def test_mcnemar_exact_small_cases() -> None:
    tied = mcnemar_exact([True, False], [False, True])
    assert tied["b"] == 1 and tied["c"] == 1
    assert tied["p"] == 1.0
    empty = mcnemar_exact([True, True], [True, True])
    assert empty["p"] == 1.0 and empty["n_discordant"] == 0
    one_sided = mcnemar_exact([False, False, False], [True, True, True])
    assert one_sided["b"] == 3 and one_sided["c"] == 0
    assert one_sided["p"] == 0.25
    assert format_p(1e-8) == "<0.0001"
    assert format_p(0.25) == "0.2500"


def test_higher_tau_does_not_increase_coverage() -> None:
    taxonomy = load_taxonomy()
    rows = [
        RoutedRow("product_question", "product_question", confidence, False)
        for confidence in (0.1, 0.4, 0.7, 0.95)
    ]
    previous = 1.1
    for tau in DEFAULT_TAUS:
        point = route_stats(rows, tau, taxonomy)
        assert point.coverage <= previous
        previous = point.coverage
    tau, met = select_tau(rows, taxonomy, DEFAULT_TAUS, 0.02)
    assert met
    assert route_stats(rows, tau, taxonomy).auto_error <= 0.02


def test_calibration_bins() -> None:
    report = expected_calibration_error([True, False], [0.9, 0.2], n_bins=5)
    assert 0.0 <= float(report["ece"]) <= 1.0

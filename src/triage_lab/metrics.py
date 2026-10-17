"""Paired, per-message metrics. Sample size is the number of messages."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from triage_lab.policy import decide_route
from triage_lab.taxonomy import Taxonomy


@dataclass(frozen=True)
class ClassScore:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True)
class SweepPoint:
    tau: float
    coverage: float
    auto_error: float
    human_share: float
    n_auto: int
    n_auto_error: int
    n_human: int


@dataclass(frozen=True)
class RoutedRow:
    gold: str
    category: str
    confidence: float
    injection: bool


def accuracy(golds: Sequence[str], preds: Sequence[str]) -> float:
    if not golds:
        return 0.0
    correct = sum(gold == pred for gold, pred in zip(golds, preds, strict=True))
    return correct / len(golds)


def confusion(
    golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]
) -> dict[str, dict[str, int]]:
    table = {gold: {pred: 0 for pred in labels} for gold in labels}
    for gold, pred in zip(golds, preds, strict=True):
        if gold not in table or pred not in table[gold]:
            raise KeyError(f"label outside the taxonomy: {gold} -> {pred}")
        table[gold][pred] += 1
    return table


def confusion_total(table: dict[str, dict[str, int]]) -> int:
    return sum(count for row in table.values() for count in row.values())


def per_class(
    golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]
) -> dict[str, ClassScore]:
    scores: dict[str, ClassScore] = {}
    pairs = list(zip(golds, preds, strict=True))
    for label in labels:
        tp = sum(gold == label and pred == label for gold, pred in pairs)
        fp = sum(gold != label and pred == label for gold, pred in pairs)
        fn = sum(gold == label and pred != label for gold, pred in pairs)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )
        scores[label] = ClassScore(precision, recall, f1, tp + fn)
    return scores


def macro_f1(
    golds: Sequence[str], preds: Sequence[str], labels: Sequence[str]
) -> float:
    scores = per_class(golds, preds, labels)
    if not scores:
        return 0.0
    return sum(item.f1 for item in scores.values()) / len(scores)


def expected_calibration_error(
    correct: Sequence[bool], confidence: Sequence[float], n_bins: int = 5
) -> dict[str, object]:
    if len(correct) != len(confidence):
        raise ValueError("correct and confidence must be paired")
    bins: list[dict[str, float | int]] = []
    n = len(correct)
    total = 0.0
    for index in range(n_bins):
        members = [
            i for i, conf in enumerate(confidence) if _bin_index(conf, n_bins) == index
        ]
        count = len(members)
        if count == 0:
            bins.append({"bin": index, "count": 0, "accuracy": 0.0, "confidence": 0.0})
            continue
        acc = sum(1.0 if correct[i] else 0.0 for i in members) / count
        mean_conf = sum(confidence[i] for i in members) / count
        total += (count / n) * abs(acc - mean_conf) if n else 0.0
        bins.append(
            {
                "bin": index,
                "count": count,
                "accuracy": acc,
                "confidence": mean_conf,
            }
        )
    return {"ece": total, "bins": bins}


def _bin_index(confidence: float, n_bins: int) -> int:
    if confidence >= 1.0:
        return n_bins - 1
    return min(n_bins - 1, max(0, int(confidence * n_bins)))


def bootstrap_ci(
    statistic: Callable[[Sequence[int]], float],
    n: int,
    *,
    n_boot: int = 1000,
    seed: int = 7,
) -> dict[str, float]:
    """Resample message indexes. The point estimate does not depend on ``seed``."""
    if n <= 0:
        raise ValueError("n must be the number of messages")
    point = statistic(tuple(range(n)))
    rng = random.Random(seed)
    samples = []
    for _ in range(n_boot):
        draw = tuple(rng.randrange(n) for _ in range(n))
        samples.append(statistic(draw))
    samples.sort()
    low = samples[int(0.025 * n_boot)]
    high = samples[min(n_boot - 1, int(0.975 * n_boot))]
    return {
        "point": point,
        "low": low,
        "high": high,
        "n": float(n),
        "n_boot": float(n_boot),
    }


def mcnemar_exact(
    correct_a: Sequence[bool], correct_b: Sequence[bool]
) -> dict[str, float]:
    """Exact two-sided McNemar on paired message outcomes.

    ``b`` counts A wrong and B right. ``c`` counts A right and B wrong.
    p-values below 0.0001 should be displayed as ``<0.0001``.
    """
    if len(correct_a) != len(correct_b):
        raise ValueError("paired lists must have the same length")
    b_count = 0
    c_count = 0
    for left, right in zip(correct_a, correct_b, strict=True):
        if (not left) and right:
            b_count += 1
        elif left and (not right):
            c_count += 1
    discordant = b_count + c_count
    if discordant == 0:
        p_value = 1.0
    else:
        k = min(b_count, c_count)
        tail = sum(math.comb(discordant, i) for i in range(k + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "b": float(b_count),
        "c": float(c_count),
        "n_discordant": float(discordant),
        "n": float(len(correct_a)),
        "p": p_value,
    }


def format_p(p_value: float) -> str:
    if p_value < 0.0001:
        return "<0.0001"
    return f"{p_value:.4f}"


def route_stats(
    rows: Sequence[RoutedRow], tau: float, taxonomy: Taxonomy
) -> SweepPoint:
    n = len(rows)
    n_auto = 0
    n_auto_error = 0
    n_human = 0
    for row in rows:
        route = decide_route(row.category, row.confidence, tau, row.injection, taxonomy)
        if route == "human_review":
            n_human += 1
            continue
        n_auto += 1
        if row.category != row.gold:
            n_auto_error += 1
    coverage = n_auto / n if n else 0.0
    human_share = n_human / n if n else 0.0
    auto_error = n_auto_error / n_auto if n_auto else 0.0
    return SweepPoint(
        tau, coverage, auto_error, human_share, n_auto, n_auto_error, n_human
    )


def threshold_sweep(
    rows: Sequence[RoutedRow], taxonomy: Taxonomy, taus: Sequence[float]
) -> list[SweepPoint]:
    return [route_stats(rows, tau, taxonomy) for tau in taus]


def select_tau(
    rows: Sequence[RoutedRow],
    taxonomy: Taxonomy,
    taus: Sequence[float],
    error_budget: float,
) -> tuple[float, bool]:
    """Maximise dev coverage subject to auto-routed error <= budget.

    Ties break toward the higher tau. If no tau meets the budget, return the
    highest tau and ``False``.
    """
    points = threshold_sweep(rows, taxonomy, taus)
    feasible = [point for point in points if point.auto_error <= error_budget]
    if not feasible:
        return max(taus), False
    best = max(feasible, key=lambda point: (point.coverage, point.tau))
    return best.tau, True


DEFAULT_TAUS: tuple[float, ...] = (
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    0.95,
    0.99,
)

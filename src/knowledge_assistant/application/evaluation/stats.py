"""Paired statistics for Arm A vs Arm B (EXP-001 §1). Plain Python (scipy is not installed), pure, no I/O.

Both arms answer the same cases, so every test is paired on the case: `a[i]` and `b[i]` belong to the same case.
Sign convention everywhere: difference = B - A (the EXP-001 table column "Δ (B−A)").
- binary metrics (hit@k, correct, ...): exact McNemar test on the discordant pairs;
- continuous metrics (reciprocal rank, latency, tokens): Wilcoxon signed-rank test, exact;
- 95 % CI of the difference: paired bootstrap (resample case indices, both arms together), 10 000 resamples, seed 42.
Wording rule (EXP-001): p >= 0.05 means "no statistically reliable difference at n = X", never "A is better".
"""
import math
import random
from dataclasses import dataclass
from fractions import Fraction

from knowledge_assistant.application.evaluation.metrics.latency import nearest_rank

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42
TIE_DECIMALS = 12  # |differences| equal after rounding to 12 decimals are ties (float noise such as 0.1 + 0.2)


def _paired(a, b) -> None:
    if len(a) != len(b):
        raise ValueError(f"paired samples need equal lengths, got {len(a)} and {len(b)}")


@dataclass(frozen=True)
class McNemarResult:
    b: int  # discordant pairs with A = 1, B = 0 (A-only successes)
    c: int  # discordant pairs with A = 0, B = 1 (B-only successes)
    p_value: float  # exact two-sided


def mcnemar_exact(a: list[int | bool], b: list[int | bool]) -> McNemarResult:
    """Exact McNemar: under H0 the b + c discordant pairs split Binomial(b + c, 1/2).

    p = min(1, 2 * sum_{i <= min(b, c)} C(n, i) / 2^n), computed with exact fractions; no discordant pairs -> p = 1.
    """
    _paired(a, b)
    b_count = sum(1 for x, y in zip(a, b) if bool(x) and not bool(y))
    c_count = sum(1 for x, y in zip(a, b) if not bool(x) and bool(y))
    n = b_count + c_count
    if n == 0:
        return McNemarResult(b_count, c_count, 1.0)
    tail = Fraction(sum(math.comb(n, i) for i in range(min(b_count, c_count) + 1)), 2 ** n)
    return McNemarResult(b_count, c_count, float(min(Fraction(1), 2 * tail)))


@dataclass(frozen=True)
class BootstrapResult:
    delta: float  # observed statistic(B) - statistic(A)
    low: float
    high: float
    confidence: float
    resamples: int
    seed: int


def _mean(values) -> float:
    return sum(values) / len(values)


def paired_bootstrap_ci(a: list[float], b: list[float], resamples: int = BOOTSTRAP_RESAMPLES,
                        seed: int = BOOTSTRAP_SEED, confidence: float = 0.95, statistic=_mean) -> BootstrapResult:
    """Percentile CI of statistic(B) - statistic(A), resampling case indices (pairs stay together).

    `random.Random(seed)` draws n indices with replacement per resample; the bounds are the nearest-rank
    (1 - confidence) / 2 and (1 + confidence) / 2 percentiles of the resampled differences.
    """
    _paired(a, b)
    if not a:
        raise ValueError("bootstrap of no pairs")
    rng = random.Random(seed)
    n = len(a)
    deltas = []
    for _ in range(resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        deltas.append(statistic([b[i] for i in indices]) - statistic([a[i] for i in indices]))
    low, high = percentile_interval(deltas, confidence)
    return BootstrapResult(delta=statistic(b) - statistic(a), low=low, high=high, confidence=confidence,
                           resamples=resamples, seed=seed)


def percentile_interval(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Nearest-rank (1 - confidence) / 2 and (1 + confidence) / 2 percentiles of `values`."""
    tail = (1 - Fraction(str(confidence))) / 2 * 100  # exact: 0.95 -> 5/2, not 2.5000000000000022
    return nearest_rank(values, tail), nearest_rank(values, 100 - tail)


@dataclass(frozen=True)
class WilcoxonResult:
    n: int  # non-zero differences used
    zeros_dropped: int
    w_plus: float  # rank sum of positive differences (B > A)
    w_minus: float
    p_value: float  # exact two-sided


def _average_ranks(values: list[float]) -> list[float]:
    """1-based ranks of `values`, ties get the mean of their ranks."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for position in range(i, j + 1):
            ranks[order[position]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def wilcoxon_signed_rank(a: list[float], b: list[float]) -> WilcoxonResult:
    """Exact Wilcoxon signed-rank test on d = b - a.

    Zero differences are dropped (Wilcoxon's method); ties get average ranks. The p-value comes from the exact
    permutation distribution of W+ given these ranks (each sign +/- with probability 1/2), counted with a subset-sum
    table over doubled ranks (average ranks are multiples of 0.5). It is exact with ties too, where scipy would switch
    to a normal approximation, so tied cases can differ slightly from scipy. p = min(1, 2 * min(P(W+ <= w), P(W+ >= w))).
    """
    _paired(a, b)
    differences = [round(y - x, TIE_DECIMALS) for x, y in zip(a, b)]
    nonzero = [d for d in differences if d != 0]
    zeros = len(differences) - len(nonzero)
    if not nonzero:
        return WilcoxonResult(0, zeros, 0.0, 0.0, 1.0)
    ranks = _average_ranks([abs(d) for d in nonzero])
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    doubled = [round(2 * r) for r in ranks]
    counts = [1] + [0] * sum(doubled)  # counts[s] = number of sign patterns with doubled W+ = s
    for rank in doubled:
        for total in range(len(counts) - 1, rank - 1, -1):
            counts[total] += counts[total - rank]
    observed = round(2 * w_plus)
    patterns = 2 ** len(nonzero)
    lower = Fraction(sum(counts[: observed + 1]), patterns)
    upper = Fraction(sum(counts[observed:]), patterns)
    return WilcoxonResult(len(nonzero), zeros, w_plus, w_minus, float(min(Fraction(1), 2 * min(lower, upper))))

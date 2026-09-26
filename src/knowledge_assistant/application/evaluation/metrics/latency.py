"""Latency summary per stage (EVAL-003b §4). Pure, no I/O.

Percentiles use the nearest-rank method: sort the n values ascending; the p-th percentile (0 < p <= 100) is the
value at 1-based rank ceil(p / 100 * n). No interpolation, so every reported percentile is a measured value.
The main table uses only records with `retry_count == 0 and not fallback_used`; retried or fallback records are
counted and summarized separately (evaluation-spec.md: "retried calls are reported separately").
Record shape (EVAL-003a; confirmed by EVAL-003b proper): {"latency_ms": {stage: float | None}, "retry_count": int,
"fallback_used": bool}. A missing or None stage value is skipped, so `n` can differ between stages.
"""
import math
from fractions import Fraction

STAGES = ("embed_query", "retrieve", "generate", "total")
METHOD = "nearest-rank"


def nearest_rank(values: list[float], p: float) -> float:
    """The p-th percentile by nearest rank; exact rational rank, so float rounding never shifts it."""
    if not values:
        raise ValueError("percentile of no values")
    if not 0 < p <= 100:
        raise ValueError(f"p must be in (0, 100], got {p}")
    ordered = sorted(values)
    rank = math.ceil(Fraction(str(p)) * len(ordered) / 100)
    return ordered[max(rank, 1) - 1]


def summarize_values(values: list[float]) -> dict:
    """{n, mean, p50, p95, max}; the statistics are None when there are no values."""
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "max": None}
    return {"n": len(values), "mean": sum(values) / len(values), "p50": nearest_rank(values, 50),
            "p95": nearest_rank(values, 95), "max": max(values)}


def is_clean(record: dict) -> bool:
    """True for records in the main latency table: no retry and no fallback model."""
    return record["retry_count"] == 0 and not record["fallback_used"]


def _by_stage(records: list[dict], stages: tuple[str, ...]) -> dict:
    return {stage: summarize_values([r["latency_ms"][stage] for r in records
                                     if r["latency_ms"].get(stage) is not None])
            for stage in stages}


def summarize_latency(records: list[dict], stages: tuple[str, ...] = STAGES) -> dict:
    """Main table (clean records) and a separate table for retried/fallback records, with its count."""
    clean = [record for record in records if is_clean(record)]
    other = [record for record in records if not is_clean(record)]
    return {
        "method": METHOD,
        "main": {"count": len(clean), "stages": _by_stage(clean, stages)},
        "retried_or_fallback": {"count": len(other), "stages": _by_stage(other, stages)},
    }

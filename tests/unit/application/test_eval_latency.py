"""EVAL-003b-pre: nearest-rank percentiles and the clean vs retried/fallback latency split."""
import pytest

from knowledge_assistant.application.evaluation.metrics.latency import (
    nearest_rank,
    summarize_latency,
    summarize_values,
)


def test_nearest_rank_textbook_example():
    # [15, 20, 35, 40, 50]: p30 -> rank ceil(1.5) = 2; p40 -> ceil(2.0) = 2; p50 -> ceil(2.5) = 3; p100 -> 5
    values = [50, 15, 40, 20, 35]  # unsorted on purpose
    assert [nearest_rank(values, p) for p in (5, 30, 40, 50, 100)] == [15, 20, 20, 35, 50]


def test_nearest_rank_1_to_20():
    values = list(range(1, 21))
    assert nearest_rank(values, 50) == 10  # rank ceil(10.0) = 10
    assert nearest_rank(values, 95) == 19  # rank ceil(19.0) = 19


def test_nearest_rank_float_percentile_is_exact():
    # 14 / 100 * 50 is 7.000000000000001 in floats (ceil -> 8); the exact rank is 7
    assert nearest_rank(list(range(1, 51)), 14) == 7
    assert nearest_rank(list(range(1, 51)), 14.0) == 7


@pytest.mark.parametrize("p", [0, -1, 100.5])
def test_nearest_rank_rejects_p_outside_0_100(p):
    with pytest.raises(ValueError):
        nearest_rank([1, 2, 3], p)


def test_summarize_values():
    assert summarize_values(list(range(1, 21))) == {"n": 20, "mean": 10.5, "p50": 10, "p95": 19, "max": 20}
    assert summarize_values([]) == {"n": 0, "mean": None, "p50": None, "p95": None, "max": None}


def _record(total, retry=0, fallback=False, generate=None):
    return {"latency_ms": {"embed_query": 10.0, "retrieve": 5.0, "generate": generate, "total": total},
            "retry_count": retry, "fallback_used": fallback}


def test_retried_and_fallback_records_are_excluded_from_the_main_table():
    records = [_record(100.0, generate=80.0), _record(200.0, generate=180.0), _record(300.0, generate=280.0),
               _record(9000.0, retry=2, generate=8000.0), _record(7000.0, fallback=True, generate=6000.0)]
    summary = summarize_latency(records)
    assert summary["method"] == "nearest-rank"
    main = summary["main"]
    assert main["count"] == 3
    assert main["stages"]["total"] == {"n": 3, "mean": 200.0, "p50": 200.0, "p95": 300.0, "max": 300.0}
    other = summary["retried_or_fallback"]
    assert other["count"] == 2
    assert other["stages"]["total"] == {"n": 2, "mean": 8000.0, "p50": 7000.0, "p95": 9000.0, "max": 9000.0}


def test_missing_stage_values_are_skipped_per_stage():
    records = [_record(100.0, generate=None), _record(200.0, generate=150.0)]  # e.g. an insufficient short-circuit
    stages = summarize_latency(records)["main"]["stages"]
    assert stages["total"]["n"] == 2
    assert stages["generate"] == {"n": 1, "mean": 150.0, "p50": 150.0, "p95": 150.0, "max": 150.0}

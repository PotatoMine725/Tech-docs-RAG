"""gate_calibration: the threshold sweep over gate-off runs and the fixed selection rule. Offline."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluation" / "gate_calibration.py"
spec = importlib.util.spec_from_file_location("gate_calibration", SCRIPT)
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


def row(case_id, answerable, top1, label):
    return {"case_id": case_id, "answerable": answerable, "top1": top1, "label": label}


ROWS = [
    row("A1", True, 0.70, "correct"),
    row("A2", True, 0.55, "partially_correct"),
    row("A3", True, 0.45, "correct"),
    row("A4", True, 0.40, "false_refusal"),  # the LLM refused
    row("U1", False, 0.50, "hallucination"),
    row("U2", False, 0.42, "correct_refusal"),
]


def test_candidates_are_off_then_midpoints():
    assert gc.candidates(ROWS) == [None, 0.41, 0.435, 0.475, 0.525, 0.625]


def test_gate_refusal_overrides_the_llm_answer():
    assert gc.evaluate(ROWS, 0.475)["hallucination"] == 1  # U1 (0.50) passes the gate and hallucinates
    result = gc.evaluate(ROWS, 0.525)
    assert (result["hallucination"], result["false_refusal"], result["lenient"], result["gate_refused"]) == (0, 2, 2, 4)


def test_off_keeps_every_recorded_label():
    result = gc.evaluate(ROWS, None)
    assert (result["hallucination"], result["false_refusal"], result["correct"], result["lenient"]) == (1, 1, 2, 3)


def test_rule_picks_the_smallest_threshold_with_fewest_hallucinations():
    results = [gc.evaluate(ROWS, t) for t in gc.candidates(ROWS)]
    assert gc.choose(results)["t"] == 0.525


def test_unlabelled_counts_as_failure():
    rows = [row("A1", True, 0.7, None), row("U1", False, 0.6, None)]
    result = gc.evaluate(rows, None)
    assert result["hallucination"] == 1 and result["lenient"] == 0 and result["unlabelled"] == ["A1", "U1"]


def _run(run_id, threshold=-1.0, gate_fired=False, case="A1"):
    record = {"case_id": case, "arm": "A", "mode": "full", "status": "ok", "gate_fired": gate_fired, "answerable": False,
              "insufficient": True, "missing_information": None, "citations": [], "top1_score": 0.4, "answer": ""}
    return {"run_id": run_id, "manifest": {"config": {"threshold": threshold}}, "records": [record],
            "judgement_lines": []}


def test_runs_must_be_gate_off_and_disjoint():
    assert gc.case_rows([_run("r")])[0]["label"] == "correct_refusal"  # bare refusal needs no judge
    with pytest.raises(gc.CalibrationError, match="gate was on"):
        gc.case_rows([_run("r", threshold=0.5417)])
    with pytest.raises(gc.CalibrationError, match="gate fired"):
        gc.case_rows([_run("r", gate_fired=True)])
    with pytest.raises(gc.CalibrationError, match="more than one run"):
        gc.case_rows([_run("r1"), _run("r2")])

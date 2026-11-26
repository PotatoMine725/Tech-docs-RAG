"""llm_run_summary: missing-marker rate, language match, TTFT, same-retrieval check, on tiny fake runs."""
import json

from scripts.evaluation import llm_run_summary as summary


def _record(case_id, *, language="vi", answer="Trả lời [1].", insufficient=False, citations=1, ttft=1000.0,
            chunks=("c1", "c2"), gate=False, note=None, answerable=True):
    return {"case_id": case_id, "answerable": answerable, "arm": "A", "mode": "full", "status": "ok", "language": language,
            "llm_called": not gate, "insufficient": insufficient or gate, "gate_fired": gate,
            "answer": answer, "missing_information": note, "citations": [{"marker": 1}] * citations,
            "retrieved": [{"chunk_id": c} for c in chunks], "time_to_first_token_ms": None if gate else ttft,
            "latency_ms": {"generate": None if gate else 3000.0}}


def _write(tmp_path, run_id, records, model="qwen"):
    directory = tmp_path / run_id
    directory.mkdir()
    (directory / "run.json").write_text(json.dumps({"config": {"answer_model": model, "prompt_version": "answer_v3"}}))
    (directory / "records.jsonl").write_text("\n".join(json.dumps(r) for r in records))


def test_metrics_and_same_retrieval(tmp_path, capsys):
    _write(tmp_path, "ref", [_record("Q1"), _record("Q2"), _record("Q3")])
    _write(tmp_path, "local", [
        _record("Q1", ttft=1000.0),
        _record("Q2", answer="An English answer.", citations=0, ttft=3000.0),  # no marker + wrong language
        _record("Q3", insufficient=True, answer="msg", note="Thiếu thông tin.", ttft=2000.0),
        _record("Q4", gate=True),
    ])
    s = summary.summarize(*summary.load_run("local", tmp_path))
    assert (s["answered"], s["llm_refused"], s["gate"]) == (2, 1, 1)
    assert s["missing_marker"] == 0.5 and s["missing_marker_cases"] == ["Q2"]
    assert s["lang_mismatch_cases"] == ["Q2"] and abs(s["lang_match"] - 2 / 3) < 1e-9
    # A2: the gate refusal (Q4) and the LLM refusal (Q3) are counted apart
    assert s["false_refusal_gate"] == 0.25 and s["false_refusal_gate_cases"] == ["Q4"]
    assert abs(s["false_refusal_llm"] - 1 / 3) < 1e-9 and s["false_refusal_llm_cases"] == ["Q3"]
    assert s["ttft_median_ms"] == 2000.0 and s["ttft_p90_ms"] == 3000.0
    assert summary.main(["--runs", "local", "--reference", "ref"], results_dir=tmp_path) == 0
    assert "| yes |" in capsys.readouterr().out


def test_retrieval_order_change_fails(tmp_path, capsys):
    _write(tmp_path, "ref", [_record("Q1", chunks=("c1", "c2"))])
    _write(tmp_path, "other", [_record("Q1", chunks=("c2", "c1"))])
    assert summary.main(["--runs", "other", "--reference", "ref"], results_dir=tmp_path) == 1
    assert "retrieval differs from ref on Q1" in capsys.readouterr().out


def test_known_difference_is_accepted_only_when_gated_in_both_runs(tmp_path, capsys):
    _write(tmp_path, "ref", [_record("Q1", chunks=("c1", "c2"), gate=True), _record("Q2", chunks=("c1", "c2"))])
    _write(tmp_path, "run", [_record("Q1", chunks=("c2", "c1"), gate=True), _record("Q2", chunks=("c2", "c1"))])
    assert summary.main(["--runs", "run", "--reference", "ref", "--known-differences", "Q1"], results_dir=tmp_path) == 1
    out = capsys.readouterr().out
    assert "retrieval differs from ref on Q2" in out and "accepted known difference" in out and "Q1" in out
    assert summary.main(["--runs", "run", "--reference", "ref", "--known-differences", "Q1,Q2"],
                        results_dir=tmp_path) == 1  # Q2 reached the LLM: never accepted
    _write(tmp_path, "run2", [_record("Q1", chunks=("c2", "c1"), gate=True), _record("Q2")])
    assert summary.main(["--runs", "run2", "--reference", "ref", "--known-differences", "Q1"], results_dir=tmp_path) == 0
    assert "| yes* |" in capsys.readouterr().out

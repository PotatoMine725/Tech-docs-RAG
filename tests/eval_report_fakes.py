"""Offline fixtures for EVAL-003c tests (make_tables.py / make_spot_check.py / score_spot_check.py): fake run
folders and question data on disk, built from the same doubles the EVAL-003a/b tests use. No eval-set content."""
import json
from pathlib import Path

from knowledge_assistant.application.evaluation.judge import answer_sha256, parse_verdict


def write_manifest(root: Path, run_id: str, arm: str = "A", mode: str = "full", split: str = "dev") -> Path:
    directory = root / "data" / "evaluation" / "results" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"run_id": run_id, "config": {"arm": arm, "mode": mode, "split": split}}
    (directory / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def write_records(directory: Path, records: list[dict]) -> None:
    (directory / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def write_judgements(directory: Path, lines: list[dict]) -> None:
    (directory / "judgements.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def write_spans_file(root: Path, cases: dict) -> None:
    """`cases`: {case_id: {"answerable": bool, "slots": {slot: [span dict, ...]}}} (`build_expected_spans`'s shape)."""
    path = root / "data" / "evaluation" / "questions" / "expected-spans-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "rule": "test", "inputs": {}, "cases": cases}), encoding="utf-8")


def span_dict(source_id: str, heading_path: str, char_start: int = 0, char_end: int = 20, role: str = "expected",
             variant: int = 0) -> dict:
    return {"role": role, "source_id": source_id, "heading_path": heading_path, "variant": variant,
            "char_start": char_start, "char_end": char_end}


def write_pricing(root: Path, model: str = "test-judge-model") -> None:
    path = root / "config" / "pricing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"source": {"url": "http://example.test", "retrieved": "2026-01-01"},
                                "models": {model: {"input_per_1m_usd": 1.0, "output_per_1m_usd": 2.0}}}),
                    encoding="utf-8")


def judgement_line(record: dict, check: str, verdict_text: str, status: str = "ok", model: str = "test-judge-model",
                   prompt_version: str = "judge_v1") -> dict:
    verdict = parse_verdict(check, verdict_text, record) if status == "ok" else None
    return {
        "run_id": record["run_id"], "case_id": record["case_id"], "arm": record["arm"], "mode": record["mode"],
        "split": record.get("split") or "dev", "check": check, "answer_sha256": answer_sha256(record),
        "judge_prompt_version": prompt_version, "judge_prompt_sha256": "a" * 64, "judge_model": model,
        "status": status, "verdict": verdict, "error": None, "error_kind": None, "error_type": None,
        "raw_text": None, "model_used": model, "retry_count": 0, "fallback_used": False,
        "prompt_tokens": 50, "output_tokens": 10, "thoughts_tokens": 0,
        "latency_ms": {"generate": 100.0, "retry_wait": None, "throttle_wait": None, "total": 120.0},
        "started_at": "t0", "finished_at": "t1",
    }

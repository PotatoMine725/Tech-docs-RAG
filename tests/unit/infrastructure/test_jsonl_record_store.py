"""JsonlRecordStore: the on-disk side of a resumable evaluation run (EVAL-003a). Offline, tmp_path only.

A record line is on disk (flushed) before the next case starts, only newline-terminated lines count as records, and
every line passes the redaction function, so a key can never reach a results file.
"""
import pytest

from knowledge_assistant.core.exceptions import EvaluationError
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore


def _store(tmp_path, redact=lambda text: text):
    return JsonlRecordStore(tmp_path / "run-1", redact=redact)


def test_a_new_run_has_no_manifest_and_no_records(tmp_path):
    store = _store(tmp_path)
    assert store.read_manifest() is None
    assert store.read_records() == []
    assert not (tmp_path / "run-1").exists()  # reading creates nothing


def test_manifest_round_trip_replaces_the_file_and_leaves_no_temp_file(tmp_path):
    store = _store(tmp_path)
    store.write_manifest({"run_id": "run-1", "finished_at": None})
    store.write_manifest({"run_id": "run-1", "finished_at": "2026-09-27T10:00:00+00:00"})
    assert store.read_manifest() == {"run_id": "run-1", "finished_at": "2026-09-27T10:00:00+00:00"}
    assert sorted(path.name for path in (tmp_path / "run-1").iterdir()) == ["run.json"]


def test_each_appended_record_is_on_disk_before_the_next_one(tmp_path):
    store = _store(tmp_path)
    for n in range(1, 4):
        store.append_record({"case_id": f"Q-T-{n}", "status": "ok"})
        raw = (tmp_path / "run-1" / "records.jsonl").read_bytes()  # read while the store is still open
        assert raw.endswith(b"\n") and raw.count(b"\n") == n
    assert [record["case_id"] for record in store.read_records()] == ["Q-T-1", "Q-T-2", "Q-T-3"]


def test_files_are_utf8_with_unix_newlines(tmp_path):
    store = _store(tmp_path)
    store.append_record({"case_id": "Q-T-1", "answer": "Không đủ thông tin"})
    store.write_manifest({"note": "Không"})
    raw = (tmp_path / "run-1" / "records.jsonl").read_bytes()
    assert b"\r" not in raw and "Không đủ thông tin".encode("utf-8") in raw
    assert b"\r" not in (tmp_path / "run-1" / "run.json").read_bytes()
    assert store.read_records() == [{"case_id": "Q-T-1", "answer": "Không đủ thông tin"}]


def test_errors_go_to_their_own_file(tmp_path):
    store = _store(tmp_path)
    store.append_record({"case_id": "Q-T-1", "status": "error"})
    store.append_error({"case_id": "Q-T-1", "error_kind": "quota"})
    assert [line for line in (tmp_path / "run-1" / "errors.jsonl").read_text(encoding="utf-8").splitlines()] == [
        '{"case_id": "Q-T-1", "error_kind": "quota"}'
    ]
    assert store.read_records() == [{"case_id": "Q-T-1", "status": "error"}]


def test_an_unterminated_last_line_is_not_a_record_and_the_next_append_drops_it(tmp_path):
    """A process killed mid-write leaves a torn tail. It must neither crash a resume nor swallow the next record."""
    store = _store(tmp_path)
    store.append_record({"case_id": "Q-T-1"})
    store.append_record({"case_id": "Q-T-2"})
    with (tmp_path / "run-1" / "records.jsonl").open("ab") as handle:
        handle.write(b'{"case_id": "Q-T-3", "sta')  # no newline: the write was cut off
    assert [record["case_id"] for record in store.read_records()] == ["Q-T-1", "Q-T-2"]
    store.append_record({"case_id": "Q-T-3"})
    assert [record["case_id"] for record in store.read_records()] == ["Q-T-1", "Q-T-2", "Q-T-3"]
    assert (tmp_path / "run-1" / "records.jsonl").read_bytes().count(b"\n") == 3  # the torn fragment is gone


def test_a_corrupt_complete_line_is_an_error_not_a_silent_skip(tmp_path):
    store = _store(tmp_path)
    store.append_record({"case_id": "Q-T-1"})
    with (tmp_path / "run-1" / "records.jsonl").open("ab") as handle:
        handle.write(b"this is not json\n")
    store.append_record({"case_id": "Q-T-2"})
    with pytest.raises(EvaluationError, match="records.jsonl line 2"):
        store.read_records()


def test_every_written_line_passes_the_redaction_function(tmp_path):
    store = _store(tmp_path, redact=lambda text: text.replace("SECRET-KEY", "[REDACTED]"))
    store.append_record({"case_id": "Q-T-1", "error": "bad key SECRET-KEY"})
    store.append_error({"body": "SECRET-KEY"})
    store.write_manifest({"note": "SECRET-KEY"})
    for name in ("records.jsonl", "errors.jsonl", "run.json"):
        assert "SECRET-KEY" not in (tmp_path / "run-1" / name).read_text(encoding="utf-8")
    assert store.read_records() == [{"case_id": "Q-T-1", "error": "bad key [REDACTED]"}]


def test_a_non_finite_number_is_refused_because_it_is_not_valid_json(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.append_record({"case_id": "Q-T-1", "top1_score": float("nan")})
    assert not (tmp_path / "run-1" / "records.jsonl").exists() or (tmp_path / "run-1" / "records.jsonl").read_bytes() == b""

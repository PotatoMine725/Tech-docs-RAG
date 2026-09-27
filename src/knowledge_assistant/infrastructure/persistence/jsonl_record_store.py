"""RecordStore on disk: `run.json`, `records.jsonl` and `errors.jsonl` in one run directory (EVAL-003a).

Every write is one newline-terminated line, flushed and fsynced before the call returns, so a killed process loses at
most the line being written. Only newline-terminated lines are records: an unterminated tail is a torn write, ignored by
`read_records` and cut off by the next append (the case is then simply run again). A complete line that is not JSON is
corruption and raises. Every line passes `redact` first, so an API key can never reach a results file. Files are UTF-8
with "\n" line ends, whatever the platform.
"""
import json
import os
from collections.abc import Callable
from pathlib import Path

from knowledge_assistant.core.exceptions import EvaluationError

MANIFEST = "run.json"
RECORDS = "records.jsonl"
ERRORS = "errors.jsonl"


class JsonlRecordStore:
    def __init__(self, run_dir: str | Path, redact: Callable[[str], str]) -> None:
        self._dir = Path(run_dir)
        self._redact = redact

    def read_manifest(self) -> dict | None:
        path = self._dir / MANIFEST
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def write_manifest(self, manifest: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        text = self._redact(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)) + "\n"
        temporary = self._dir / f"{MANIFEST}.tmp"
        with temporary.open("wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self._dir / MANIFEST)  # atomic: a reader sees the old or the new manifest, never half

    def read_records(self) -> list[dict]:
        path = self._dir / RECORDS
        if not path.exists():
            return []
        *complete, _torn_tail = path.read_bytes().split(b"\n")  # the piece after the last newline is not a record
        records = []
        for number, line in enumerate(complete, start=1):
            try:
                records.append(json.loads(line.decode("utf-8")))
            except ValueError as error:  # JSONDecodeError and UnicodeDecodeError
                raise EvaluationError(f"{path} {RECORDS} line {number} is not valid JSON: {error}") from error
        return records

    def append_record(self, record: dict) -> None:
        self._append(RECORDS, record)

    def append_error(self, entry: dict) -> None:
        self._append(ERRORS, entry)

    def _append(self, name: str, item: dict) -> None:
        line = self._redact(json.dumps(item, ensure_ascii=False, allow_nan=False)) + "\n"  # raises before any write
        self._dir.mkdir(parents=True, exist_ok=True)
        with (self._dir / name).open("ab+") as handle:
            if handle.seek(0, os.SEEK_END):  # a non-empty file must end with a newline
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    handle.seek(0)
                    handle.truncate(handle.read().rfind(b"\n") + 1)  # everything after the last newline is torn
            handle.write(line.encode("utf-8"))  # append mode: always at the end
            handle.flush()
            os.fsync(handle.fileno())

from typing import Protocol


class RecordStore(Protocol):
    """Where one evaluation run keeps its files (EVAL-003a): the manifest (`run.json`), the per-case records and the
    error log. Records and errors are append-only; a line is durable before the call returns."""

    def read_manifest(self) -> dict | None: ...

    def write_manifest(self, manifest: dict) -> None: ...

    def read_records(self) -> list[dict]:
        """Every complete record in the order written; a retried case appears again after its earlier error."""
        ...

    def append_record(self, record: dict) -> None: ...

    def append_error(self, entry: dict) -> None: ...


class JudgementStore(Protocol):
    """The judge's cache of one run (EVAL-003b): append-only judgements, one line per judge call (or failure).
    A line is durable before the call returns; read them back in the order written."""

    def read_manifest(self) -> dict | None: ...

    def read_judgements(self) -> list[dict]: ...

    def append_judgement(self, entry: dict) -> None: ...

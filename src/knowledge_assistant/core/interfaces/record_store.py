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

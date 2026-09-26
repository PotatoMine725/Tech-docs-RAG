"""Write `data/evaluation/questions/expected-spans-v1.json` from `normalized.jsonl` + `eval-v1.jsonl` (EVAL-003b §1).

Offline, deterministic. The header records the SHA-256 of both inputs, so a stale file is detectable.
Run from the repo root: .venv/Scripts/python.exe -m knowledge_assistant.application.evaluation.build_expected_spans
"""
import hashlib
import json
from pathlib import Path

from knowledge_assistant.application.evaluation.metrics.spans import build_expected_spans
from knowledge_assistant.config import PROJECT_ROOT

QUESTIONS_FILE = Path("data/evaluation/questions/eval-v1.jsonl")
NORMALIZED_FILE = Path("data/processed/documents/normalized.jsonl")
OUTPUT_FILE = Path("data/evaluation/questions/expected-spans-v1.json")
SCHEMA_VERSION = 1


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_spans_document(root: Path = PROJECT_ROOT) -> dict:
    """The full JSON document (header + cases) for the files under `root`."""
    questions, normalized = root / QUESTIONS_FILE, root / NORMALIZED_FILE
    return {
        "schema_version": SCHEMA_VERSION,
        "rule": "Spans are half-open [char_start, char_end) offsets into the normalized text of source_id. "
                "Every variant of a heading path is listed; any variant counts (ADR-0003 D8). "
                "Lenient = expected + alternate spans per slot; strict = role 'expected' only (OWNER-001).",
        "inputs": {
            "questions": {"path": QUESTIONS_FILE.as_posix(), "sha256": _sha256(questions)},
            "normalized": {"path": NORMALIZED_FILE.as_posix(), "sha256": _sha256(normalized)},
        },
        "cases": build_expected_spans(_read_jsonl(normalized), _read_jsonl(questions)),
    }


def main() -> int:
    document = expected_spans_document()
    output = PROJECT_ROOT / OUTPUT_FILE
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=1) + "\n")
    spans = sum(len(s) for case in document["cases"].values() for s in case["slots"].values())
    print(f"{OUTPUT_FILE.as_posix()}: {len(document['cases'])} cases, {spans} spans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The frozen question files must match the hashes in the eval-v1 snapshot before any run starts (EVAL-003a)."""
import hashlib
from pathlib import Path

import pytest

from knowledge_assistant.application.evaluation.integrity import frozen_hashes, sha256_hex, verify_frozen_files
from knowledge_assistant.core.exceptions import IntegrityError

ROOT = Path(__file__).resolve().parents[3]
EVAL_BYTES, DEV_BYTES = b'{"id": "made-up-1"}\n', b'{"id": "made-up-2"}\n'
SNAPSHOT = (
    "| Item | Value |\n|---|---|\n"
    f"| `data/evaluation/questions/eval-v1.jsonl` SHA-256 | `{hashlib.sha256(EVAL_BYTES).hexdigest()}` (36 cases) |\n"
    f"| `data/evaluation/questions/dev-v1.jsonl` SHA-256 | `{hashlib.sha256(DEV_BYTES).hexdigest()}` (6 cases) |\n"
)


def test_matching_files_return_their_hashes():
    hashes = verify_frozen_files(SNAPSHOT, {"eval-v1.jsonl": EVAL_BYTES, "dev-v1.jsonl": DEV_BYTES})
    assert hashes == {"eval-v1.jsonl": sha256_hex(EVAL_BYTES), "dev-v1.jsonl": sha256_hex(DEV_BYTES)}


def test_a_changed_file_aborts_and_names_the_file_and_both_hashes():
    with pytest.raises(IntegrityError) as caught:
        verify_frozen_files(SNAPSHOT, {"eval-v1.jsonl": EVAL_BYTES + b" ", "dev-v1.jsonl": DEV_BYTES})
    message = str(caught.value)
    assert "eval-v1.jsonl" in message and "dev-v1.jsonl" not in message
    assert sha256_hex(EVAL_BYTES + b" ") in message and sha256_hex(EVAL_BYTES) in message
    assert "amendment" in message  # tells the reader what a legitimate change looks like


def test_the_dev_file_is_checked_too():
    with pytest.raises(IntegrityError, match="dev-v1.jsonl"):
        verify_frozen_files(SNAPSHOT, {"eval-v1.jsonl": EVAL_BYTES, "dev-v1.jsonl": b"changed\n"})


def test_a_file_the_snapshot_does_not_list_aborts():
    with pytest.raises(IntegrityError, match="no frozen hash for other-v1.jsonl"):
        verify_frozen_files(SNAPSHOT, {"other-v1.jsonl": b"x"})


def test_a_snapshot_without_hashes_aborts():
    with pytest.raises(IntegrityError, match="no SHA-256 rows"):
        verify_frozen_files("# nothing here\n", {"eval-v1.jsonl": EVAL_BYTES})


def test_the_repository_snapshot_holds_the_hashes_the_owner_named():
    """Owner addendum 2026-09-27: eval 3436870e…2937, dev 37d349e5…21d6."""
    hashes = frozen_hashes((ROOT / "docs" / "snapshots" / "evaluation" / "eval-v1.md").read_text(encoding="utf-8"))
    assert {name: (sha[:8], sha[-4:]) for name, sha in hashes.items()} == {
        "eval-v1.jsonl": ("3436870e", "2937"),
        "dev-v1.jsonl": ("37d349e5", "21d6"),
    }


def test_the_repository_question_files_match_the_snapshot():
    questions = ROOT / "data" / "evaluation" / "questions"
    files = {name: (questions / name).read_bytes() for name in ("eval-v1.jsonl", "dev-v1.jsonl")}
    snapshot = (ROOT / "docs" / "snapshots" / "evaluation" / "eval-v1.md").read_text(encoding="utf-8")
    assert set(verify_frozen_files(snapshot, files)) == {"eval-v1.jsonl", "dev-v1.jsonl"}

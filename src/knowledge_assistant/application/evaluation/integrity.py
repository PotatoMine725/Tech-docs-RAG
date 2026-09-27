"""The frozen question files must equal the hashes in the eval-v1 snapshot before a run starts (EVAL-003a).

`docs/snapshots/evaluation/eval-v1.md` holds one row per file: ``| `data/evaluation/questions/<name>` SHA-256 | `<hex>` ... |``.
Pure: the caller reads the snapshot and the files. Both files are checked whichever split is run, so a quiet edit to
either one stops every run.
"""
import hashlib
import re
from collections.abc import Mapping

from knowledge_assistant.core.exceptions import IntegrityError

_ROW = re.compile(r"`data/evaluation/questions/([\w.\-]+\.jsonl)`\s+SHA-256\s*\|\s*`([0-9a-f]{64})`")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frozen_hashes(snapshot_text: str) -> dict[str, str]:
    """{file name: SHA-256} from the snapshot table."""
    return {name: digest for name, digest in _ROW.findall(snapshot_text)}


def verify_frozen_files(snapshot_text: str, files: Mapping[str, bytes]) -> dict[str, str]:
    """{file name: SHA-256} of `files` when every one equals its frozen hash; otherwise IntegrityError."""
    expected = frozen_hashes(snapshot_text)
    if not expected:
        raise IntegrityError("the eval-v1 snapshot has no SHA-256 rows for the question files; cannot verify them")
    actual = {}
    for name, data in files.items():
        if name not in expected:
            raise IntegrityError(f"the eval-v1 snapshot has no frozen hash for {name}")
        actual[name] = sha256_hex(data)
        if actual[name] != expected[name]:
            raise IntegrityError(
                f"{name}: SHA-256 is {actual[name]} but the frozen snapshot says {expected[name]}. The frozen "
                f"question file changed; a change must be a logged amendment, never a quiet edit. Refusing to run."
            )
    return actual

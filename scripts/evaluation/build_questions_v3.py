"""Expand the dev-v3 drafts into dev-v3.jsonl with the v1 record schema. Offline; v1 and v2 files are not touched.

Input:  data/evaluation/questions/drafts-v3/*.yaml (hand-written, same compact schema as drafts-v2).
Output: data/evaluation/questions/dev-v3.jsonl and evidence-map-v3.yaml (absence proofs ABS3-NNN).
Reuses build_questions_v2.expand (unchanged) and then sets the v3 differences: blueprint_id BP3-*, status DRAFT for
review_status "draft" (owner review pending), and `question_language` (en / vi / mixed: the language mix of the
question text; `language` stays the answer language en / vi).
Run: .venv/Scripts/python.exe scripts/evaluation/build_questions_v3.py
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_questions_v2 as v2  # noqa: E402  (v2 builder, reused read-only)

QUESTIONS = v2.QUESTIONS
DRAFTS = QUESTIONS / "drafts-v3"
OUTPUT = QUESTIONS / "dev-v3.jsonl"
EVIDENCE_MAP = QUESTIONS / "evidence-map-v3.yaml"
QUESTION_LANGUAGES = {"en", "vi", "mixed"}
STATUS = {"draft": "DRAFT", "approved": "approved", "fixed": "fixed"}


def expand(draft: dict, chars: dict, absence_ids: dict) -> dict:
    record = v2.expand(draft, chars, absence_ids)
    record["blueprint_id"] = draft["id"].replace("Q3-", "BP3-")
    record["status"] = STATUS[draft.get("review_status") or "draft"]
    record["question_language"] = draft.get("question_language", draft["language"])
    return record


def load_drafts(folder: Path = DRAFTS) -> list[dict]:
    drafts = [entry for path in sorted(folder.glob("*.yaml"))
              for entry in (yaml.safe_load(path.read_text(encoding="utf-8")) or [])]
    return sorted(drafts, key=lambda d: d["id"])


def build(drafts: list[dict], chars: dict) -> tuple[list[dict], list[dict]]:
    """(records, absence proofs) for the drafts, in ID order."""
    absence, absence_ids = [], {}
    for draft in drafts:
        if not draft["answerable"]:
            proof_id = f"ABS3-{len(absence) + 1:03d}"
            absence_ids[draft["id"]] = proof_id
            absence.append({"id": proof_id, "question": draft["id"], **draft["absence"]})
    return [expand(d, chars, absence_ids) for d in drafts], absence


def main() -> int:
    chars = {d["id"]: d.get("chars") for d in json.loads(v2.C2_MANIFEST.read_text(encoding="utf-8"))["documents"]}
    drafts = load_drafts()
    if any(d["split"] != "dev" for d in drafts):
        raise SystemExit("dev-v3 drafts must all be split: dev")
    records, absence = build(drafts, chars)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    print(f"{OUTPUT.name}: {len(records)} questions")
    header = ("# dev-v3 absence proofs: why each unanswerable dev-v3 question is not answered by the corpus.\n"
              "# Scope: corpus/sources (24 accepted) + corpus2/converted (accepted C2-* only). Method: case-insensitive\n"
              "# search after NFC and diacritic folding (đ->d, combining marks dropped), so each term is checked with and\n"
              "# without diacritics; validate_questions_v3.py re-runs every zero_hit_terms search.\n")
    with EVIDENCE_MAP.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + yaml.safe_dump({"version": 3, "absence_proofs": absence}, allow_unicode=True,
                                             sort_keys=False, width=120))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

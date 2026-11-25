"""Expand the benchmark v2 drafts into question files with the v1 record schema. Offline; v1 files are not touched.

Input:  data/evaluation/questions/drafts-v2/*.yaml (hand-written; one list of compact question entries per file).
Output: data/evaluation/questions/eval-v2.jsonl, dev-v2.jsonl and evidence-map-v2.yaml (absence proofs).
Derived here: blueprint_id, question_chars, tags, generated (null), absence_proof id, default citation_criteria,
size_class for corpus-2 sources (from the manifest's chars), failure_mode default per category.
Every record carries `status` (DRAFT until the owner approves it in the review sheet), `typing` and `corpus`.
Run: .venv/Scripts/python.exe scripts/evaluation/build_questions_v2.py
"""
import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
DRAFTS = QUESTIONS / "drafts-v2"
C2_MANIFEST = PROJECT_ROOT / "corpus2" / "manifest.json"
TAG_FIELDS = ("difficulty", "cognitive_level", "size_class", "failure_mode", "scope")
DEFAULT_FAILURE_MODE = {"C_vi_on_en": "cross_language", "E_identifier_c1": "exact_identifier"}
REFUSAL = "The assistant should explicitly state that the provided collection does not contain sufficient information."


def _size_class(sources: list[dict], chars: dict) -> str:
    sizes = set()
    for source in sources:
        n = chars.get(source["source_id"])
        if n is None:
            return "TBD"
        sizes.add("tiny" if n < 5_000 else "medium" if n < 50_000 else "huge")
    return sizes.pop() if len(sizes) == 1 else "mixed"


def _citation_criteria(draft: dict) -> list[str]:
    if not draft["answerable"]:
        return ["No citation is required; any citation must not be presented as supporting an answer."]
    cites = ", ".join(f"#{s['source_id']}" for s in draft["expected_sources"])
    return [f"Cites {cites}; the cited chunk contains the evidence quote(s).",
            "Citation excerpt stays in the document's original language."]


def expand(draft: dict, chars: dict, absence_ids: dict) -> dict:
    answerable = draft["answerable"]
    sources = draft.get("expected_sources", [])
    typing = draft.get("typing", "en" if draft["language"] == "en" else "diacritics")
    failure_mode = draft.get("failure_mode") or (
        "no_diacritics" if typing == "no_diacritics" else DEFAULT_FAILURE_MODE.get(draft["category"], "none"))
    record = {
        "id": draft["id"],
        "blueprint_id": draft["id"].replace("Q2-", "BP2-"),
        "split": draft["split"],
        "language": draft["language"],
        "parallel_group_id": None,
        "question": draft["question"],
        "question_chars": len(draft["question"]),
        "answerable": answerable,
        "expected_answer": draft["expected_answer"] if answerable else REFUSAL,
        "expected_behavior": None if answerable else REFUSAL,
        "answer_points": draft.get("answer_points", []),
        "expected_sources": sources,
        "acceptable_alternate_sources": draft.get("acceptable_alternate_sources", []),
        "evidence": draft.get("evidence", []),
        "acceptable_variations": draft.get("acceptable_variations", []),
        "must_not_claim": draft["must_not_claim"],
        "citation_criteria": draft.get("citation_criteria") or _citation_criteria(draft),
        "near_miss_sources": draft.get("near_miss_sources", []),
        "absence_proof": absence_ids.get(draft["id"]),
        "scope": draft.get("scope", "single-source" if answerable else "corpus-insufficient"),
        "cognitive_level": draft["cognitive_level"],
        "difficulty": draft["difficulty"],
        "size_class": draft.get("size_class") or ("none" if not answerable else _size_class(sources, chars)),
        "failure_mode": failure_mode,
        "retrieval_challenges": draft.get("retrieval_challenges", [draft["category"]]),
        "concepts": draft.get("concepts", []),
        "status": "DRAFT",
        "typing": typing,
        "corpus": draft["corpus"],
        "category": draft["category"],
    }
    if draft.get("review_status"):  # set only after the owner's review (approved / fixed)
        record["status"] = draft["review_status"]
    record["tags"] = {field: record[field] for field in TAG_FIELDS}
    record["generated"] = {"generated_answer": None, "citations": None, "result": None}
    return record


def main() -> int:
    chars = {d["id"]: d.get("chars") for d in json.loads(C2_MANIFEST.read_text(encoding="utf-8"))["documents"]}
    drafts = [entry for path in sorted(DRAFTS.glob("*.yaml"))
              for entry in (yaml.safe_load(path.read_text(encoding="utf-8")) or [])]
    drafts.sort(key=lambda d: d["id"])
    absence, absence_ids = [], {}
    for draft in drafts:
        if not draft["answerable"]:
            proof_id = f"ABS2-{len(absence) + 1:03d}"
            absence_ids[draft["id"]] = proof_id
            absence.append({"id": proof_id, "question": draft["id"], **draft["absence"]})
    for split in ("eval", "dev"):
        rows = [expand(d, chars, absence_ids) for d in drafts if d["split"] == split]
        with (QUESTIONS / f"{split}-v2.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        print(f"{split}-v2.jsonl: {len(rows)} questions")
    header = ("# Benchmark v2 absence proofs: why each unanswerable v2 question is not answered by the corpus.\n"
              "# Scope: corpus/sources (24 accepted) + corpus2/converted (accepted C2-* only). Method: case-insensitive\n"
              "# fixed-string search; validate_questions_v2.py re-runs every zero_hit_terms search.\n")
    with (QUESTIONS / "evidence-map-v2.yaml").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + yaml.safe_dump({"version": 2, "absence_proofs": absence}, allow_unicode=True,
                                             sort_keys=False, width=120))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

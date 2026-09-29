"""Validate the EVAL-002 question files (eval-v1.jsonl, dev-v1.jsonl) against the corpus. Offline.

Checks (agents/prompts/02-EVAL-002-write-and-freeze.md, step 3):
- schema: required fields and types, allowed values, unique IDs, `tags` equal the flat fields, generated fields null;
- at least 30 eval cases and at least 30 answerable eval cases; both languages in each split;
- parallel EN/VI pairs share sources, heading paths, answer points, evidence and criteria;
- every source_id is an accepted document (never 14/19/24/27 or the non-existent 25);
- every heading path exists in the section inventory;
- every evidence quote is an exact substring of its section's text in the normalized corpus
  (ADR-0003 D1 normalization, EOLs already LF; runs of whitespace collapsed on both sides): the
  anti-hallucination check on ground truth. Any variant of the section counts unless `evidence_variant` is set;
- eval and dev are disjoint (IDs, blueprints, question text, expected sections).
Run: .venv/Scripts/python.exe scripts/evaluation/validate_questions.py   (exit 1 on any error)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
EVAL_FILE = QUESTIONS / "eval-v1.jsonl"
DEV_FILE = QUESTIONS / "dev-v1.jsonl"
INVENTORY = PROJECT_ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
NORMALIZED = PROJECT_ROOT / "data" / "processed" / "documents" / "normalized.jsonl"
MANIFEST = PROJECT_ROOT / "corpus" / "manifest.json"

FORBIDDEN_IDS = {"14", "19", "24", "25", "27"}
MIN_EVAL_CASES = 30
MAX_QUOTE_CHARS = 300
ALLOWED = {
    "split": {"eval", "dev"},
    "language": {"en", "vi"},
    "scope": {"single-source", "cross-document", "corpus-insufficient"},
    "cognitive_level": {"recall", "explain", "apply", "analyze", "compare", "diagnose"},
    "difficulty": {"easy", "medium", "hard"},
    "size_class": {"tiny", "medium", "huge", "mixed", "none"},
    "failure_mode": {
        "mixed_version", "near_duplicate_topk", "fixed_size_code_split", "link_list_noise",
        "tiny_doc_single_chunk", "large_doc_outranks_small", "specific_heading", "repeated_version_sections", "none",
    },
}
TAG_FIELDS = ("difficulty", "cognitive_level", "size_class", "failure_mode", "scope")
FIELD_TYPES = {
    "id": str, "blueprint_id": str, "split": str, "language": str, "question": str, "question_chars": int,
    "answerable": bool, "expected_answer": str, "answer_points": list, "expected_sources": list,
    "acceptable_alternate_sources": list, "evidence": list, "acceptable_variations": list, "must_not_claim": list,
    "citation_criteria": list, "near_miss_sources": list, "scope": str, "cognitive_level": str, "difficulty": str,
    "size_class": str, "failure_mode": str, "retrieval_challenges": list, "concepts": list, "tags": dict, "generated": dict,
}
PARALLEL_SHARED = ("expected_answer", "answer_points", "expected_sources", "acceptable_alternate_sources", "evidence",
                   "acceptable_variations", "must_not_claim", "citation_criteria", "answerable", "scope")
ID_PATTERN = {"eval": re.compile(r"Q-EVAL-\d{3}"), "dev": re.compile(r"Q-DEV-\d{3}")}
SLOT = re.compile(r"S\d+")
# Vietnamese-only letters (with tone/shape marks). An EN question must have none; a VI question must have some.
VIETNAMESE_LETTERS = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.IGNORECASE)


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corpus():
    """(accepted source IDs, inventory heading paths, {(source_id, heading_path): [(variant, collapsed text)]})."""
    accepted = {d["source_id"] for d in json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"]}
    inventory = {(r["source_id"], r["heading_path"]) for r in read_jsonl(INVENTORY)}
    sections = defaultdict(list)
    for record in read_jsonl(NORMALIZED):
        text = record["text"]
        for span in record["metadata"]["sections"]:
            body = collapse_whitespace(text[span["char_start"] : span["char_end"]])
            sections[(record["id"], span["heading_path"])].append((span["variant"], body))
    return accepted, inventory, dict(sections)


def _schema_errors(case: dict, split: str) -> list[str]:
    cid = case.get("id", "?")
    errors = [f"{cid}: missing or wrong type: {field}" for field, kind in FIELD_TYPES.items()
              if not isinstance(case.get(field), kind) or (kind is int and isinstance(case.get(field), bool))]
    if errors:
        return errors
    if not ID_PATTERN[split].fullmatch(cid):
        errors.append(f"{cid}: ID does not match the {split} pattern")
    if case["split"] != split:
        errors.append(f"{cid}: split {case['split']!r} in the {split} file")
    for field, allowed in ALLOWED.items():
        if case[field] not in allowed:
            errors.append(f"{cid}: {field}={case[field]!r} not allowed")
    if not case["question"].strip():
        errors.append(f"{cid}: empty question")
    if case["question_chars"] != len(case["question"]):
        errors.append(f"{cid}: question_chars {case['question_chars']} != {len(case['question'])}")
    has_vietnamese = bool(VIETNAMESE_LETTERS.search(case["question"]))
    if has_vietnamese != (case["language"] == "vi"):
        errors.append(f"{cid}: question text does not look like language {case['language']!r}")
    if case["tags"] != {field: case[field] for field in TAG_FIELDS}:
        errors.append(f"{cid}: tags differ from the flat fields")
    if any(value is not None for value in case["generated"].values()):
        errors.append(f"{cid}: generated fields must be null in the question file")
    if case["answerable"] != (case["scope"] != "corpus-insufficient"):
        errors.append(f"{cid}: answerable does not match scope")
    for point in case["answer_points"]:
        if not (isinstance(point.get("id"), str) and isinstance(point.get("text"), str) and point["text"].strip()
                and isinstance(point.get("required"), bool)):
            errors.append(f"{cid}: malformed answer point {point!r}")
    for entry in case["expected_sources"] + case["acceptable_alternate_sources"]:
        if not SLOT.fullmatch(str(entry.get("slot"))):
            errors.append(f"{cid}: source without a valid evidence slot: {entry!r}")
    return errors


def _ground_truth_errors(case: dict) -> list[str]:
    cid = case["id"]
    errors = []
    if not case["answerable"]:
        if case["expected_sources"] or case["answer_points"] or case["evidence"]:
            errors.append(f"{cid}: an unanswerable case must have no sources, points or evidence")
        if not case.get("expected_behavior"):
            errors.append(f"{cid}: an unanswerable case needs expected_behavior")
        return errors
    if not case["expected_sources"]:
        errors.append(f"{cid}: no expected source")
    points = {p["id"] for p in case["answer_points"]}
    required = {p["id"] for p in case["answer_points"] if p["required"]}
    if not required:
        errors.append(f"{cid}: no required answer point")
    supported = set()
    for evidence in case["evidence"]:
        supports = set(evidence.get("supports") or [])
        if not supports <= points:
            errors.append(f"{cid}: evidence supports unknown points {sorted(supports - points)}")
        supported |= supports
    if required - supported:
        errors.append(f"{cid}: required points without evidence: {sorted(required - supported)}")
    expected_slots = {s["slot"] for s in case["expected_sources"]}
    if {a["slot"] for a in case["acceptable_alternate_sources"]} - expected_slots:
        errors.append(f"{cid}: alternate source in a slot with no expected source")
    if not {s["source_id"] for s in case["expected_sources"]} <= {e["source_id"] for e in case["evidence"]}:
        errors.append(f"{cid}: an expected source has no evidence quote")
    if not case["must_not_claim"] or not case["citation_criteria"]:
        errors.append(f"{cid}: must_not_claim and citation_criteria must not be empty")
    return errors


def _corpus_errors(case: dict, accepted: set, inventory: set, sections: dict) -> list[str]:
    cid = case["id"]
    errors = []
    refs = case["expected_sources"] + case["acceptable_alternate_sources"] + case["evidence"]
    for source_id in [r["source_id"] for r in refs] + case["near_miss_sources"]:
        if source_id in FORBIDDEN_IDS or source_id not in accepted:
            errors.append(f"{cid}: source {source_id!r} is not an accepted document")
    for ref in refs:
        if (ref["source_id"], ref["heading_path"]) not in inventory:
            errors.append(f"{cid}: heading path not in the section inventory: #{ref['source_id']} {ref['heading_path']}")
    wanted_variant = {(s["source_id"], s["heading_path"]): s["evidence_variant"]
                      for s in case["expected_sources"] if "evidence_variant" in s}
    for evidence in case["evidence"]:
        quote = collapse_whitespace(evidence["quote"])
        if not quote or len(evidence["quote"]) > MAX_QUOTE_CHARS:
            errors.append(f"{cid}: quote empty or longer than {MAX_QUOTE_CHARS} chars")
            continue
        key = (evidence["source_id"], evidence["heading_path"])
        variants = [variant for variant, body in sections.get(key, []) if quote in body]
        if not variants:
            errors.append(f"{cid}: quote not found in #{key[0]} {key[1]!r}: {evidence['quote'][:60]!r}")
        elif key in wanted_variant and wanted_variant[key] not in variants:
            errors.append(f"{cid}: quote not in evidence_variant {wanted_variant[key]} of {key[1]!r}")
    return errors


def _parallel_errors(cases: list[dict]) -> list[str]:
    groups = defaultdict(list)
    for case in cases:
        if case.get("parallel_group_id"):
            groups[case["parallel_group_id"]].append(case)
    errors = []
    for group_id, members in sorted(groups.items()):
        if sorted(c["language"] for c in members) != ["en", "vi"]:
            errors.append(f"{group_id}: a parallel group needs exactly one en and one vi case")
            continue
        en, vi = sorted(members, key=lambda c: c["language"])
        errors += [f"{group_id}: {field} differs between {en['id']} and {vi['id']}"
                   for field in PARALLEL_SHARED if en.get(field) != vi.get(field)]
    return errors


def _disjoint_errors(eval_cases: list[dict], dev_cases: list[dict]) -> list[str]:
    errors = []
    for field in ("id", "blueprint_id", "question"):
        shared = {c[field] for c in eval_cases} & {c[field] for c in dev_cases}
        if shared:
            errors.append(f"eval and dev share {field}: {sorted(shared)}")
    sections = [{(s["source_id"], s["heading_path"]) for c in cases for s in c["expected_sources"]}
                for cases in (eval_cases, dev_cases)]
    if sections[0] & sections[1]:
        errors.append(f"eval and dev share expected sections: {sorted(sections[0] & sections[1])}")
    return errors


def validate(eval_cases: list[dict], dev_cases: list[dict], corpus=None) -> list[str]:
    accepted, inventory, sections = corpus or load_corpus()
    errors = []
    for split, cases in (("eval", eval_cases), ("dev", dev_cases)):
        ids = [c.get("id") for c in cases]
        errors += [f"duplicate ID {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        if {c.get("language") for c in cases} != {"en", "vi"}:
            errors.append(f"{split}: both languages (en, vi) are required")
        for case in cases:
            schema = _schema_errors(case, split)
            errors += schema
            if not schema:
                errors += _ground_truth_errors(case)
                errors += _corpus_errors(case, accepted, inventory, sections)
        errors += _parallel_errors(cases)
    if len(eval_cases) < MIN_EVAL_CASES:
        errors.append(f"eval: {len(eval_cases)} cases, at least {MIN_EVAL_CASES} required")
    answerable = sum(1 for c in eval_cases if c.get("answerable") is True)
    if answerable < MIN_EVAL_CASES:
        errors.append(f"eval: {answerable} answerable cases, at least {MIN_EVAL_CASES} required")
    errors += _disjoint_errors(eval_cases, dev_cases)
    return errors


def main() -> int:
    eval_cases, dev_cases = read_jsonl(EVAL_FILE), read_jsonl(DEV_FILE)
    errors = validate(eval_cases, dev_cases)
    quotes = sum(len(c["evidence"]) for c in eval_cases + dev_cases)
    print(f"eval: {len(eval_cases)} cases ({sum(c['answerable'] for c in eval_cases)} answerable); "
          f"dev: {len(dev_cases)} cases; evidence quotes checked: {quotes}")
    for error in errors:
        print(f"ERROR {error}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

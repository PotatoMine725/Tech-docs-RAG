"""Validate the benchmark v2 question files (eval-v2.jsonl, dev-v2.jsonl) against corpus 1 and corpus 2. Offline.

Reuses the v1 checks (scripts/evaluation/validate_questions.py, unchanged) where they apply:
ground-truth structure, whitespace-collapsed exact-substring quotes, corpus-1 loading. v2-specific rules:
- IDs Q2-EVAL-NNN / Q2-DEV-NNN; status DRAFT / approved / fixed (freeze needs every eval and dev case non-DRAFT
  with --frozen); typing diacritics / no_diacritics / en must match the question text (no_diacritics: a vi
  question with no Vietnamese-only letters);
- sources: corpus-1 accepted IDs ("01".."29", never 14/19/24/25/27) or accepted C2-* IDs of corpus2/manifest.json;
- corpus-2 heading paths come from corpus2/converted/sections.jsonl ("" = whole document or preamble); quotes are
  exact substrings of that span's text, at most 300 chars, and never contain "|" (prose only, ADR-0008);
- every absence proof's zero_hit_terms have 0 case-insensitive hits in all accepted documents of both corpora;
- eval and dev v2 are disjoint (IDs, questions, expected sections) and disjoint from v1 question text.
Run: .venv/Scripts/python.exe scripts/evaluation/validate_questions_v2.py [--frozen]   (exit 1 on any error)
Needs a local conversion first: scripts/corpus2/convert_corpus2.py (converted text is git-ignored).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_questions as v1  # noqa: E402  (v1 validator, reused read-only)

PROJECT_ROOT = v1.PROJECT_ROOT
QUESTIONS = v1.QUESTIONS
FILES = {"eval": QUESTIONS / "eval-v2.jsonl", "dev": QUESTIONS / "dev-v2.jsonl"}
EVIDENCE_MAP = QUESTIONS / "evidence-map-v2.yaml"
C2_MANIFEST = PROJECT_ROOT / "corpus2" / "manifest.json"
C2_CONVERTED = PROJECT_ROOT / "corpus2" / "converted"
ID_PATTERN = {"eval": re.compile(r"Q2-EVAL-\d{3}"), "dev": re.compile(r"Q2-DEV-\d{3}")}
STATUSES = {"DRAFT", "approved", "fixed"}
CATEGORIES = {"A_vi_on_vi", "B_en_on_en", "C_vi_on_en", "D_vi_on_mixed", "E_identifier_c1", "F_unanswerable"}
FAILURE_MODES = v1.ALLOWED["failure_mode"] | {
    "cross_language", "no_diacritics", "exact_identifier", "near_duplicate_version", "fragmented_extraction"}
SIZE_CLASSES = v1.ALLOWED["size_class"]
EXTRA_TYPES = {"status": str, "typing": str, "corpus": str, "category": str}


def load_corpus2():
    """(accepted C2 IDs, {(id, heading_path): [(variant, collapsed text)]}, {id: full text})."""
    manifest = json.loads(C2_MANIFEST.read_text(encoding="utf-8"))
    accepted = {d["id"] for d in manifest["documents"] if d["status"] == "accepted"}
    texts = {i: (C2_CONVERTED / f"{i}.md").read_text(encoding="utf-8") for i in sorted(accepted)}
    sections = defaultdict(list)
    for record in v1.read_jsonl(C2_CONVERTED / "sections.jsonl"):
        body = texts[record["source_id"]][record["char_start"]:record["char_end"]]
        sections[(record["source_id"], record["heading_path"])].append((record["variant"], v1.collapse_whitespace(body)))
    return accepted, dict(sections), texts


def _schema_errors(case: dict, split: str) -> list[str]:
    cid = case.get("id", "?")
    errors = [f"{cid}: missing or wrong type: {f}" for f, kind in {**v1.FIELD_TYPES, **EXTRA_TYPES}.items()
              if not isinstance(case.get(f), kind) or (kind is int and isinstance(case.get(f), bool))]
    if errors:
        return errors
    checks = [
        (ID_PATTERN[split].fullmatch(cid), "ID does not match the v2 pattern"),
        (case["split"] == split, f"split {case['split']!r} in the {split} file"),
        (case["status"] in STATUSES, f"status {case['status']!r}"),
        (case["category"] in CATEGORIES, f"category {case['category']!r}"),
        (case["corpus"] in {"corpus1", "corpus2"}, f"corpus {case['corpus']!r}"),
        (case["failure_mode"] in FAILURE_MODES, f"failure_mode {case['failure_mode']!r}"),
        (case["size_class"] in SIZE_CLASSES, f"size_class {case['size_class']!r}"),
        (case["question_chars"] == len(case["question"]), "question_chars mismatch"),
        (case["tags"] == {f: case[f] for f in v1.TAG_FIELDS}, "tags differ from the flat fields"),
        (all(v is None for v in case["generated"].values()), "generated fields must be null"),
        (case["answerable"] == (case["scope"] != "corpus-insufficient"), "answerable does not match scope"),
        (case["question"].strip() != "", "empty question"),
    ]
    errors += [f"{cid}: {message}" for ok, message in checks if not ok]
    for field in ("language", "scope", "cognitive_level", "difficulty"):
        if case[field] not in v1.ALLOWED[field]:
            errors.append(f"{cid}: {field}={case[field]!r} not allowed")
    has_vi = bool(v1.VIETNAMESE_LETTERS.search(case["question"]))
    expected = {"en": (case["language"] == "en", False), "diacritics": (case["language"] == "vi", True),
                "no_diacritics": (case["language"] == "vi", False)}.get(case["typing"])
    if expected is None or not expected[0] or has_vi != expected[1]:
        errors.append(f"{cid}: typing {case['typing']!r} does not fit language {case['language']!r} / question text")
    return errors


def _corpus_errors(case: dict, c1, c2) -> list[str]:
    cid = case["id"]
    c1_accepted, c1_inventory, c1_sections = c1
    c2_accepted, c2_sections, _ = c2
    errors = []
    refs = case["expected_sources"] + case["acceptable_alternate_sources"] + case["evidence"]
    for source_id in [r["source_id"] for r in refs] + case["near_miss_sources"]:
        in_c2 = source_id in c2_accepted
        in_c1 = source_id in c1_accepted and source_id not in v1.FORBIDDEN_IDS
        if not (in_c1 or in_c2):
            errors.append(f"{cid}: source {source_id!r} is not an accepted document")
    for ref in refs:
        key = (ref["source_id"], ref["heading_path"])
        if key not in c1_inventory and key not in c2_sections:
            errors.append(f"{cid}: heading path not in the section inventory: #{key[0]} {key[1]!r}")
    for evidence in case["evidence"]:
        quote = v1.collapse_whitespace(evidence["quote"])
        if not quote or len(evidence["quote"]) > v1.MAX_QUOTE_CHARS:
            errors.append(f"{cid}: quote empty or longer than {v1.MAX_QUOTE_CHARS} chars")
            continue
        key = (evidence["source_id"], evidence["heading_path"])
        if key[0] in c2_accepted and "|" in evidence["quote"]:
            errors.append(f"{cid}: corpus-2 quote taken from a table row (prose only): {evidence['quote'][:60]!r}")
        bodies = c1_sections.get(key, []) + c2_sections.get(key, [])
        if not any(quote in body for _, body in bodies):
            errors.append(f"{cid}: quote not found in #{key[0]} {key[1]!r}: {evidence['quote'][:60]!r}")
    return errors


def _absence_errors(cases: list[dict], c1_texts: dict, c2_texts: dict) -> list[str]:
    proofs = {p["id"]: p for p in (yaml.safe_load(EVIDENCE_MAP.read_text(encoding="utf-8")) or {}).get("absence_proofs", [])}
    corpus = {**{f"#{k}": v.lower() for k, v in c1_texts.items()}, **{f"#{k}": v.lower() for k, v in c2_texts.items()}}
    errors = []
    for case in cases:
        if case["answerable"]:
            continue
        proof = proofs.get(case["absence_proof"])
        if not proof or not proof.get("zero_hit_terms"):
            errors.append(f"{case['id']}: unanswerable case without an absence proof with zero_hit_terms")
            continue
        for term in proof["zero_hit_terms"]:
            hits = sorted(doc for doc, text in corpus.items() if term.lower() in text)
            if hits:
                errors.append(f"{case['id']}: absence term {term!r} found in {hits}")
    return errors


def _corpus1_texts(accepted: set) -> dict:
    return {r["id"]: r["text"] for r in v1.read_jsonl(v1.NORMALIZED) if r["id"] in accepted}


def validate(cases_by_split: dict, frozen: bool = False) -> list[str]:
    c1 = v1.load_corpus()
    c2 = load_corpus2()
    errors = []
    v1_questions = {c["question"] for f in (v1.EVAL_FILE, v1.DEV_FILE) for c in v1.read_jsonl(f)}
    for split, cases in cases_by_split.items():
        ids = [c.get("id") for c in cases]
        errors += [f"duplicate ID {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        for case in cases:
            schema = _schema_errors(case, split)
            errors += schema
            if schema:
                continue
            errors += v1._ground_truth_errors(case)
            errors += _corpus_errors(case, c1, c2)
            if case["question"] in v1_questions:
                errors.append(f"{case['id']}: question text repeats a v1 question")
            if frozen and case["status"] == "DRAFT":
                errors.append(f"{case['id']}: still DRAFT (freeze needs owner approval of every case)")
    eval_cases, dev_cases = cases_by_split.get("eval", []), cases_by_split.get("dev", [])
    for field in ("id", "question"):
        shared = {c.get(field) for c in eval_cases} & {c.get(field) for c in dev_cases}
        if shared:
            errors.append(f"eval-v2 and dev-v2 share {field}: {sorted(shared)}")
    sections = [{(s["source_id"], s["heading_path"]) for c in cs for s in c.get("expected_sources", [])}
                for cs in (eval_cases, dev_cases)]
    if sections[0] & sections[1]:
        errors.append(f"eval-v2 and dev-v2 share expected sections: {sorted(sections[0] & sections[1])}")
    errors += _absence_errors(eval_cases + dev_cases, _corpus1_texts(c1[0]), c2[2])
    return errors


def main() -> int:
    frozen = "--frozen" in sys.argv[1:]
    cases = {split: v1.read_jsonl(path) for split, path in FILES.items()}
    errors = validate(cases, frozen=frozen)
    for split, rows in cases.items():
        print(f"{split}-v2: {len(rows)} cases ({sum(c.get('answerable') is True for c in rows)} answerable), "
              f"evidence quotes: {sum(len(c.get('evidence', [])) for c in rows)}")
    for error in errors:
        print(f"ERROR {error}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

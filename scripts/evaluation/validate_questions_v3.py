"""Validate dev-v3.jsonl (20 dev questions) against corpus 1 and corpus 2, offline, and report the language check.

Reuses the v1 / v2 validators (unchanged) for schema and ground-truth structure. v3 rules:
- IDs Q3-DEV-NNN, split dev, status DRAFT / approved / fixed; typing must fit the question text (v2 rule);
  question_language en / vi / mixed (mixed: answer language vi);
- sources are accepted documents only (never corpus-1 14/19/24/25/27, never an excluded C2-*);
- every heading path is in the section inventory (corpus 1) or corpus2 sections.jsonl;
- every evidence quote, after NFC and whitespace collapsing on both sides, is a substring of its section's text,
  at most 300 chars, and a corpus-2 quote holds no "|" (prose only);
- every absence term has zero hits in all accepted documents of both corpora, matched case-insensitively both as
  written and diacritic-folded (NFD, combining marks dropped, đ -> d), so "with and without diacritics";
- no dev-v3 case expects a section (source + heading path) that an eval-v1 / eval-v2 case expects or accepts as an
  alternate; no question text repeats a v1 / v2 question; the closest v1 / v2 question by word overlap is reported
  and a Jaccard overlap >= PARAPHRASE_LIMIT is an error;
- at most 2 cases per document; the fixed composition of the task (14 answerable, 6 unanswerable, by corpus /
  language / typing) holds.
Language check (report only, never an error): detect_language(question) vs the labelled language.
Run: .venv/Scripts/python.exe scripts/evaluation/validate_questions_v3.py [--c2-converted DIR]
     (DIR defaults to corpus2/converted, or env KA_C2_CONVERTED; converted text is git-ignored, ADR-0008)
Exit 1 on any error.
"""
import argparse
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_questions_v2 as v2  # noqa: E402  (v2 validator, reused read-only)

v1 = v2.v1
PROJECT_ROOT = v2.PROJECT_ROOT
QUESTIONS = v2.QUESTIONS
DEV_FILE = QUESTIONS / "dev-v3.jsonl"
EVIDENCE_MAP = QUESTIONS / "evidence-map-v3.yaml"
EVAL_FILES = (QUESTIONS / "eval-v1.jsonl", QUESTIONS / "eval-v2.jsonl")
OTHER_FILES = EVAL_FILES + (QUESTIONS / "dev-v1.jsonl", QUESTIONS / "dev-v2.jsonl")
ID_PATTERN = re.compile(r"Q3-DEV-\d{3}")
QUESTION_LANGUAGES = {"en", "vi", "mixed"}
MAX_PER_DOCUMENT = 2
PARAPHRASE_LIMIT = 0.5
# Task composition: (answerable, corpus, document language group, question_language, typing) -> count.
# Owner 2026-11-27: Q3-DEV-011 replaced; its corpus-2 VI slot moved to the mixed doc C2-04 (no free VI-doc section left).
COMPOSITION = Counter({
    (True, "corpus1", "en", "en", "en"): 3,
    (True, "corpus1", "en", "vi", "diacritics"): 2,
    (True, "corpus1", "en", "vi", "no_diacritics"): 1,
    (True, "corpus2", "vi", "vi", "diacritics"): 2,
    (True, "corpus2", "mixed", "vi", "diacritics"): 1,
    (True, "corpus2", "vi", "vi", "no_diacritics"): 2,
    (True, "corpus2", "en", "en", "en"): 2,
    (True, "corpus2", "mixed", "mixed", "diacritics"): 1,
    (False, "corpus1", None, "en", "en"): 1,
    (False, "corpus1", None, "vi", "diacritics"): 1,
    (False, "corpus2", None, "vi", "diacritics"): 1,
    (False, "corpus2", None, "vi", "no_diacritics"): 1,
    (False, "corpus2", None, "en", "en"): 1,
    (False, "corpus2", None, "mixed", "diacritics"): 1,
})
_WORDS = re.compile(r"\w+")


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def fold(text: str) -> str:
    """Lower-case, NFD, combining marks dropped, đ -> d: 'Viêm gan C' and 'viem gan c' fold to the same text."""
    decomposed = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def quote_in(quote: str, bodies: list[str]) -> bool:
    needle = v1.collapse_whitespace(nfc(quote))
    return bool(needle) and any(needle in v1.collapse_whitespace(nfc(body)) for body in bodies)


def term_hits(term: str, corpus: dict) -> list[str]:
    """Documents holding the term, as written (case-insensitive, NFC) or diacritic-folded."""
    plain, folded = nfc(term).lower(), fold(term)
    return sorted(doc for doc, (lower, folded_text) in corpus.items() if plain in lower or folded in folded_text)


def jaccard(a: str, b: str) -> float:
    left, right = set(_WORDS.findall(fold(a))), set(_WORDS.findall(fold(b)))
    return len(left & right) / len(left | right) if left | right else 0.0


def doc_language(source_id: str, c2_languages: dict) -> str:
    return "en" if not source_id.startswith("C2-") else c2_languages[source_id]


def schema_errors(case: dict) -> list[str]:
    cid = case.get("id", "?")
    saved = v2.ID_PATTERN
    v2.ID_PATTERN = {**saved, "dev": ID_PATTERN}  # v2 schema rules with the v3 ID pattern
    try:
        errors = v2._schema_errors(case, "dev")
    finally:
        v2.ID_PATTERN = saved
    if errors:
        return errors
    if case.get("question_language") not in QUESTION_LANGUAGES:
        errors.append(f"{cid}: question_language {case.get('question_language')!r}")
    elif case["question_language"] == "mixed" and case["language"] != "vi":
        errors.append(f"{cid}: a mixed VI-EN question is answered in vi")
    elif case["question_language"] != "mixed" and case["question_language"] != case["language"]:
        errors.append(f"{cid}: question_language differs from language")
    if not case["blueprint_id"].startswith("BP3-"):
        errors.append(f"{cid}: blueprint_id {case['blueprint_id']!r}")
    return errors


def corpus_errors(case: dict, c1, c2) -> list[str]:
    cid = case["id"]
    c1_accepted, c1_inventory, c1_sections = c1
    c2_accepted, c2_sections, _ = c2
    errors = []
    refs = case["expected_sources"] + case["acceptable_alternate_sources"] + case["evidence"]
    for source_id in [r["source_id"] for r in refs] + case["near_miss_sources"]:
        if not ((source_id in c1_accepted and source_id not in v1.FORBIDDEN_IDS) or source_id in c2_accepted):
            errors.append(f"{cid}: source {source_id!r} is not an accepted document")
    for ref in refs:
        key = (ref["source_id"], ref["heading_path"])
        if key not in c1_inventory and key not in c2_sections:
            errors.append(f"{cid}: heading path not in the section inventory: #{key[0]} {key[1]!r}")
    for evidence in case["evidence"]:
        key = (evidence["source_id"], evidence["heading_path"])
        quote = evidence["quote"]
        if not quote.strip() or len(quote) > v1.MAX_QUOTE_CHARS:
            errors.append(f"{cid}: quote empty or longer than {v1.MAX_QUOTE_CHARS} chars")
        elif key[0] in c2_accepted and "|" in quote:
            errors.append(f"{cid}: corpus-2 quote taken from a table row (prose only): {quote[:60]!r}")
        elif not quote_in(quote, [body for _, body in c1_sections.get(key, []) + c2_sections.get(key, [])]):
            errors.append(f"{cid}: quote not found (NFC) in #{key[0]} {key[1]!r}: {quote[:60]!r}")
    return errors


def absence_errors(cases: list[dict], proofs: dict, corpus: dict) -> list[str]:
    errors = []
    for case in cases:
        if case["answerable"]:
            continue
        proof = proofs.get(case["absence_proof"])
        if not proof or not proof.get("zero_hit_terms") or proof.get("question") != case["id"]:
            errors.append(f"{case['id']}: unanswerable case without its absence proof / zero_hit_terms")
            continue
        for term in proof["zero_hit_terms"]:
            hits = term_hits(str(term), corpus)
            if hits:
                errors.append(f"{case['id']}: absence term {term!r} found in {hits}")
    return errors


def overlap_errors(cases: list[dict], eval_cases: list[dict]) -> list[str]:
    taken = {(s["source_id"], s["heading_path"]) for c in eval_cases
             for s in c["expected_sources"] + c.get("acceptable_alternate_sources", [])}
    return [f"{c['id']}: expects section #{s['source_id']} {s['heading_path']!r}, which an eval case expects"
            for c in cases for s in c["expected_sources"] + c["acceptable_alternate_sources"]
            if (s["source_id"], s["heading_path"]) in taken]


def closest_questions(cases: list[dict], others: list[dict]) -> list[tuple[str, str, float]]:
    """(dev-v3 id, closest v1/v2 id, Jaccard word overlap after folding) per case."""
    rows = []
    for case in cases:
        best = max(others, key=lambda o: jaccard(case["question"], o["question"]))
        rows.append((case["id"], best["id"], round(jaccard(case["question"], best["question"]), 3)))
    return rows


def composition_errors(cases: list[dict], c2_languages: dict) -> list[str]:
    errors = []
    per_doc = Counter(s["source_id"] for c in cases for s in c["expected_sources"])
    errors += [f"document #{d} is expected by {n} cases (at most {MAX_PER_DOCUMENT})"
               for d, n in sorted(per_doc.items()) if n > MAX_PER_DOCUMENT]
    actual = Counter()
    for c in cases:
        group = None
        if c["answerable"]:
            groups = {doc_language(s["source_id"], c2_languages) for s in c["expected_sources"]}
            group = groups.pop() if len(groups) == 1 else "multi"
        actual[(c["answerable"], c["corpus"], group, c["question_language"], c["typing"])] += 1
    if actual != COMPOSITION:
        errors.append(f"composition differs from the task: missing {dict(COMPOSITION - actual)}, "
                      f"extra {dict(actual - COMPOSITION)}")
    return errors


def language_check(cases: list[dict]) -> list[tuple[str, str, str, str, str]]:
    """(id, question_language, typing, labelled language, detected) for every case."""
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from knowledge_assistant.application.common.language import detect_language

    return [(c["id"], c["question_language"], c["typing"], c["language"], detect_language(c["question"]))
            for c in cases]


def load_corpus2(converted: Path):
    saved = v2.C2_CONVERTED
    v2.C2_CONVERTED = converted
    try:
        return v2.load_corpus2()
    finally:
        v2.C2_CONVERTED = saved


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--c2-converted", type=Path,
                        default=Path(os.environ.get("KA_C2_CONVERTED", PROJECT_ROOT / "corpus2" / "converted")))
    args = parser.parse_args(argv)
    cases = v1.read_jsonl(DEV_FILE)
    c1 = v1.load_corpus()
    c2 = load_corpus2(args.c2_converted)
    c2_languages = {d["id"]: d.get("language") for d in v2.json.loads(v2.C2_MANIFEST.read_text(encoding="utf-8"))["documents"]}
    proofs = {p["id"]: p for p in (yaml.safe_load(EVIDENCE_MAP.read_text(encoding="utf-8")) or {}).get("absence_proofs", [])}
    corpus_texts = {**{f"#{k}": v for k, v in v2._corpus1_texts(c1[0]).items()}, **{f"#{k}": v for k, v in c2[2].items()}}
    corpus = {doc: (nfc(text).lower(), fold(text)) for doc, text in corpus_texts.items()}
    eval_cases = [c for f in EVAL_FILES for c in v1.read_jsonl(f)]
    others = [c for f in OTHER_FILES for c in v1.read_jsonl(f)]

    errors = []
    ids = [c.get("id") for c in cases]
    errors += [f"duplicate ID {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    valid = []
    for case in cases:
        schema = schema_errors(case)
        errors += schema
        if not schema:
            valid.append(case)
            errors += v1._ground_truth_errors(case) + corpus_errors(case, c1, c2)
    other_questions = {o["question"] for o in others}
    errors += [f"{c['id']}: question text repeats a v1/v2 question" for c in valid if c["question"] in other_questions]
    errors += absence_errors(valid, proofs, corpus)
    errors += overlap_errors(valid, eval_cases)
    errors += composition_errors(valid, c2_languages)
    errors += v2._conversion_errors(c2[2])
    closest = closest_questions(valid, others)
    errors += [f"{cid}: word overlap {score} with {oid} (paraphrase limit {PARAPHRASE_LIMIT})"
               for cid, oid, score in closest if score >= PARAPHRASE_LIMIT]

    quotes = sum(len(c["evidence"]) for c in valid)
    terms = sum(len(p.get("zero_hit_terms", [])) for p in proofs.values())
    print(f"dev-v3: {len(cases)} cases ({sum(c['answerable'] for c in valid)} answerable), "
          f"evidence quotes: {quotes}, absence terms: {terms}, documents scanned: {len(corpus)}")
    print(f"closest v1/v2 question (Jaccard word overlap, max {max((s for *_, s in closest), default=0)}):")
    for cid, oid, score in closest:
        print(f"  {cid} ~ {oid}: {score}")
    print("language check (detect_language vs labelled language; report only):")
    for cid, mix, typing, labelled, detected in language_check(valid):
        flag = "" if detected == labelled else "  MISMATCH"
        print(f"  {cid} question={mix} typing={typing} labelled={labelled} detected={detected}{flag}")
    for error in errors:
        print(f"ERROR {error}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

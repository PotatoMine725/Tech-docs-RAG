"""Expected section spans of the benchmark v2 cases (eval-v2 + dev-v2) -> expected-spans-v2.json. Offline.

Same rule and schema as expected-spans-v1.json (`metrics.spans.case_spans`): every expected / alternate
(source_id, heading path) of a case -> all its [char_start, char_end) spans in the ingested text. Corpus-1 cases (E,
part of F) use the corpus-1 normalized.jsonl sections; corpus-2 cases use the corpus-2 inventory on the NFC text
(data/processed/documents-corpus2/sections.jsonl, written by scripts/corpus2/ingest_corpus2.py), which keeps the
frozen whole-document span "" of heading-less documents. Both splits are covered (v1's spans covered eval only).
Every corpus-2 evidence quote is checked to lie, in NFC, inside one of its section's spans; exit 1 otherwise.
Run: .venv/Scripts/python.exe scripts/evaluation/build_expected_spans_v2.py
"""
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.evaluation.metrics.spans import case_spans, section_index  # noqa: E402
from knowledge_assistant.config import get_normalized_path  # noqa: E402

QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
FILES = ("eval-v2.jsonl", "dev-v2.jsonl")
OUTPUT = QUESTIONS / "expected-spans-v2.json"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _comparable(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text))


def main() -> int:
    corpus1 = _read_jsonl(get_normalized_path("corpus1"))
    c2_path = get_normalized_path("corpus2")
    c2_texts = {r["id"]: r["text"] for r in _read_jsonl(c2_path)}
    index = dict(section_index(corpus1))
    c2_index = defaultdict(list)
    for span in _read_jsonl(c2_path.with_name("sections.jsonl")):
        c2_index[(span["source_id"], span["heading_path"])].append((span["variant"], span["char_start"], span["char_end"]))
    index.update(c2_index)

    cases, inputs = [], {}
    for name in FILES:
        path = QUESTIONS / name
        inputs[name] = {"path": path.relative_to(PROJECT_ROOT).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        cases += _read_jsonl(path)

    errors, result = [], {}
    for case in cases:
        slots = defaultdict(list)
        for span in case_spans(case, index):
            slots[span.slot].append({"role": span.role, "source_id": span.source_id, "heading_path": span.heading_path,
                                     "variant": span.variant, "char_start": span.char_start, "char_end": span.char_end})
        result[case["id"]] = {"answerable": case["answerable"], "corpus": case["corpus"],
                              "slots": {slot: slots[slot] for slot in sorted(slots, key=lambda s: int(s[1:]))}}
        for evidence in case["evidence"]:
            if not evidence["source_id"].startswith("C2-"):
                continue
            spans = c2_index[(evidence["source_id"], evidence["heading_path"])]
            text = c2_texts[evidence["source_id"]]
            if not any(_comparable(evidence["quote"]) in _comparable(text[s:e]) for _, s, e in spans):
                errors.append(f"{case['id']}: quote not inside {evidence['source_id']} {evidence['heading_path']!r}")

    data = {
        "schema_version": 1,
        "rule": "As expected-spans-v1.json. Offsets index the ingested text: corpus 1 normalized.jsonl, corpus 2 the "
                "NFC text (ADR-0008). Corpus-2 heading path \"\" = the whole document (heading-less) or its preamble.",
        "inputs": {"questions": inputs,
                   "corpus2_sections_sha256": hashlib.sha256(c2_path.with_name("sections.jsonl").read_bytes()).hexdigest()},
        "cases": result,
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    answerable = sum(entry["answerable"] for entry in result.values())
    print(f"{len(result)} cases ({answerable} answerable) -> {OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

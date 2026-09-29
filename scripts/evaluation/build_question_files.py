"""Build the EVAL-002 question files from the approved blueprints plus the question wording.

Reads data/evaluation/questions/blueprint.yaml (ground truth, EVAL-001) and question-wording-v1.yaml (EVAL-002).
Writes data/evaluation/questions/eval-v1.jsonl and dev-v1.jsonl, one case per line (schema:
docs/specs/evaluation-dataset-design.md §18 + the 09a runner fields). Ground truth is copied, never rewritten,
so a question file can only differ from its blueprint in the wording. Generated fields stay null here: answers,
citations and results live in the per-arm result files (EVAL-003a). Deterministic output.
Run: .venv/Scripts/python.exe scripts/evaluation/build_question_files.py
"""
import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
BLUEPRINTS = QUESTIONS / "blueprint.yaml"
WORDING = QUESTIONS / "question-wording-v1.yaml"
OUTPUTS = {"eval": QUESTIONS / "eval-v1.jsonl", "dev": QUESTIONS / "dev-v1.jsonl"}
REFUSAL = "The assistant should explicitly state that the provided collection does not contain sufficient information."
TAG_FIELDS = ("difficulty", "cognitive_level", "size_class", "failure_mode", "scope")
GENERATED_FIELDS = ("generated_answer", "citations", "result")


def _source(entry: dict, with_note: bool) -> dict:
    out = {"source_id": entry["source_id"], "heading_path": entry["heading_path"], "slot": entry["slot"]}
    if "evidence_variant" in entry:
        out["evidence_variant"] = entry["evidence_variant"]
    if with_note:
        out["note"] = entry.get("note")
    return out


def build_case(blueprint: dict, wording: dict) -> dict:
    ground_truth = blueprint["ground_truth"]
    answerable = blueprint["scope"] != "corpus-insufficient"
    required = [p["text"] for p in ground_truth["answer_points"] if p["required"]]
    criteria = blueprint["answer_acceptance_criteria"]
    flat = {
        "scope": blueprint["scope"],
        "cognitive_level": blueprint["cognitive_level"],
        "difficulty": blueprint["difficulty"],
        "size_class": blueprint["size_class"],
        "failure_mode": blueprint["evaluation_target"]["failure_mode"],
    }
    return {
        "id": wording["id"],
        "blueprint_id": blueprint["id"],
        "split": blueprint["split"],
        "language": blueprint["language"],
        "parallel_group_id": blueprint["parallel_group_id"],
        "question": wording["question"],
        "question_chars": len(wording["question"]),
        "answerable": answerable,
        # --- ground truth (frozen at eval-freeze-v1) ---
        "expected_answer": " ".join(required) if answerable else REFUSAL,
        "expected_behavior": None if answerable else blueprint["evaluation_target"]["expected_behavior"],
        "answer_points": [{"id": p["id"], "text": p["text"], "required": p["required"]} for p in ground_truth["answer_points"]],
        "expected_sources": [_source(s, with_note=False) for s in blueprint["expected_sources"]],
        "acceptable_alternate_sources": [_source(s, with_note=True) for s in blueprint["acceptable_alternate_sources"]],
        "evidence": [
            {"source_id": e["source_id"], "heading_path": e["heading_path"], "quote": e["quote"], "supports": e["supports"]}
            for e in ground_truth["evidence"]
        ],
        "acceptable_variations": criteria["acceptable_variations"],
        "must_not_claim": criteria["must_not_claim"],
        "citation_criteria": blueprint["citation_acceptance_criteria"],
        "near_miss_sources": blueprint.get("near_miss_sources", []),
        "absence_proof": blueprint.get("absence_proof"),
        # --- slicing metadata (design §15/§18; `tags` is the 09a runner's grouping of the same values) ---
        **flat,
        "retrieval_challenges": blueprint["retrieval_challenges"],
        "concepts": blueprint["concepts"],
        "tags": {field: flat[field] for field in TAG_FIELDS},
        # --- generated fields: always null in the question file; filled only in per-arm result files ---
        "generated": {field: None for field in GENERATED_FIELDS},
    }


def build() -> dict[str, list[dict]]:
    blueprints = yaml.safe_load(BLUEPRINTS.read_text(encoding="utf-8"))["blueprints"]
    wording = yaml.safe_load(WORDING.read_text(encoding="utf-8"))["cases"]
    by_blueprint = {w["blueprint_id"]: w for w in wording}
    if len(by_blueprint) != len(wording) or set(by_blueprint) != {b["id"] for b in blueprints}:
        raise ValueError("question-wording-v1.yaml must word every blueprint exactly once")
    files: dict[str, list[dict]] = {split: [] for split in OUTPUTS}
    for blueprint in blueprints:
        files[blueprint["split"]].append(build_case(blueprint, by_blueprint[blueprint["id"]]))
    return files


def render(cases: list[dict]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases)


def main() -> int:
    for split, cases in build().items():
        with OUTPUTS[split].open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(render(cases))
        print(f"wrote {OUTPUTS[split].relative_to(PROJECT_ROOT).as_posix()}: {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

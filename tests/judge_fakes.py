"""Offline doubles for the judge and scoring tests (EVAL-003b). Case ids and texts are made up: no eval-set content."""
import json
from pathlib import Path

from knowledge_assistant.application.evaluation.judge import JudgeConfig, parse_template
from knowledge_assistant.application.evaluation.records import assemble
from tests.eval_fakes import make_case, response

ROOT = Path(__file__).resolve().parents[1]
JUDGE_MODEL = "test-judge-model"
CONFIG = JudgeConfig(model=JUDGE_MODEL, prompt_version="judge_v1", prompt_sha256="a" * 64, max_output_tokens=2048)
TEMPLATES = parse_template((ROOT / "config" / "prompts" / "judge_v1.md").read_text(encoding="utf-8"))


def chunk_entry(n: int, text: str | None = None) -> dict:
    return {"rank": n, "chunk_id": f"{n:02d}:header-1600:0000", "source_id": f"{n:02d}", "heading_path": f"Doc > Part {n}",
            "char_start": 0, "char_end": 20, "score": 0.9, "display_text": text or f"Passage body {n}.",
            "passage_hash": f"h{n}", "duplicate_chunk_ids": []}


def make_record(n=1, answerable=True, answer="Part 1 says so [1].", insufficient=False, missing=None, cited=(1,),
                arm="A", status="ok", mode="full", points=None) -> dict:
    case = make_case(n, answerable=answerable)
    if points is not None:
        case["answer_points"] = points
        case["evidence"] = [{"source_id": "01", "heading_path": "Doc > Part 1", "quote": "q", "supports": [p["id"]]}
                            for p in points]
    retrieved = [chunk_entry(i) for i in (1, 2, 3)]
    citations = [{"marker": m, "chunk_id": retrieved[m - 1]["chunk_id"], "source_id": retrieved[m - 1]["source_id"],
                  "heading_path": retrieved[m - 1]["heading_path"]} for m in cited]
    generated = {"llm_called": True, "retrieved": retrieved, "answer": answer, "insufficient": insufficient,
                 "missing_information": missing, "citations": citations} if status == "ok" else {}
    return assemble("run-1", case, arm, mode, "dev", status, "t0", "t1", generated)


def answer_verdict(points=(("P1", "yes"),), markers=((1, "yes"),), contradicts=False, unsupported=()) -> str:
    return json.dumps({"required_points": [{"id": i, "point": "p", "covered": c} for i, c in points],
                       "contradicts_ground_truth": contradicts, "unsupported_claims": list(unsupported),
                       "citations": [{"marker": m, "supports_attached_claim": s} for m, s in markers],
                       "reason": "Fine."})


def refusal_verdict(presents: bool) -> str:
    return json.dumps({"presents_related_as_answer": presents, "reason": "Checked."})


class MemoryJudgementStore:
    def __init__(self, manifest=None) -> None:
        self.manifest = manifest
        self.lines: list[dict] = []

    def read_manifest(self):
        return self.manifest

    def read_judgements(self):
        return json.loads(json.dumps(self.lines))

    def append_judgement(self, entry: dict) -> None:
        self.lines.append(json.loads(json.dumps(entry, allow_nan=False)))



def ok_response(text: str, **kwargs):
    return response(text, model=JUDGE_MODEL, **kwargs)

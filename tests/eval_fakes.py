"""Offline doubles for the evaluation runner tests (EVAL-003a). Case ids and texts are made up: no eval-set content."""
import json
from pathlib import Path

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import RetrievalResult
from knowledge_assistant.core.interfaces.llm import LLMResponse
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import make_chunk

ROOT = Path(__file__).resolve().parents[1]
ANSWER_MODEL = "test-answer-model"
PROMPT_VERSION = "answer_v2"


def make_case(n: int, answerable: bool = True, language: str = "en") -> dict:
    """A dataset case shaped like the frozen question files (all ground-truth fields, plus fields the runner must
    not copy). Case n is answered from passage n: its evidence quote is the body of chunk n."""
    case_id = f"Q-TEST-{n:03d}"
    question = f"What does part {n} say?" if language == "en" else f"Phần {n} nói gì?"
    return {
        "id": case_id,
        "split": "dev",
        "blueprint_id": f"BP-TEST-{n:03d}",
        "concepts": ["not copied"],
        "question": question,
        "language": language,
        "parallel_group_id": f"PG-TEST-{n:03d}",
        "answerable": answerable,
        "expected_answer": f"Part {n} says so." if answerable else "",
        "answer_points": [{"id": "P1", "text": f"Part {n} says so.", "required": True}] if answerable else [],
        "expected_sources": [{"source_id": f"{n:02d}", "heading_path": f"Doc > Part {n}", "slot": "S1"}]
        if answerable else [],
        "acceptable_alternate_sources": [],
        "evidence": [{"source_id": f"{n:02d}", "heading_path": f"Doc > Part {n}", "quote": f"Passage body {n}.",
                      "supports": ["P1"]}] if answerable else [],
        "acceptable_variations": [],
        "must_not_claim": [],
        "citation_criteria": [f"Cites part {n}."],
        "tags": {"difficulty": "easy", "cognitive_level": "recall", "size_class": "tiny",
                 "failure_mode": "none", "scope": "single-source" if answerable else "corpus-insufficient"},
    }


def make_cases(count: int) -> list[dict]:
    return [make_case(n) for n in range(1, count + 1)]


def answer_json(answer="Part says so [1].", cited=(1,), insufficient=False, missing="") -> str:
    return json.dumps({"insufficient": insufficient, "answer": answer, "cited_passages": list(cited),
                       "missing_information": missing})


class ScriptedRetriever:
    """Retriever double: seven passages, ranks 1..5, the top score per question scripted (default 0.8).

    `failures` maps a question to an exception raised when it is retrieved; `duplicates` is what every result reports.
    """

    def __init__(self, top_scores: dict[str, float] | None = None, failures: dict[str, Exception] | None = None,
                 duplicates_dropped: int = 0, duplicate_ids: tuple[str, ...] = ()) -> None:
        self.top_scores = top_scores or {}
        self.failures = failures or {}
        self.duplicates_dropped = duplicates_dropped
        self.duplicate_ids = duplicate_ids
        self.calls: list[str] = []
        self.top_k = 5

    def retrieve(self, question: str) -> RetrievalResult:
        self.calls.append(question)
        if question in self.failures:
            raise self.failures[question]
        top = self.top_scores.get(question, 0.8)
        chunks = tuple(
            RetrievedChunk(make_chunk(f"{i:02d}", i, f"Passage body {i}.", ("Doc", f"Part {i}")), rank=i,
                           score=top - (i - 1) / 100, duplicate_chunk_ids=self.duplicate_ids if i == 1 else ())
            for i in range(1, 6)
        )
        return RetrievalResult(chunks, self.duplicates_dropped, {"embed_query": 2.0, "retrieve": 3.0})


class ScriptedLLM:
    """LLM double. `outcomes` is consumed one per generate() call: an Exception is raised, an LLMResponse is returned
    as is, "ok" becomes the default JSON answer, any other str is the raw model text; when it runs out the default
    answer is returned. `requests` counts calls."""

    def __init__(self, *outcomes, model: str = ANSWER_MODEL) -> None:
        self.outcomes = list(outcomes)
        self.model = model
        self.requests: list = []

    def generate(self, request) -> LLMResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if self.outcomes else answer_json()
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, LLMResponse):
            return outcome
        return response(answer_json() if outcome == "ok" else outcome, model=self.model)


def response(text: str, model: str = ANSWER_MODEL, retry_count: int = 0, fallback_used: bool = False,
             thoughts_tokens: int | None = 7, retry_wait_ms: float = 0.0, throttle_wait_ms: float = 0.0) -> LLMResponse:
    return LLMResponse(text=text, model_used=model, retry_count=retry_count, fallback_used=fallback_used,
                       prompt_tokens=100, output_tokens=20, latency_ms=50.0, thoughts_tokens=thoughts_tokens,
                       retry_wait_ms=retry_wait_ms, throttle_wait_ms=throttle_wait_ms)


def make_answerer(retriever: ScriptedRetriever, llm, threshold: float = 0.5) -> AnswerQuestion:
    messages = load_messages(ROOT / "config" / "messages.json")
    ticks = iter(range(10_000))
    return AnswerQuestion(retriever, llm, PromptBuilder.from_dir(ROOT / "config" / "prompts", PROMPT_VERSION),
                          messages, threshold, clock=lambda: next(ticks) / 1000)


class MemoryRecordStore:
    """RecordStore double that outlives one RunEvaluation, so a test can 'restart' the runner on the same run."""

    def __init__(self) -> None:
        self.manifest: dict | None = None
        self.records: list[dict] = []
        self.errors: list[dict] = []

    def read_manifest(self):
        return json.loads(json.dumps(self.manifest)) if self.manifest is not None else None

    def write_manifest(self, manifest: dict) -> None:
        self.manifest = json.loads(json.dumps(manifest))  # a copy, like a file

    def read_records(self):
        return json.loads(json.dumps(self.records))

    def append_record(self, record: dict) -> None:
        self.records.append(json.loads(json.dumps(record, allow_nan=False)))  # must be JSON-serializable

    def append_error(self, entry: dict) -> None:
        self.errors.append(json.loads(json.dumps(entry, allow_nan=False)))

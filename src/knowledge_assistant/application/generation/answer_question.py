"""Ask a question → grounded answer with citations, or an explicit "insufficient information" (RAG-002).

Two insufficient layers (OD-9, retrieval-spec.md):
  (a) retrieval gate: top-1 score < threshold → the LLM is not called, `insufficient_reason="retrieval_gate"`;
  (b) LLM layer: the model answers `"insufficient": true` → `insufficient_reason="llm"`.
An insufficient answer shows the localized message, keeps `missing_information`, and may keep related citations
(owner decision D2, 2026-09-24). Unusable LLM output raises GenerationError, and a provider failure raises an LLMError
(quota | unavailable | other, RAG-003); neither is ever turned into "insufficient".
"""
import json
import time
from collections.abc import Callable
from pathlib import Path

from knowledge_assistant.application.citation.citations import count_uncited_sentences, resolve_citations
from knowledge_assistant.application.common.language import detect_language
from knowledge_assistant.application.generation.prompt_builder import ANSWER_SCHEMA, PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import GenerationError
from knowledge_assistant.core.interfaces.llm import LLM, LLMRequest
from knowledge_assistant.core.models import AnswerResult

RETRIEVAL_GATE = "retrieval_gate"
LLM_LAYER = "llm"


def load_messages(path: str | Path) -> dict[str, str]:
    """{language: insufficient-information message} from `config/messages.json`."""
    messages = json.loads(Path(path).read_text(encoding="utf-8"))["insufficient"]
    for language in ("en", "vi"):
        if not messages.get(language):
            raise ValueError(f"messages file lacks the '{language}' insufficient message")
    return messages


def parse_answer_json(text: str) -> dict:
    """The LLM's JSON answer, type-checked against ANSWER_SCHEMA. Raises GenerationError with the raw text."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise GenerationError(f"LLM output is not valid JSON: {error}", raw_text=text) from error
    if not isinstance(data, dict):
        raise GenerationError("LLM output is not a JSON object", raw_text=text)
    checks = {
        "insufficient": lambda v: isinstance(v, bool),
        "answer": lambda v: isinstance(v, str),
        "cited_passages": lambda v: isinstance(v, list)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in v),
        "missing_information": lambda v: isinstance(v, str),
    }
    wrong = [key for key, check in checks.items() if key not in data or not check(data[key])]
    if wrong:
        raise GenerationError(f"LLM JSON has missing or mistyped keys: {wrong}", raw_text=text)
    if not data["insufficient"] and not data["answer"].strip():
        raise GenerationError("LLM answered insufficient=false with an empty answer", raw_text=text)
    return data


class AnswerQuestion:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLM,
        prompt_builder: PromptBuilder,
        messages: dict[str, str],
        threshold: float,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._prompts = prompt_builder
        self._messages = messages
        self.threshold = threshold
        self._clock = clock

    def ask(self, question: str) -> AnswerResult:
        start = self._clock()
        language = detect_language(question)
        retrieval = self._retriever.retrieve(question)
        retrieved = retrieval.chunks
        latency = dict(retrieval.latency_ms)
        common = {
            "question": question,
            "language": language,
            "retrieved": retrieved,
            "prompt_version": self._prompts.version,
            "duplicates_dropped": retrieval.duplicates_dropped,
        }

        if retrieved[0].score < self.threshold:
            latency["total"] = (self._clock() - start) * 1000.0
            return AnswerResult(
                answer=self._messages[language], insufficient=True, insufficient_reason=RETRIEVAL_GATE,
                missing_information=None, citations=(), dropped_markers=(), uncited_sentences=0,
                latency_ms=latency, llm=None, **common,
            )

        prompt = self._prompts.build(question, language, retrieved)
        generate_start = self._clock()
        response = self._llm.generate(LLMRequest(prompt=prompt, response_schema=ANSWER_SCHEMA))
        latency["generate"] = (self._clock() - generate_start) * 1000.0  # wall time: model + waits + failed attempts
        latency["retry_wait"] = response.retry_wait_ms  # backoff between attempts (RAG-003)
        latency["throttle_wait"] = response.throttle_wait_ms  # client-side per-minute throttle (RAG-003)
        data = parse_answer_json(response.text)

        answer, citations, dropped = resolve_citations(data["answer"], data["cited_passages"], retrieved)
        missing = data["missing_information"].strip() or None
        insufficient = data["insufficient"]
        latency["total"] = (self._clock() - start) * 1000.0
        return AnswerResult(
            answer=self._messages[language] if insufficient else answer,
            insufficient=insufficient,
            insufficient_reason=LLM_LAYER if insufficient else None,
            missing_information=missing,
            citations=citations,  # when insufficient: related content only (D2)
            dropped_markers=dropped,
            uncited_sentences=0 if insufficient else count_uncited_sentences(answer),
            latency_ms=latency,
            llm=response,
            **common,
        )

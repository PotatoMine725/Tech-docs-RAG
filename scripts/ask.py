"""Ask one question end to end: retrieve, answer from the passages, cite (RAG-003).

    python scripts/ask.py "What is dependency injection?" [--arm A|B] [--json] [--gate-off]

Prints the answer, numbered citations (document, heading path, excerpt), the insufficient-information flag, the
latency per stage, the model that answered and the token counts. A question whose embedding is not cached spends one
embedding request; the answer spends one LLM request, plus retries and the single fallback call when the answer model
fails (ALLOW_FALLBACK=false turns the fallback off). Reads GEMINI_API_KEY from the environment or .env; the key is
never printed.

--gate-off is a DIAGNOSTIC ONLY: it disables the retrieval gate so a low-scoring question still reaches the LLM, to
check the LLM's own "insufficient" answer. The evaluation runner never uses it.

Exit codes: 0 answered (an "insufficient" answer is still 0), 2 provider failure (quota / unavailable / other),
3 unusable model output, 4 setup or retrieval failure (missing index, missing key, embedding failure).
"""
import argparse
import contextlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.composition import ARMS, build_answer_service, open_embedder  # noqa: E402
from knowledge_assistant.config import get_logs_dir  # noqa: E402
from knowledge_assistant.core.exceptions import (  # noqa: E402
    ConfigurationError,
    EmbeddingError,
    GenerationError,
    KnowledgeAssistantError,
    LLMError,
    RetrievalError,
    VectorStoreError,
)
from knowledge_assistant.core.models import AnswerResult  # noqa: E402
from knowledge_assistant.infrastructure.gemini_retry import redact_key  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: E402


@contextlib.contextmanager
def open_service(arm: str, gate_off: bool):
    """(AnswerQuestion, GeminiLLM) for one arm; the query embedder is closed on exit."""
    llm = GeminiLLM()
    with open_embedder() as embedder:
        yield build_answer_service(arm, llm, embedder, gate_off=gate_off), llm


def _threshold(result_threshold: float) -> float | None:
    return None if result_threshold == float("-inf") else result_threshold


def result_to_dict(result: AnswerResult, arm: str, threshold: float) -> dict:
    llm = result.llm
    return {
        "question": result.question,
        "arm": arm,
        "language": result.language,
        "answer": result.answer,
        "insufficient": result.insufficient,
        "insufficient_reason": result.insufficient_reason,
        "missing_information": result.missing_information,
        "citations": [
            {
                "marker": c.marker,
                "document_name": c.document_name,
                "location": c.location,
                "location_type": c.location_type,
                "excerpt": c.excerpt,
                "source_id": c.source_id,
                "chunk_id": c.chunk_id,
                "source_url": c.source_url,
                "related_only": result.insufficient,  # under D2 every citation of an insufficient answer is related-only
            }
            for c in result.citations
        ],
        "llm_called": llm is not None,
        "model_used": llm.model_used if llm else None,
        "retry_count": llm.retry_count if llm else None,
        "fallback_used": llm.fallback_used if llm else None,
        "tokens": {
            "prompt": llm.prompt_tokens if llm else None,
            "output": llm.output_tokens if llm else None,
            "thoughts": llm.thoughts_tokens if llm else None,
        },
        "latency_ms": {stage: round(ms, 1) for stage, ms in result.latency_ms.items()},
        "retrieval": {
            "top1_score": round(result.retrieved[0].score, 4),
            "threshold": _threshold(threshold),
            "gate_off": _threshold(threshold) is None,
            "duplicates_dropped": result.duplicates_dropped,
        },
        "prompt_version": result.prompt_version,
        "dropped_markers": list(result.dropped_markers),
        "uncited_sentences": result.uncited_sentences,
    }


def render_text(result: AnswerResult, arm: str, threshold: float) -> str:
    llm = result.llm
    lines = [f"Question: {result.question}", f"Arm {arm} | language {result.language} | prompt {result.prompt_version}"]
    if _threshold(threshold) is None:
        lines.append("*** GATE OFF: diagnostic run, the retrieval gate is disabled. Never used for evaluation. ***")
    lines += ["", "Answer:", result.answer, ""]
    if result.insufficient:
        lines.append(f"Insufficient information: yes ({result.insufficient_reason})")
    else:
        lines.append("Insufficient information: no")
    if result.missing_information:
        lines.append(f"Missing information: {result.missing_information}")
    if result.citations:
        lines += ["", "Citations (related content only; they do not answer the question):"
                  if result.insufficient else "Citations:"]
        for citation in result.citations:
            excerpt = " ".join(citation.excerpt.split())  # already a <= 300-character prefix of the passage
            lines += [f"  [{citation.marker}] {citation.document_name} — {citation.location}", f"      {excerpt}"]
    lines.append("")
    lines.append("Latency (ms): " + ", ".join(f"{stage} {ms:.0f}" for stage, ms in result.latency_ms.items()))
    if llm:
        lines.append(f"Model: {llm.model_used} (retries {llm.retry_count}, fallback {'yes' if llm.fallback_used else 'no'})")
        thoughts = "n/a" if llm.thoughts_tokens is None else llm.thoughts_tokens
        prompt = "n/a" if llm.prompt_tokens is None else llm.prompt_tokens
        output = "n/a" if llm.output_tokens is None else llm.output_tokens
        lines.append(f"Tokens: prompt {prompt}, output {output}, thoughts {thoughts}")
    else:
        lines.append("Model: none (no LLM call: the retrieval gate refused)")
        lines.append("Tokens: none")
    shown = _threshold(threshold)
    lines.append(
        f"Retrieval: top-1 score {result.retrieved[0].score:.4f}, threshold "
        f"{'off' if shown is None else f'{shown:.4f}'}, duplicates dropped {result.duplicates_dropped}"
    )
    return "\n".join(lines) + "\n"


def _save_error_body(error: LLMError) -> str | None:
    """The provider's error body (key redacted) goes to data/logs so a 429 can be inspected; returns the file name."""
    if not error.provider_body:
        return None
    path = get_logs_dir() / f"ask-{error.kind}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_key(error.provider_body), encoding="utf-8")
    return path.name


def _classify(error: KnowledgeAssistantError) -> tuple[int, str]:
    if isinstance(error, LLMError):
        return 2, error.kind
    if isinstance(error, GenerationError):
        return 3, "generation"
    if isinstance(error, (ConfigurationError, VectorStoreError)):
        return 4, "setup"
    if isinstance(error, (EmbeddingError, RetrievalError)):
        return 4, "retrieval"
    return 4, "error"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--arm", choices=ARMS, default="A", help="experiment arm (default A)")
    parser.add_argument("--json", action="store_true", help="print one JSON document instead of text")
    parser.add_argument("--gate-off", action="store_true", help="DIAGNOSTIC ONLY: disable the retrieval gate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, factory=open_service, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        with factory(args.arm, args.gate_off) as (service, llm):
            result = service.ask(args.question)
            threshold = service.threshold
    except KnowledgeAssistantError as error:
        code, kind = _classify(error)
        message = redact_key(str(error))
        saved = _save_error_body(error) if isinstance(error, LLMError) else None
        if args.json:
            print(json.dumps({"error": {"kind": kind, "message": message}}, ensure_ascii=False), file=out)
        else:
            print(f"ERROR ({kind}): {message}" + (f" [provider error body saved: {saved}]" if saved else ""), file=err)
        return code
    if args.json:
        print(json.dumps(result_to_dict(result, args.arm, threshold), ensure_ascii=False, indent=2), file=out)
    else:
        print(render_text(result, args.arm, threshold), end="", file=out)
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Vietnamese answers on a Windows console
    load_dotenv(PROJECT_ROOT / ".env")
    sys.exit(main())

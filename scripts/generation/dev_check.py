"""RAG-002 live checks on the DEV set only (never the eval set). Every step prints its quota cost first.

    python scripts/generation/dev_check.py duplicates                     # offline: passages in > 1 chunk
    python scripts/generation/dev_check.py retrieval [--live]             # dev queries → top-1 table (embeddings only)
    python scripts/generation/dev_check.py render --case Q-DEV-001        # the exact prompt, no LLM call
    python scripts/generation/dev_check.py answer --case Q-DEV-001 --live # one LLM call, end to end

Without --live a step that would spend quota stops after printing its estimate. Query embeddings are cached
(`EMBEDDING_CACHE_PATH`), so a repeat costs nothing. Retries are off (1 attempt): an HTTP 429 stops the run, and its
body is saved with the key redacted (RAG-002 addendum 5). Markdown output is appended to --out.
"""
import argparse
import json
import sys
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from google.genai import errors  # noqa: E402

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages  # noqa: E402
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder  # noqa: E402
from knowledge_assistant.application.common.language import detect_language  # noqa: E402
from knowledge_assistant.application.common.passage import passage_hash  # noqa: E402
from knowledge_assistant.application.ingestion.build_chunks import load_chunks  # noqa: E402
from knowledge_assistant.application.ingestion.index_corpus import chunker_config_of  # noqa: E402
from knowledge_assistant.application.retrieval.retrieve import Retriever  # noqa: E402
from knowledge_assistant.config import (  # noqa: E402
    get_answer_settings,
    get_chroma_path,
    get_chunks_dir,
    get_embedding_settings,
    get_logs_dir,
    get_retrieval_settings,
)
from knowledge_assistant.core.exceptions import EmbeddingError, GenerationError  # noqa: E402
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import (  # noqa: E402
    GeminiEmbedder,
    _raw_body,
    redact_key,
)
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: E402
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore  # noqa: E402

DEV_FILE = PROJECT_ROOT / "data" / "evaluation" / "questions" / "dev-v1.jsonl"  # the only question file read here
ARMS = ("A", "B")


def dev_cases() -> list[dict]:
    cases = [json.loads(line) for line in DEV_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    for case in cases:  # eval-set firewall (addendum 6)
        if case["split"] != "dev" or not case["id"].startswith("Q-DEV-"):
            raise SystemExit(f"refusing non-dev case {case['id']}")
    return cases


def emit(text: str, out: Path | None) -> None:
    print(text)
    if out:
        with out.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")


def save_error(kind: str, body: str) -> Path:
    path = get_logs_dir() / f"rag-002-{kind}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_key(body), encoding="utf-8")
    return path


def open_cache() -> CachingEmbedder:
    settings = replace(get_embedding_settings(), max_attempts=1)  # no retry loop on a 429 (addendum 5)
    return CachingEmbedder(GeminiEmbedder(settings), settings.cache_path)


def open_store(arm: str) -> ChromaVectorStore:
    config = chunker_config_of(load_chunks(get_chunks_dir() / f"arm-{arm.lower()}.jsonl"))
    store = ChromaVectorStore(get_chroma_path(), config, get_embedding_settings().model_id, create=False)
    if not store.exists:
        raise SystemExit(f"collection {store.name} does not exist; run scripts/ingestion/build_index.py --arm {arm}")
    return store


def check_embed_budget(cache: CachingEmbedder, questions: list[str], live: bool, out: Path | None) -> bool:
    missing = cache.missing(questions, EmbeddingTask.QUERY)
    emit(f"- embedding model `{cache.model_id}`; query texts {len(questions)}, not cached {len(missing)} "
         f"→ estimated embed requests: {len(missing)} (1 request per text, V-1)", out)
    if missing and not live:
        print("not cached: re-run with --live to spend these requests")
        return False
    return True


def cmd_duplicates(args) -> int:
    """Chunks that share a passage (the dedup key) vs chunks that share a content_hash, per arm."""
    for arm in ARMS:
        chunks = load_chunks(get_chunks_dir() / f"arm-{arm.lower()}.jsonl")
        by_passage: dict[str, list] = defaultdict(list)
        by_content: dict[str, list] = defaultdict(list)
        for chunk in chunks:
            by_passage[passage_hash(chunk)].append(chunk)
            by_content[chunk.content_hash].append(chunk)
        groups = [sorted(g, key=lambda c: c.chunk_id) for g in by_passage.values() if len(g) > 1]
        content_extra = sum(len(g) - 1 for g in by_content.values() if len(g) > 1)
        emit(f"\n### Arm {arm}: {len(groups)} passages occur in more than one chunk, "
             f"{sum(len(g) - 1 for g in groups)} extra copies (by content_hash: {content_extra} extra copies)", args.out)
        if groups:
            emit("\n| chunk ids sharing one passage (lowest id first = kept on a score tie) | same content_hash? |\n"
                 "|---|---|", args.out)
        for group in sorted(groups, key=lambda g: g[0].chunk_id):
            same = len({c.content_hash for c in group}) == 1
            emit(f"| {', '.join(c.chunk_id for c in group)} | {'yes' if same else 'no (link URLs differ)'} |", args.out)
    return 0


def cmd_retrieval(args) -> int:
    cases = dev_cases()
    top_k = get_retrieval_settings().top_k
    emit(f"\n## Dev retrieval ({datetime.now(timezone.utc).isoformat(timespec='seconds')}), top_k={top_k}, "
         f"over-fetch {get_retrieval_settings().overfetch}", args.out)
    with open_cache() as cache:
        if not check_embed_budget(cache, [c["question"] for c in cases], args.live, args.out):
            return 1
        rows = []
        try:
            for arm in ARMS:
                retriever = Retriever(cache, open_store(arm), top_k, get_retrieval_settings().overfetch)
                for case in cases:
                    result = retriever.retrieve(case["question"])
                    rows.append((arm, case, result))
        except EmbeddingError as error:
            path = save_error("embed-error", f"{error}\n{error.__cause__!r}")
            emit(f"STOPPED on an embedding error: {error} (saved {path.name})", args.out)
            return 2
        emit(f"- actual embed API requests this run: {cache.stats().get('api_requests', 0)}; "
             f"cache hits {cache.hits}", args.out)

    emit("\n| arm | case | lang | answerable | top-1 | top-5 scores | duplicates_dropped | top-5 chunk ids "
         "(+ duplicate_chunk_ids) |\n|---|---|---|---|---:|---|---:|---|", args.out)
    for arm, case, result in rows:
        scores = ", ".join(f"{hit.score:.4f}" for hit in result.chunks)
        ids = ", ".join(hit.chunk.chunk_id + (f" (+{'/'.join(hit.duplicate_chunk_ids)})" if hit.duplicate_chunk_ids
                                              else "") for hit in result.chunks)
        emit(f"| {arm} | {case['id']} | {case['language']} | {case['answerable']} | {result.chunks[0].score:.4f} | "
             f"{scores} | {result.duplicates_dropped} | {ids} |", args.out)

    arm_a = [(case, result.chunks[0].score) for arm, case, result in rows if arm == "A"]
    answerable = [score for case, score in arm_a if case["answerable"]]
    unanswerable = [score for case, score in arm_a if not case["answerable"]]
    lowest = min(answerable)
    threshold = round(lowest - 0.05, 4)
    overlap = max(unanswerable) >= lowest if unanswerable else False
    emit(f"\n- Arm A answerable top-1: min {lowest:.4f}; unanswerable top-1: {', '.join(f'{s:.4f}' for s in unanswerable)}",
         args.out)
    emit(f"- rule: threshold = min answerable top-1 − 0.05 = {threshold:.4f}; "
         f"unanswerable scores {'reach' if overlap else 'stay below'} the lowest answerable score", args.out)
    gated = [case["id"] for case, score in arm_a if score < threshold]
    emit(f"- dev cases the gate would refuse at {threshold:.4f} (Arm A): {gated or 'none'}", args.out)
    for language in ("en", "vi"):
        values = [f"{score:.4f}" for case, score in arm_a if case["language"] == language and case["answerable"]]
        emit(f"- Arm A answerable top-1, {language}: {', '.join(values)}", args.out)
    return 0


def _build_service(arm: str, cache: CachingEmbedder, llm, threshold: float) -> AnswerQuestion:
    answer = get_answer_settings()
    retrieval = get_retrieval_settings()
    return AnswerQuestion(
        Retriever(cache, open_store(arm), retrieval.top_k, retrieval.overfetch),
        llm,
        PromptBuilder.from_dir(answer.prompts_dir, answer.prompt_version),
        load_messages(answer.messages_path),
        threshold,
    )


def _case(case_id: str) -> dict:
    matches = [case for case in dev_cases() if case["id"] == case_id]
    if not matches:
        raise SystemExit(f"{case_id} is not a dev case")
    return matches[0]


def cmd_render(args) -> int:
    case = _case(args.case)
    answer = get_answer_settings()
    with open_cache() as cache:
        if not check_embed_budget(cache, [case["question"]], False, None):
            return 1
        result = Retriever(cache, open_store(args.arm), get_retrieval_settings().top_k,
                           get_retrieval_settings().overfetch).retrieve(case["question"])
    builder = PromptBuilder.from_dir(answer.prompts_dir, answer.prompt_version)
    prompt = builder.build(case["question"], detect_language(case["question"]), result.chunks)
    emit(f"\n## Rendered prompt `{builder.version}`: {case['id']}, Arm {args.arm} (no LLM call)\n\n````text\n"
         f"{prompt}````", args.out)
    return 0


def cmd_answer(args) -> int:
    case = _case(args.case)
    settings = get_answer_settings()
    threshold = get_retrieval_settings().insufficient_score_threshold
    emit(f"\n## End to end: {case['id']} ({case['language']}, answerable={case['answerable']}), Arm {args.arm}, "
         f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}", args.out)
    emit(f"- ANSWER_MODEL = `{settings.model}`; prompt `{settings.prompt_version}`; threshold {threshold}; "
         f"estimated LLM requests: 1 (0 if the gate fires)", args.out)
    llm = GeminiLLM(settings)
    with open_cache() as cache:
        if not check_embed_budget(cache, [case["question"]], False, args.out):
            return 1
        if not args.live:
            print("dry run: re-run with --live to spend 1 LLM request")
            return 1
        service = _build_service(args.arm, cache, llm, threshold)
        try:
            result = service.ask(case["question"])
        except errors.APIError as error:
            path = save_error(f"llm-http-{error.code}", _raw_body(error))
            emit(f"- STOPPED: HTTP {error.code} {error.status}; redacted body saved to data/logs/{path.name}; "
                 f"LLM requests made: {llm.requests}", args.out)
            return 2
        except GenerationError as error:
            path = save_error("generation-error", f"{error}\nRAW:\n{error.raw_text}")
            emit(f"- GenerationError: {error} (raw saved to data/logs/{path.name}); finish_reason "
                 f"{llm.last_finish_reason}; usage {llm.last_usage}; LLM requests made: {llm.requests}", args.out)
            return 3
    emit(f"- LLM requests made: {llm.requests}; finish_reason {llm.last_finish_reason}; usage {llm.last_usage}", args.out)
    emit(f"- insufficient={result.insufficient} reason={result.insufficient_reason}; "
         f"dropped_markers={list(result.dropped_markers)}; uncited_sentences={result.uncited_sentences}; "
         f"duplicates_dropped={result.duplicates_dropped}; top-1 {result.retrieved[0].score:.4f}", args.out)
    emit("- latency ms: " + ", ".join(f"{k} {v:.0f}" for k, v in result.latency_ms.items()), args.out)
    if result.llm:
        emit(f"\nRaw JSON from the model:\n\n```json\n{result.llm.text}\n```", args.out)
    emit(f"\nAnswer shown to the user:\n\n> {result.answer}", args.out)
    if result.missing_information:
        emit(f"\nmissing_information: {result.missing_information}", args.out)
    emit("\n| marker | chunk_id | location | excerpt (first 80 chars) |\n|---:|---|---|---|", args.out)
    for citation in result.citations:
        emit(f"| {citation.marker} | {citation.chunk_id} | {citation.location} | "
             f"{citation.excerpt[:80].replace(chr(10), ' ')} |", args.out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, help="append Markdown output to this file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("duplicates")
    retrieval = sub.add_parser("retrieval")
    retrieval.add_argument("--live", action="store_true")
    for name in ("render", "answer"):
        command = sub.add_parser(name)
        command.add_argument("--case", required=True)
        command.add_argument("--arm", choices=ARMS, default="A")
        if name == "answer":
            command.add_argument("--live", action="store_true")
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    handlers = {"duplicates": cmd_duplicates, "retrieval": cmd_retrieval, "render": cmd_render, "answer": cmd_answer}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

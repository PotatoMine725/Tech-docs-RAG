"""Embed one arm's chunks and index them in Chroma, and index their text in the keyword index (RAG-001b, ADR-0005,
ADR-0007).

    python scripts/ingestion/build_index.py --arm A|B [--corpus corpus1|corpus2] [--dry-run]

Reads the corpus's arm-<a|b>.jsonl (corpus 1: data/processed/chunks/). --corpus sets CORPUS for this process: corpus 2
gets its own Chroma directory, keyword-index directory and chunk dir (config.corpus_scoped), never corpus 1's. Chunks already in the arm's collection are skipped and
texts already in the embedding cache cost no quota, so a stopped run is resumed by running it again.
The keyword index (SQLite FTS5, data/keyword/kw_<chunker config>.sqlite) is built first from the same chunks with
the same resume rule (chunk_ids already present are skipped); it costs no quota and needs no model, so a run stopped
by the embedding quota still leaves it complete.
--dry-run makes no API call and writes nothing to Chroma or to the keyword index: it prints what a run would send and,
for Gemini, a simulated duration under the per-minute throttle.
The embedder is the configured provider (EMBEDDING_PROVIDER: gemini | embeddinggemma); each provider/model gets its
own collection, so switching providers never mixes vectors.
A real run appends its IndexReport to validation/retrieval/indexing-log.jsonl.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.build_chunks import load_chunks  # noqa: E402
from knowledge_assistant.application.ingestion.index_corpus import (  # noqa: E402
    IndexCorpus,
    chunker_config_of,
    index_keywords,
)
from knowledge_assistant.composition import create_embedder, embedding_cache_path  # noqa: E402
from knowledge_assistant.config import (  # noqa: E402
    CORPORA,
    get_active_embedding_model_id,
    get_chroma_path,
    get_chunks_dir,
    get_corpus,
    get_embedding_settings,
    get_keyword_index_dir,
    get_logs_dir,
)
from knowledge_assistant.core.exceptions import QuotaExhaustedError  # noqa: E402
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens  # noqa: E402
from knowledge_assistant.infrastructure.keyword_index.fts5_index import Fts5KeywordIndex  # noqa: E402
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore  # noqa: E402

INDEXING_LOG = PROJECT_ROOT / "validation" / "retrieval" / "indexing-log.jsonl"
DAILY_REQUEST_LIMIT = 1000  # free-tier embedding requests per day, one per text (ADR-0005 V-1, D19)


def setup_logging(arm: str) -> Path:
    """Warnings (retry waits, the first 429's raw body with the key redacted) go to stderr and a log file."""
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"build-index-{get_corpus()}-arm-{arm.lower()}.log"
    handlers = [logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)
    for noisy in ("httpx", "chromadb", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_path


def count_lines(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def simulate_minutes(plan: list[list[str]], requests_per_minute: int, tokens_per_minute: int) -> float:
    """When the last planned call would start under the real throttle, on a fake clock (no latency)."""
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    throttle = SlidingWindowThrottle(requests_per_minute, tokens_per_minute, clock=lambda: now[0], sleep=sleep)
    for group in plan:
        throttle.acquire(sum(estimate_tokens(t) for t in group), requests=len(group))
    return now[0] / 60


def dry_run(arm: str, chunks_path: Path) -> int:
    chunks = load_chunks(chunks_path)
    config = chunker_config_of(chunks)
    store = ChromaVectorStore(get_chroma_path(), config, get_active_embedding_model_id(), create=False)
    present = store.get_ids()
    pending = [chunk for chunk in chunks if chunk.chunk_id not in present]
    # Gemini: no client is created and no API call is made. The local embedder DOES load its model (ONNX session and
    # tokenizer) when any text is left to embed: planning tokenizes the texts to sort them by length (ADR-0006). It
    # embeds nothing.
    embedder = create_embedder()
    with CachingEmbedder(embedder, embedding_cache_path()) as cache:
        to_send = cache.missing([chunk.embed_text for chunk in pending], EmbeddingTask.DOCUMENT)
    plan = embedder.plan_calls(to_send)
    tokens = sum(estimate_tokens(text) for text in to_send)
    print(f"DRY RUN {get_corpus()} arm {arm} ({config}), collection {store.name} in {get_chroma_path()} "
          f"({'exists' if store.exists else 'not created yet'})")
    print(f"embedder: {embedder.model_id}")
    keywords = Fts5KeywordIndex(get_keyword_index_dir(), config, create=False)
    keyword_present = keywords.get_ids()
    print(f"keyword index {keywords.path.name} ({'exists' if keywords.exists else 'not created yet'}): "
          f"{sum(chunk.chunk_id in keyword_present for chunk in chunks)} of {len(chunks)} chunks present, "
          f"{sum(chunk.chunk_id not in keyword_present for chunk in chunks)} to add")
    keywords.close()
    print(f"chunks in file: {len(chunks)}; already in store: {len(chunks) - len(pending)}; to index: {len(pending)}")
    print(f"unique texts to embed (not in cache): {len(to_send)}; est. tokens (chars/4): {tokens}")
    print(f"embedding calls: {len(plan)}; largest call: {max((len(g) for g in plan), default=0)} texts")
    if isinstance(embedder, GeminiEmbedder):
        settings = get_embedding_settings()
        minutes = simulate_minutes(plan, settings.requests_per_minute, settings.tokens_per_minute)
        print(f"quota requests (1 per text): {len(to_send)} of {DAILY_REQUEST_LIMIT}/day")
        print(f"simulated: last call starts at {minutes:.1f} min (throttle {settings.requests_per_minute} req/min, "
              f"{settings.tokens_per_minute} tok/min; call latency not included)")
    return 0


def run(arm: str, chunks_path: Path) -> int:
    log_path = setup_logging(arm)
    chunks = load_chunks(chunks_path)
    keywords = Fts5KeywordIndex(get_keyword_index_dir(), chunker_config_of(chunks))
    try:
        keyword_report = index_keywords(chunks, keywords)
    finally:
        keywords.close()
    print(f"keyword index {keywords.path.name}: {keyword_report.to_dict()}")
    store = ChromaVectorStore(get_chroma_path(), chunker_config_of(chunks), get_active_embedding_model_id())
    embedder = create_embedder()
    with CachingEmbedder(embedder, embedding_cache_path()) as cache:
        try:
            report = IndexCorpus(cache, store, usage=cache.stats).run(chunks_path)
        except QuotaExhaustedError as error:
            print(f"STOPPED: {error}")
            print(f"cache kept every paid vector: {cache.stats()}; store count {store.count()}; run again after the reset")
            return 3
    entry = {
        "corpus": get_corpus(),
        "arm": arm,
        "collection": store.name,
        **report.to_dict(),
        "keyword_index": {"file": keywords.path.name, **keyword_report.to_dict()},
        # provider counters (Gemini: http_calls, retries, throttle_wait_s; local: batches, texts); the report
        # already holds api_requests and estimated_tokens
        **{k: v for k, v in embedder.stats().items() if k not in ("api_requests", "estimated_tokens")},
    }
    if "throttle_wait_s" in entry:
        entry["throttle_wait_s"] = round(entry["throttle_wait_s"], 1)
    INDEXING_LOG.parent.mkdir(parents=True, exist_ok=True)
    with INDEXING_LOG.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    lines = count_lines(chunks_path)
    print(f"store.count() = {store.count()}; lines in {chunks_path.name} = {lines}; "
          f"{'MATCH' if store.count() == lines else 'MISMATCH'}")
    print(f"appended to {INDEXING_LOG.relative_to(PROJECT_ROOT).as_posix()}; log {log_path.name}; "
          f"finished {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    keyword_ok = keyword_report.index_count == lines
    print(f"keyword index count = {keyword_report.index_count}; {'MATCH' if keyword_ok else 'MISMATCH'}")
    return 0 if store.count() == lines and keyword_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", required=True, choices=["A", "B"])
    parser.add_argument("--corpus", choices=CORPORA, help="default: CORPUS from the environment, else corpus1")
    parser.add_argument("--dry-run", action="store_true", help="print the cost estimate only; no API call")
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    if args.corpus:
        os.environ["CORPUS"] = args.corpus
    chunks_path = get_chunks_dir() / f"arm-{args.arm.lower()}.jsonl"
    return dry_run(args.arm, chunks_path) if args.dry_run else run(args.arm, chunks_path)


if __name__ == "__main__":
    sys.exit(main())

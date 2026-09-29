"""Embed one arm's chunks and index them in Chroma (RAG-001b, ADR-0005).

    python scripts/ingestion/build_index.py --arm A|B [--dry-run]

Reads data/processed/chunks/arm-<a|b>.jsonl. Chunks already in the arm's collection are skipped and
texts already in the embedding cache cost no quota, so a stopped run is resumed by running it again.
--dry-run makes no API call and writes nothing to Chroma: it prints what a run would send and a
simulated duration under the per-minute throttle.
A real run appends its IndexReport to validation/retrieval/indexing-log.jsonl.
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.build_chunks import load_chunks  # noqa: E402
from knowledge_assistant.application.ingestion.index_corpus import IndexCorpus, chunker_config_of  # noqa: E402
from knowledge_assistant.config import (  # noqa: E402
    get_chroma_path,
    get_chunks_dir,
    get_embedding_settings,
    get_logs_dir,
)
from knowledge_assistant.core.exceptions import QuotaExhaustedError  # noqa: E402
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens  # noqa: E402
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore  # noqa: E402

INDEXING_LOG = PROJECT_ROOT / "validation" / "retrieval" / "indexing-log.jsonl"
DAILY_REQUEST_LIMIT = 1000  # free-tier embedding requests per day, one per text (ADR-0005 V-1, D19)


def setup_logging(arm: str) -> Path:
    """Warnings (retry waits, the first 429's raw body with the key redacted) go to stderr and a log file."""
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"build-index-arm-{arm.lower()}.log"
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
    settings = get_embedding_settings()
    chunks = load_chunks(chunks_path)
    config = chunker_config_of(chunks)
    store = ChromaVectorStore(get_chroma_path(), config, settings.model_id, create=False)
    present = store.get_ids()
    pending = [chunk for chunk in chunks if chunk.chunk_id not in present]
    gemini = GeminiEmbedder(settings)  # no client is created: planning makes no call
    with CachingEmbedder(gemini, settings.cache_path) as cache:
        to_send = cache.missing([chunk.embed_text for chunk in pending], EmbeddingTask.DOCUMENT)
    plan = gemini.plan_calls(to_send)
    tokens = sum(estimate_tokens(text) for text in to_send)
    minutes = simulate_minutes(plan, settings.requests_per_minute, settings.tokens_per_minute)
    print(f"DRY RUN arm {arm} ({config}), collection {store.name} ({'exists' if store.exists else 'not created yet'})")
    print(f"chunks in file: {len(chunks)}; already in store: {len(chunks) - len(pending)}; to index: {len(pending)}")
    print(f"unique texts to send (not in cache): {len(to_send)}; est. tokens (chars/4): {tokens}")
    print(f"provider calls: {len(plan)}; largest call: {max((len(g) for g in plan), default=0)} texts")
    print(f"quota requests (1 per text): {len(to_send)} of {DAILY_REQUEST_LIMIT}/day")
    print(f"simulated: last call starts at {minutes:.1f} min (throttle {settings.requests_per_minute} req/min, "
          f"{settings.tokens_per_minute} tok/min; call latency not included)")
    return 0


def run(arm: str, chunks_path: Path) -> int:
    settings = get_embedding_settings()
    log_path = setup_logging(arm)
    chunks = load_chunks(chunks_path)
    store = ChromaVectorStore(get_chroma_path(), chunker_config_of(chunks), settings.model_id)
    gemini = GeminiEmbedder(settings)
    with CachingEmbedder(gemini, settings.cache_path) as cache:
        try:
            report = IndexCorpus(cache, store, usage=cache.stats).run(chunks_path)
        except QuotaExhaustedError as error:
            print(f"STOPPED: {error}")
            print(f"cache kept every paid vector: {cache.stats()}; store count {store.count()}; run again after the reset")
            return 3
    entry = {
        "arm": arm,
        "collection": store.name,
        **report.to_dict(),
        "http_calls": gemini.http_calls,
        "retries": gemini.retries,
        "throttle_wait_s": round(gemini.stats()["throttle_wait_s"], 1),
    }
    INDEXING_LOG.parent.mkdir(parents=True, exist_ok=True)
    with INDEXING_LOG.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    lines = count_lines(chunks_path)
    print(f"store.count() = {store.count()}; lines in {chunks_path.name} = {lines}; "
          f"{'MATCH' if store.count() == lines else 'MISMATCH'}")
    print(f"appended to {INDEXING_LOG.relative_to(PROJECT_ROOT).as_posix()}; log {log_path.name}; "
          f"finished {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    return 0 if store.count() == lines else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", required=True, choices=["A", "B"])
    parser.add_argument("--dry-run", action="store_true", help="print the cost estimate only; no API call")
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    chunks_path = get_chunks_dir() / f"arm-{args.arm.lower()}.jsonl"
    return dry_run(args.arm, chunks_path) if args.dry_run else run(args.arm, chunks_path)


if __name__ == "__main__":
    sys.exit(main())

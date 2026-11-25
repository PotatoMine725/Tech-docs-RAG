"""Chunk the normalized corpus with one experiment arm (INGEST-002, ADR-0003 D2-D8).

    python scripts/ingestion/build_chunks.py --arm A|B [--corpus corpus1|corpus2]

Reads the corpus's normalized.jsonl (config.get_normalized_path) and config/chunking.json; writes
arm-<a|b>.jsonl and stats-arm-<a|b>.json to the corpus's chunk dir (corpus 1: data/processed/chunks; corpus 2:
data/processed/chunks-corpus2, git-ignored). Both corpora use the same arm configs (ADR-0003, ADR-0008). Deterministic: no timestamps, fixed order.
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.build_chunks import (  # noqa: E402
    chunk_to_record,
    load_normalized_documents,
)
from knowledge_assistant.application.ingestion.normalize_corpus import write_jsonl  # noqa: E402
from knowledge_assistant.config import CORPORA, get_chunks_dir, get_normalized_path  # noqa: E402
from knowledge_assistant.infrastructure.chunking.factory import load_arm, small_chunk_chars  # noqa: E402
from knowledge_assistant.infrastructure.chunking.stats import chunk_stats  # noqa: E402

CONFIG = PROJECT_ROOT / "config" / "chunking.json"


def build(arm: str, corpus: str = "corpus1") -> tuple[list[dict], dict]:
    chunker = load_arm(CONFIG, arm)
    documents = load_normalized_documents(get_normalized_path(corpus))
    results = [chunker.chunk_with_report(document) for document in documents]
    records = [chunk_to_record(chunk) for result in results for chunk in result.chunks]
    stats = chunk_stats(documents, results, chunker.config.chunker_config, small_chunk_chars(CONFIG))
    return records, {"arm": arm, **stats}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", required=True, choices=["A", "B"])
    parser.add_argument("--corpus", choices=CORPORA, default="corpus1")
    args = parser.parse_args()
    arm = args.arm
    records, stats = build(arm, args.corpus)
    chunks_dir = get_chunks_dir(args.corpus)
    chunks_path = chunks_dir / f"arm-{arm.lower()}.jsonl"
    stats_path = chunks_dir / f"stats-arm-{arm.lower()}.json"
    write_jsonl(records, chunks_path)
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    size = stats["size_chars"]
    print(f"arm {arm} ({stats['chunker_config']}): {stats['chunks_total']} chunks over {stats['documents']} documents")
    print(f"size min/p50/p90/max: {size['min']}/{size['p50']}/{size['p90']}/{size['max']}")
    print(f"chunks cutting a code fence: {stats['chunks_cutting_code_fence']} ({stats['pct_chunks_cutting_code_fence']}%)")
    print(f"duplicates dropped: {stats['duplicates_dropped']}; documents with one chunk: {stats['documents_with_one_chunk']}")
    print(f"wrote {chunks_path.relative_to(PROJECT_ROOT).as_posix()}, {stats_path.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Print the top-k chunks one arm retrieves for a question (RAG-001b sanity check).

    python scripts/utilities/peek_retrieval.py --arm A "How do I register a scoped service?" [--top-k 5] [--out FILE.md]

One live embedding request per new question (RETRIEVAL_QUERY); it is cached, so a repeat costs no quota.
Use a question that is not in the eval or dev set.
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.build_chunks import load_chunks  # noqa: E402
from knowledge_assistant.application.ingestion.index_corpus import chunker_config_of  # noqa: E402
from knowledge_assistant.config import get_chroma_path, get_chunks_dir, get_embedding_settings  # noqa: E402
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask  # noqa: E402
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR  # noqa: E402
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder  # noqa: E402
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", required=True, choices=["A", "B"])
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", type=Path, help="also write the output as Markdown to this file")
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")

    settings = get_embedding_settings()
    config = chunker_config_of(load_chunks(get_chunks_dir() / f"arm-{args.arm.lower()}.jsonl"))
    store = ChromaVectorStore(get_chroma_path(), config, settings.model_id, create=False)
    if not store.exists:
        print(f"collection {store.name} does not exist; run scripts/ingestion/build_index.py --arm {args.arm}")
        return 1
    gemini = GeminiEmbedder(settings)
    with CachingEmbedder(gemini, settings.cache_path) as cache:
        [query] = cache.embed([args.question], EmbeddingTask.QUERY)
        cost = cache.stats()
    hits = store.search(query, args.top_k)

    lines = [
        f"arm {args.arm} ({config}), collection {store.name}, {store.count()} chunks",
        f"question: {args.question}",
        f"query embedding: cache hits {cost['hits']}, API requests {cost.get('api_requests', 0)}",
        "",
        "| rank | score | chunk_id | heading path |",
        "|---:|---:|---|---|",
    ]
    for hit in hits:
        heading = HEADING_PATH_SEPARATOR.join(hit.chunk.heading_path)
        lines.append(f"| {hit.rank} | {hit.score:.4f} | {hit.chunk.chunk_id} | {heading} |")
    output = "\n".join(lines)
    print(output)
    if args.out:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with args.out.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"\n## Arm {args.arm} ({stamp})\n\n```\n$ python scripts/utilities/peek_retrieval.py "
                         f"--arm {args.arm} \"{args.question}\"\n```\n\n{output}\n")
        print(f"appended to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

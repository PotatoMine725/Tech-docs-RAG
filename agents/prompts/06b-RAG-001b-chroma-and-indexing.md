# RAG-001b — ChromaDB vector store + index both arms

Read `agents/prompts/_common.md` first and follow it.
Read: ADR-0003 D6/D7, ADR-0005, RAG-001a execution report, `core/interfaces/vector_store.py`.
Entry: RAG-001a done (ADR-0005 accepted, cache works).

## Interface change (core — impact-check first)
```python
# core/models: new
@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    rank: int          # 1-based
    score: float       # similarity, higher = more similar (convert Chroma distance: cosine sim = 1 - distance)

# core/interfaces/vector_store.py
class VectorStore(Protocol):
    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None: ...
    def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]: ...
    def count(self) -> int: ...
    def get_ids(self) -> set[str]: ...
```

## Do
1. `infrastructure/vector_store/chromadb/chroma_store.py` (`ChromaVectorStore`):
   - `PersistentClient(path=config chroma path)`; one collection per arm, name = `kb_{chunker_config}_{embedding model_id sanitized}` (so changing the embedding settings can never silently reuse an old collection);
   - collection metadata: `hnsw:space` from ADR-0005, plus `chunker_config`, `embedding_model_id`, `created_at`;
   - documents = `embed_text`; metadata = all D6 fields except `embed_text` (Chroma metadata must be str/int/float/bool — no None, no lists; convert and convert back);
   - `search` rebuilds full `DocumentChunk` objects from metadata, returns `RetrievedChunk` sorted by rank.
2. Application `IndexCorpus` use case (depends on `Chunker`-produced chunk file reader, `Embedder`, `VectorStore` interfaces only):
   - reads `data/processed/chunks/arm-{a|b}.jsonl`;
   - skips chunk_ids already in the store (resume) — combined with the embedding cache, a re-run costs 0 quota;
   - embeds `embed_text` with `EmbeddingTask.DOCUMENT`, upserts in batches;
   - returns an `IndexReport` (chunks total, already present, newly embedded, cache hits, API requests, est. tokens, duration s).
3. Script `scripts/ingestion/build_index.py --arm A|B [--dry-run]`: `--dry-run` prints the cost estimate only (no API). Appends the `IndexReport` as JSON to `validation/retrieval/indexing-log.jsonl`.
4. Tests (offline, `FakeEmbedder` + Chroma in a `tmp_path`):
   - round-trip: upsert 5 chunks → search with one chunk's own vector → rank 1 is that chunk, all D6 fields equal the original;
   - resume: index 5, then index the same 5 + 3 new → only 3 embedded;
   - collection naming differs when chunker_config or embedding model_id differs;
   - score conversion: identical vector → score ≈ 1.0.
5. **Run it (live):** `--dry-run` for both arms → confirm the plan against the quota-day decision in ADR-0005 → index Arm A → index Arm B (after 14:00 UTC+7 if ADR-0005 says two quota days).
6. Sanity check (live, 1 query): `scripts/utilities/peek_retrieval.py --arm A "How do I register a scoped service?"` prints top-5 (rank, score, chunk_id, heading path). Use a question that is NOT in the eval or dev set. Save the output to `validation/retrieval/sanity-<date>.md`.

## Acceptance (gate part of G3)
- For both arms: `store.count()` == number of lines in the chunk file (script prints both numbers; paste real output into the execution report).
- Re-running `build_index.py` for an arm reports 0 newly embedded, 0 API requests.
- Offline pytest green; key never printed (`git grep` for the key prefix in repo and logs = 0).

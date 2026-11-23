# Retrieval architecture

- **Dense:** ChromaDB behind `core.interfaces.vector_store` (one collection per arm and embedding model, ADR-0005/0006).
- **Sparse:** SQLite FTS5 (BM25) behind `core.interfaces.keyword_index`, one file per arm keyed by chunker config,
  built by `scripts/ingestion/build_index.py` (ADR-0007). Tokenizer `unicode61 remove_diacritics 0`, PROVISIONAL; the
  Vietnamese target design (plan §2) is TBD.
- **Modes:** `RETRIEVAL_MODE` = `dense` (default) | `sparse` | `hybrid`. Hybrid = Reciprocal Rank Fusion (k = 60)
  over dense and BM25 top `top_k + overfetch`, then passage dedup to top_k. `application/retrieval/retrieve.py`;
  wired by `composition.create_retriever`.
- **Gate:** dense top-1 score in every mode (ADR-0007 D6); hybrid/sparse gate TBD until the reranker.
- **Reranking:** `core.interfaces.reranker`, `RERANK_PROVIDER=none` only; a real reranker is plan step 4b.

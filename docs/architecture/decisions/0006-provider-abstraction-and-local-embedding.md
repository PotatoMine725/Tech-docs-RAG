# ADR-0006 Provider abstraction: separate embedding, generation and rerank providers; local EmbeddingGemma

Date: 2026-11-23
Status: Accepted (owner: separate interfaces for embed / generate / rerank, 2026-11-23; EmbeddingGemma v1 with FP32
default and INT4 low-RAM option, embedder budget <= 1 GB, from the embedding benchmark 2026-11-21).
Refines: ADR-0004 D10 (embedding model), ADR-0005 (cache key, collection key). Plan step 2 of
`docs/plans/local-rag-upgrade-plan.md`.

## Decision
- **Three separate contracts in `core/interfaces/`**: `Embedder` (embedding.py), `LLM` (llm.py), `Reranker`
  (reranker.py, new). Each is picked by its own setting, so e.g. local embedding + Gemini answers is valid.
- **Selection by configuration**: `EMBEDDING_PROVIDER` = `gemini` (default) | `embeddinggemma`;
  `LLM_PROVIDER` = `gemini` (default) | `llamacpp` (reserved: raises `ConfigurationError` until built);
  `RERANK_PROVIDER` = `none` (only value; `NoOpReranker` keeps the retriever's order). Unknown values fail loudly.
- **Factories live in the composition root** (`composition.py`: `create_embedder`, `create_llm`, `create_reranker`,
  `open_embedder`). The GUI wiring and `scripts/ask.py`, `build_index.py`, `run_eval.py` (embedder) use them and name
  no concrete provider. The evaluation runner and judge keep `GeminiLLM` directly (Gemini-specific throttles and
  request counters; ADR-0004 D12 fixes the judge model).
- **Local embedder** `infrastructure/embeddings/embeddinggemma_embedder.py`: ONNX Runtime, CPU only, same prompts as
  the benchmark, Matryoshka dims 768/512/256/128, lazy model load. `onnxruntime`, `tokenizers`, `numpy` are an
  optional extra (`pip install -e .[local]`); the Gemini-only setup does not need them. The app never downloads a
  model: `LOCAL_EMBEDDING_MODEL_DIR` points to an existing onnx-community export.
- **Keys**: model id `embeddinggemma-300m[-<revision>]-<variant>-t<max_tokens>@<dim>` (revision: first 8 hex of the
  export's `REVISION` file) names both cache entries and the Chroma collection, so
  vectors of different providers, variants or sizes never mix; switching provider needs a rebuilt index.

## Consequences
- The retrieval gate threshold is per embedding provider (`config.GATE_THRESHOLDS`; `INSUFFICIENT_SCORE_THRESHOLD`
  overrides): gemini 0.686, embeddinggemma 0.5417. The local value was tuned in the reindex step (2026-11-23) with
  the retrieval-spec rule (dev, Arm A, lowest answerable top-1 - 0.05), for FP32 @768 only; other variants / dims are
  TBD. The answerable / unanswerable gap on dev is 0.0048 (Gemini 0.06): see retrieval-spec.md.
- The local embedder plans token-length-sorted batches (less padding; arm A 4.86 -> 7.82 texts/s back to back on the owner's
  machine, docs/reports/2026-11-23-local-reindex.md). The embedding cache therefore accepts plan groups in any order
  (each text in exactly one group, one call per group, committed before the next; results in input order).
- The desktop app creates the embedding provider once (the local model loads once per run) and serializes query
  embedding with a lock.
- Reranking is not wired into retrieval yet; the hybrid-search step adds a real reranker behind `Reranker`.
  Done in ADR-0009 (2026-11-26): `RERANK_PROVIDER=cross-encoder`, opt-in, default `none`.

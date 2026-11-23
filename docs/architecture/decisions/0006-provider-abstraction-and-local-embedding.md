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
- **Keys**: model id `embeddinggemma-300m-<variant>@<dim>` names both cache entries and the Chroma collection, so
  vectors of different providers, variants or sizes never mix; switching provider needs a rebuilt index.

## Consequences
- `INSUFFICIENT_SCORE_THRESHOLD` (0.686) is calibrated for Gemini; it must be re-tuned on the dev set before the
  local embedder is used for answers. TBD in the reindex step.
- The desktop app creates the embedding provider once (the local model loads once per run) and serializes query
  embedding with a lock.
- Reranking is not wired into retrieval yet; the hybrid-search step adds a real reranker behind `Reranker`.

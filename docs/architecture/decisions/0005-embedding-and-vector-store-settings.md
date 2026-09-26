# ADR-0005 Embedding and vector-store settings (dimension, batching, cache, Chroma path, distance)

Date: 2026-09-26
Status: Accepted (owner decisions D14, D16, D17 via AskUserQuestion, 2026-09-26; D15 and D19 follow from the V-1 measurement below).
Task: RAG-001a. Refines: ADR-0004 D10 (embedding model), D13 (retries). Closes: OD-7, OD-8 (master-plan §8), fact V-1.
Does not close: OD-11 (max retry attempts before the *answer-model* fallback; that belongs to RAG-003).

## Context
ADR-0004 D10 fixed the embedding model (`gemini-embedding-001`, task types `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`). Before any index is built, four settings had to be fixed for both experiment arms (ADR-0003 D7 holds everything but chunking constant). We also had to check the free-tier quota behaviour of a batched request (V-1).

## V-1 measurement: how a batched request counts (2026-09-26)
Method: `scripts/utilities/probe_embedding_quota.py` sent **one HTTP request with 3 texts** (Arm A chunks `01:header-1600:0000` prose 1,487 chars, `01:header-1600:0011` code 1,116 chars, `08:header-1600:0000` short 107 chars) at **2026-09-26 00:44:38 UTC** (07:44 UTC+7; 17:44 on 25 Sep in the dashboard's UTC-8 days), `output_dimensionality=768`. The owner read Google AI Studio → Usage, model "Gemini Embedding 1", before and after the call. No other call used this project's key in between (owner statement: the key is used only by this project).

| AI Studio chart (latest point) | Before (07:44) | After (07:52) |
|---|---|---|
| Peak requests per minute (RPM) | 0 | **3** |
| Peak input tokens per minute (TPM) | 0 | **≈ 585** (read from the chart; not an exact tooltip value) |
| Peak requests per day (RPD) | 0 | shows a **3** peak (the RPD chart's day bins appear shifted by one day relative to RPM; the value agrees) |

**Result: 1 batched request = N requests.** Each text in a batch counts as one request against both the per-minute (100) and the per-day (1,000) limits. Batching saves HTTP overhead, not quota.

Other probe observations (saved in `data/cache/probe-v1.json`, git-ignored):
- All three vectors had 768 values and L2 norm ≈ 0.58: 768-d vectors are **not** normalized by the API, confirming D14's normalization step.
- The Gemini API returned no `metadata` and no per-embedding `statistics` (no token counts), so tokens are estimated.
- Token estimate check: chars / 4 (ceil) = 678 for the three texts vs ≈ 585 on the chart. The estimate is about 15% high on this sample, the safe direction for throttling. Kept as the estimator (`CHARS_PER_TOKEN = 4`). It is a 3-text sample, so code-heavy chunks could differ.

Evidence limits: chart readings from owner screenshots, one probe. Consistent across two charts (RPM, RPD), so recorded as verified; re-check if a quota error contradicts it.

## Decisions
**D14 Output dimensionality: 768 (owner).** Both arms, one constant (`EMBEDDING_DIM`, default in `config.py`).
- A store 4× smaller than 3,072 and faster search.
- Every vector is L2-normalized in `GeminiEmbedder` because only 3,072-d output comes back normalized (confirmed by V-1: norm ≈ 0.58).
- The embedder rejects any vector whose length is not the configured dimension (`EmbeddingError`).
- Cache and collection key: `model_id = "<model>@<dim>"`, built from config, so a dimension change can never reuse old vectors.

**D15 Batch size: 45 texts per call; throttle counts texts (from V-1).**
- Limits are set a little under the free-tier values: 90 requests/min (limit 100), 25,000 estimated tokens/min (limit 30,000).
- Because every text counts as a request (V-1), the throttle charges `len(batch)` requests per call. A single call can never exceed the per-minute limits: batches are capped at `min(batch_size, requests_per_minute)` texts and at one minute of estimated tokens.
- 45 = two calls per 90-request window, so the window is used fully. The worst case, 45 × 435 est. tokens (largest chunk) = 19.6K, is under 25K.
- Retries: exponential backoff 1-2-4-8 s + jitter (0-1 s), with any server `Retry-After` / `RetryInfo.retryDelay` honoured when longer. Retried: HTTP 429/500/503/504 and timeouts (explicit 60 s client timeout; the SDK default is none). The embedder's max attempts is **5** (config `EMBEDDING_MAX_ATTEMPTS`), then `EmbeddingError`. The SDK's own retry is off (its default), so retries are not doubled.

**D16 OD-7 Chroma path: `data/chroma/` (owner).** Repo-local, git-ignored (already in `.gitignore`), and not committed. It is rebuilt by a script from the chunk files plus the embedding cache, so rebuilding costs no quota. `CHROMA_PATH` default in `config.py` and `.env.example` changed from `D:\ChromaDB`.

**D17 OD-8 Distance: cosine (owner).** Same for both arms. On unit vectors cosine, inner product and L2 rank identically. Cosine stays correct even if a vector were ever left unnormalized, and its scores are the easiest to read.

**D18 Embedding cache in SQLite (stdlib `sqlite3`).** `CachingEmbedder` wraps any `Embedder`.
- The key is `sha256(model_id | task | text)`, stored in `data/cache/embeddings.sqlite` (git-ignored).
- Columns: key, model_id, task, dim, vector (float32 little-endian bytes), created_at.
- CLAUDE.md rule 2 allows SQLite only for a concrete need. The need:
  - **Atomic writes:** every batch of paid vectors is committed in one transaction right after it returns. A crash or quota stop never leaves a half-written record and never loses paid vectors.
  - **Resume:** a re-run looks up all keys and sends only misses, so indexing can stop at 14:00 and continue on the next quota day.
- Alternatives rejected:
  - JSONL append: a torn last line on crash, and every run must load and dedupe the whole file.
  - `.npy` files: no dependency today, and no atomic append.
  - Chroma as the cache: couples paid vectors to a collection that we delete and rebuild per arm.
- Duplicate texts inside one call are sent once (Arm A has 733 chunks but 709 unique `embed_text`s).
- A miss returns the same float32-rounded values a later hit would, so results do not depend on cache state.

**D19 Indexing needs two quota days (from V-1).**

| | Arm A | Arm B |
|---|---|---|
| Chunks / unique embed texts | 733 / 709 | 859 / 859 |
| Texts shared with the other arm | 0 | 0 |
| Estimated tokens (chars/4, unique texts) | 174,842 | 307,285 |
| Minutes at 90 req/min | 7.9 | 9.5 |
| Minutes at 25K tokens/min | 7.0 | 12.3 |
| Expected wall time (binding limit) | ≈ 8 min | ≈ 12–13 min |

- Both arms need 1,568 requests, more than 1,000 per day. So: **Arm A in one quota day, Arm B in the next** (the daily reset is 14:00 UTC+7).
- Already spent in the quota day that ends Sat 26 Sep 14:00: 6 requests (probe 3 + live test 3).
- Plan for RAG-001b:
  - Arm A (709) before 14:00 on Sat 26 Sep, if 06a is verified in time. That day then totals about 715 of 1,000.
  - Arm B (859) after 14:00. That leaves about 141 for the 42 question embeddings (36 eval + 6 dev; one embedding per question serves both arms) and light dev testing.
  - If Arm A slips past 14:00, the same split moves by one quota day.
- Arm A is smaller than ADR-0004's 200–300K token guess (≈ 175K, measured by character count). Arm B is ≈ 307K.

## Consequences
- The core `Embedder` protocol gains `model_id` and a provider-free `EmbeddingTask` (DOCUMENT / QUERY). Gemini task-type strings live only in `infrastructure/embeddings/gemini_embedder.py`. The new `EmbeddingError` is a core exception.
- Model name, dimension, limits, batch size, attempts, timeout and cache path live in `config.py` (env-overridable). `git grep gemini-embedding-001 -- src/` hits only `config.py`.
- RAG-001b uses `CachingEmbedder(GeminiEmbedder(...))` for indexing and `metadata={"hnsw:space": "cosine"}` (or the equivalent in the installed Chroma version) for both collections. Collections should carry `model_id` in their name or metadata.
- Changing the dimension, model or task type invalidates the cache key by construction; nothing is silently reused.

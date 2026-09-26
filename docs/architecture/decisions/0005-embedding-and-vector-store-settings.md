# ADR-0005 Embedding and vector-store settings (dimension, batching, cache, Chroma path, distance)

Date: 2026-09-26
Status: Accepted (owner decisions D14, D16, D17 via AskUserQuestion; D15 batch size 45 confirmed by the owner; D19 quota plan set by the owner from V-1; all 2026-09-26). Amended 2026-09-26 after 99-VERIFY ([RAG-001a-verify](../../reviews/code/RAG-001a-verify.md)): see the amendment note at the end. Amended again 2026-09-26 by RAG-001b Step 0 (RAG-001a re-verify open items): see amendment 2.
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

Evidence limits:
- Chart readings come from owner screenshots of one probe; no exact tooltip values were recorded.
- The per-minute count (RPM 0 → 3) is clear.
- The RPD chart shows a 3, but its day bins looked shifted relative to RPM, so the per-day count rests on that chart plus the same unit.
- The owner accepted "every text counts 1 request" for both limits (2026-09-26). The plan (D19) is the conservative one: if the daily limit counted calls instead, the only cost is that Arm B could have run a day earlier. The cache makes a quota stop cheap either way.
- Re-check if a quota error contradicts this.

## Decisions
**D14 Output dimensionality: 768 (owner).** Both arms, one constant (`EMBEDDING_DIM`, default in `config.py`).
- A store 4× smaller than 3,072 and faster search.
- Every vector is L2-normalized in `GeminiEmbedder` because only 3,072-d output comes back normalized (confirmed by V-1: norm ≈ 0.58).
- The embedder rejects any vector whose length is not the configured dimension (`EmbeddingError`).
- Cache and collection key: `model_id = "<model>@<dim>"`, built from config, so a dimension change can never reuse old vectors.

**D15 Batch size: up to 45 texts per call, and at most half the per-minute token budget per call; the throttle counts texts (owner confirmed 45; the rest follows from V-1).**
- Limits are set a little under the free-tier values: 90 requests/min (limit 100) and 25,000 estimated tokens/min (limit 30,000).
- Because every text counts as a request (V-1), the throttle charges `len(batch)` requests per call. Over a **sliding 60 s window** it admits a call only if the requests *and* estimated tokens already sent in the last 60 s, plus this call, stay within both limits. Otherwise it sleeps until enough old calls leave the window. It raises if one call alone could never fit.
- 45 texts = two calls per 90-request window. A batch is also cut at **12,500 estimated tokens** (half of 25K), so two calls always fit one token window.
  - Without that cut, two worst-case calls (45 × 435 = 19.6K each, ~39K together) exceed 25K. The throttle would still hold the budget by delaying the second call a full minute, but only one call per minute would get through.
  - Tests: `test_throttle_holds_two_worst_case_calls_to_the_token_budget_over_60s` (the second worst-case call waits 59 s) and `test_production_settings_keep_every_60s_window_under_the_token_budget`, which runs the real defaults on worst-case chunks and checks every 60 s window is ≤ 25K.
- **Expected throughput.** Offline simulation of the pipeline RAG-001b indexes with, `CachingEmbedder(GeminiEmbedder)`: all chunk `embed_text`s of each arm (733 / 859; the cache removes duplicates), a fake client, one fake clock for the throttle and every sleep, a fresh SQLite file per arm. Call latency is not included.

| | Arm A | Arm B |
|---|---|---|
| Avg est. tokens per text | 247 | 358 |
| HTTP calls = cache groups / avg texts per call | 16 / 44.3 | 25 / 34.4 |
| Largest call (est. tokens) | 12,487 | 12,499 |
| Busiest 60 s window (est. tokens / requests) | 24,648 / 90 | 24,755 / 79 |
| Binding limit | requests (90/min) | tokens (25K/min ≈ 70 texts/min) |
| Last call starts at | 7.0 min | 12.0 min |
| Before the verify fix (cache sliced 45 texts, embedder re-split them) | 20 calls, 7.0 min | 39 calls, 18.0 min |

  - Throughput is request-bound for Arm A (≈ 90 texts/min; tokens alone would allow ≈ 101) and token-bound for Arm B (≈ 70 texts/min).
  - Across both arms the average is 307 tokens per text, so a token-bound average of ≈ 81 texts/min.
  - chars/4 overestimates real tokens by about 15% (V-1), so the real token use is a little below the budget.
- Retries: exponential backoff 1-2-4-8 s + jitter (0-1 s), with any server `Retry-After` / `RetryInfo.retryDelay` honoured when longer, **but never more than 120 s per wait**. Every wait is logged (`WARNING`: texts in the call, HTTP code and status, attempt, seconds; never the error body or the key; one exception since amendment 2: the raw body of the first 429 of a run, key redacted). Retried: HTTP 429/500/503/504 and timeouts (explicit 60 s client timeout; the SDK default is none). The embedder's max attempts is **5** (config `EMBEDDING_MAX_ATTEMPTS`), then `EmbeddingError`. The SDK's own retry is off (its default), so retries are not doubled.
- **Daily quota:** a 429 whose `google.rpc.QuotaFailure` names a per-day quota (`quotaId` / `quotaMetric` matching "PerDay" / "per_day" / "daily") raises `QuotaExhaustedError` (a core subclass of `EmbeddingError`) at once, with no retry and no wait. The message says to resume after the 14:00 UTC+7 reset. Per-minute 429s (their QuotaFailure names a "PerMinute" quota) and 429s with no QuotaFailure take the retry path above. The classifier follows the documented error shape; no real daily 429 has been seen yet.

**D16 OD-7 Chroma path: `data/chroma/` (owner).** Repo-local, git-ignored (already in `.gitignore`), and not committed. It is rebuilt by a script from the chunk files plus the embedding cache, so rebuilding costs no quota. `CHROMA_PATH` default in `config.py` and `.env.example` changed from `D:\ChromaDB`.
- Every data path (`CHROMA_PATH`, `EMBEDDING_CACHE_PATH`, `CHUNKS_DIR`, `LOGS_DIR`) is resolved from the repo root, never from the working directory: a relative value, default or env, is joined to the root; an absolute value is kept. A script started in another directory therefore reads and writes the same files and never starts an empty cache.
- `.gitignore` uses `**/data/chroma/*`, `**/data/cache/` and `**/data/logs/`, so a `data/` folder created anywhere in the tree is still ignored; only the root `data/chroma/.gitkeep` is tracked.

**D17 OD-8 Distance: cosine (owner).** Same for both arms. On unit vectors cosine, inner product and L2 rank identically. Cosine stays correct even if a vector were ever left unnormalized, and its scores are the easiest to read.

**D18 Embedding cache in SQLite (stdlib `sqlite3`).** `CachingEmbedder` wraps any `Embedder`.
- **One commit per provider call.** The embedder alone owns the split rule. `plan_calls(texts)` (on the infrastructure `PlannedEmbedder` protocol since amendment 2) returns the groups `embed` would send, and `embed(group)` on one group makes exactly one provider call. The cache sends misses group by group from that plan and commits each group before sending the next. So the vectors of every successful call are stored before the next call is made, and a later failure or quota stop loses no paid vector. The cache never re-slices, so the embedder's half-budget token cap (D15) reaches the real pipeline.
- The key is `sha256(model_id | task | text)`, stored in `data/cache/embeddings.sqlite` (git-ignored).
- Columns: key, model_id, task, dim, vector (float32 little-endian bytes), created_at.
- CLAUDE.md rule 2 allows SQLite only for a concrete need. The need:
  - **Atomic writes:** every provider call's paid vectors are committed in one transaction right after the call returns. A crash or quota stop never leaves a half-written record and never loses paid vectors.
  - **Resume:** a re-run looks up all keys and sends only misses, so indexing can stop at 14:00 and continue on the next quota day.
- Alternatives rejected:
  - JSONL append: a torn last line on crash, and every run must load and dedupe the whole file.
  - `.npy` files: no dependency today, and no atomic append.
  - Chroma as the cache: couples paid vectors to a collection that we delete and rebuild per arm.
- Duplicate texts inside one call are sent once (Arm A has 733 chunks but 709 unique `embed_text`s).
- A miss returns the same float32-rounded values a later hit would, so results do not depend on cache state.

**D19 Quota plan: two quota days (owner, from V-1).**
V-1: every text counts as 1 request. Both arms need 709 + 859 = 1,568 requests, more than 1,000 per day (the daily reset is 14:00 UTC+7).

| | Arm A | Arm B |
|---|---|---|
| Chunks / unique embed texts | 733 / 709 | 859 / 859 |
| Texts shared with the other arm | 0 | 0 |
| Estimated tokens (chars/4, unique texts) | 174,842 | 307,285 |
| Expected wall time (D15 simulation of `CachingEmbedder(GeminiEmbedder)`: last call starts at 7.0 / 12.0 min, plus that call) | ≈ 8 min | ≈ 13 min |

**Plan (RAG-001b):**
- **Arm A before today's (Sat 26 Sep) 14:00 UTC+7 reset.** This quota day already has 6 requests spent (probe 3 + live test 3), so it ends at about 715 of 1,000.
- **Arm B after the 14:00 reset,** in the next quota day: 859 of 1,000. That leaves about 141 for the 42 question embeddings (36 eval + 6 dev; one embedding per question serves both arms) and light dev testing.
- RAG-001b needs 99-VERIFY of this task first. If Arm A cannot start before 14:00, the same split moves by one quota day: Arm A after 14:00 today, Arm B after 14:00 tomorrow.
- The cache makes a quota stop mid-arm safe: the re-run sends only the missing texts.

Arm A is smaller than ADR-0004's 200–300K token guess (≈ 175K by character count); Arm B is ≈ 307K.

## Consequences
- The core `Embedder` protocol gains `model_id` and a provider-free `EmbeddingTask` (DOCUMENT / QUERY). Gemini task-type strings live only in `infrastructure/embeddings/gemini_embedder.py`. The new `EmbeddingError` is a core exception.
- Model name, dimension, limits, batch size, attempts, timeout and cache path live in `config.py` (env-overridable). `git grep gemini-embedding-001 -- src/` hits only `config.py`.
- RAG-001b uses `CachingEmbedder(GeminiEmbedder(...))` for indexing and `metadata={"hnsw:space": "cosine"}` (or the equivalent in the installed Chroma version) for both collections. Collections should carry `model_id` in their name or metadata.
- Changing the dimension, model or task type invalidates the cache key by construction; nothing is silently reused.

## Amendment 2026-09-26: fixes from 99-VERIFY
The verifier ([RAG-001a-verify](../../reviews/code/RAG-001a-verify.md), ACCEPT WITH FIXES) found:
- **F1:** the cache committed per 45-text slice while the embedder re-split slices over 12.5K est. tokens into several calls. A later failure dropped earlier paid vectors.
- **F2:** through the cache, Arm B still ran in 39 calls with the last call at 18.0 min.

Changes:
- **F1:** `Embedder.plan_calls` added to the core protocol (moved to infrastructure in amendment 2); `CachingEmbedder` no longer takes a `batch_size` and commits per planned call (D18).
  - Test: 45 texts of 352 est. tokens are planned as 35 + 10. When the second call always fails, the 35 rows of the first call are in the SQLite file, and a re-run sends only the other 10.
  - The same with a daily-quota 429 on the second call: 35 rows kept, no wait, no retry.
- **F2:** D15 now gives numbers for the real pipeline (Arm A 16 calls / 7.0 min, Arm B 25 calls / 12.0 min). They are unchanged from the embedder-alone simulation because each cache group is now one call.
- **Retry (verify X5a):** a daily-quota 429 raises `QuotaExhaustedError` at once. Other retry waits are capped at 120 s and logged (D15).
- **Paths (verify X5b):** data paths resolve from the repo root; `.gitignore` covers `data/` folders anywhere in the tree (D16).

## Amendment 2 2026-09-26: RAG-001b Step 0 (open items from the RAG-001a re-verify)
- **`plan_calls` leaves core.** How texts are split into provider calls is a Gemini batching detail, so it is no longer part of the core `Embedder` protocol (`model_id`, `embed`). It lives on `PlannedEmbedder(Embedder, Protocol)` in `infrastructure/persistence/embedding_cache.py`; `CachingEmbedder` takes a `PlannedEmbedder` as its inner embedder, and D18's one-commit-per-call rule is unchanged. `CachingEmbedder` itself satisfies the core `Embedder` protocol, so the application's `IndexCorpus` receives it as a plain `Embedder`. Tests: the core protocol has exactly `model_id` and `embed`; every protocol member exists on `CachingEmbedder` with the same signature.
- **Raw body of the first 429 (exception to D15's "never the error body").** `GeminiEmbedder` logs the JSON body of the first HTTP 429 per embedder instance (one run) at `WARNING`, before the daily-quota check, so the D15 classifier can be checked against a real error. The configured key and anything shaped like a Google API key (`AIza` + 35 characters) are replaced by `[REDACTED]` first. Later 429s and other codes are not logged raw. `scripts/ingestion/build_index.py` writes warnings to stderr and to `data/logs/build-index-arm-<a|b>.log` (git-ignored). Tests: a daily 429 logs its body once and then raises; a second 429 in a run is not logged raw; a 503 is not; the key is redacted. Mutations (log after the daily check; no redaction) are each killed.
- **Accepted, not fixed (owner, RAG-001b prompt):**
  - the daily-quota error format is still untested against a real daily 429;
  - connection errors (`httpx.ConnectError`) are not retried by the embedder: indexing is resumable, and RAG-003 retries them on the LLM path (RAG-003 kept this rule; since then such errors are wrapped into `EmbeddingError` instead of escaping as raw `httpx` exceptions);
  - the throttle's per-minute counter lives in one process, so it resets when a script restarts.
- **Chroma detail (installed chromadb 1.5.9).** Creating a collection with `metadata={"hnsw:space": "cosine", ...}` sets `configuration.hnsw.space = "cosine"` (checked on a scratch collection). This is the "equivalent in the installed Chroma version" named in Consequences. Collection name `kb_{chunker_config}_{model_id}`, with characters Chroma does not allow (such as `@`) changed to `-`. The metadata keeps the exact `chunker_config` and `embedding_model_id` and is checked on every open, so two settings that sanitize to the same name cannot share a collection.

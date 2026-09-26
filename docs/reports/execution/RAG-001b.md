# RAG-001b execution report: ChromaDB vector store + index both arms

Date: 2026-09-26 · Branch: `rag-001b` (from `origin/dev` `f81faa5`) · Prompt: [prompt-log](../../prompt-log/claude-code/RAG-001b.md) · Environment: Windows 11, `.venv` Python 3.13.3, `chromadb` 1.5.9, `google-genai` 1.75.0

## Entry check
- Ledger row 06a (RAG-001a): `verified` (ACCEPT on re-verify 2026-09-26). ADR-0005 is accepted, and the cache works (RAG-001a tests + re-verify).
- `git status` at the start showed:
  - `.claude/worktrees/` untracked: not mine, left alone. Files are staged by explicit path only.
  - The owner's uncommitted edits to `agents/prompts/06b-…md` (the new Step 0) and `agents/prompts/CHANGELOG.md`. The CHANGELOG row says "commit with the next docs change", so they went into this branch's first commit, `1865607`. The CHANGELOG's last column now names the commits (`f81faa5` for the RAG-003 row).
- Pre-edit impact (GitNexus, upstream): all **LOW**; no HIGH/CRITICAL.

  | Symbol | Risk | Upstream |
  |---|---|---|
  | `Embedder` | LOW | 2 importers: the cache and the Gemini embedder |
  | `VectorStore` | LOW | 0 callers |
  | `CachingEmbedder` | LOW | 0 callers |
  | `GeminiEmbedder._embed_batch` | LOW | 1 caller (`embed`), 1 flow |
- Time at start: 09:00 UTC+7. Arm A (≈ 8 min) fitted before the 14:00 reset, so it ran at once (ADR-0005 D19).

## Step 0 (RAG-001a re-verify open items)
- **(a) `CachingEmbedder` conforms to core `Embedder`:** done the preferred way. `plan_calls` left `core/interfaces/embedding.py`; it now lives on `PlannedEmbedder(Embedder, Protocol)` in `infrastructure/persistence/embedding_cache.py`, the only consumer. `CachingEmbedder(inner: PlannedEmbedder, path)` satisfies `Embedder` (`model_id`, `embed`).
  - Tests: the core protocol has exactly `{model_id, embed}`; every protocol member exists on `CachingEmbedder` with the same kind and signature; a `CachingEmbedder` used as an `Embedder` works.
- **(b) Raw body of the first 429:**
  - `GeminiEmbedder` logs the JSON body of the first HTTP 429 per instance at `WARNING`, **before** the daily-quota check, so the daily 429 itself is captured.
  - The configured key and any `AIza…` key shape are replaced by `[REDACTED]`.
  - `build_index.py` writes warnings to stderr and to `data/logs/build-index-arm-<a|b>.log` (git-ignored).
  - No 429 occurred in the Arm A run: the log file is empty, so the classifier is still unchecked against a real body.
- **Accepted, not fixed (recorded in ADR-0005 amendment 2 and the ledger):**
  - the daily-quota error format is untested against a real error;
  - connection errors are not retried by the embedder (indexing is resumable; RAG-003 retries them on the LLM path);
  - the per-minute throttle counter resets on restart.

## Files changed
| File | Change |
|---|---|
| `src/.../core/models/__init__.py` | `RetrievedChunk(chunk, rank 1-based, score)` |
| `src/.../core/interfaces/vector_store.py` | `VectorStore`: `upsert`, `search -> list[RetrievedChunk]`, `count`, `get_ids` (was `add`/`search -> list[DocumentChunk]`, 0 callers) |
| `src/.../core/interfaces/embedding.py` | `plan_calls` removed from `Embedder` (Step 0a) |
| `src/.../core/exceptions/__init__.py` | `VectorStoreError` |
| `src/.../infrastructure/persistence/embedding_cache.py` | `PlannedEmbedder` protocol; `CachingEmbedder.missing(texts, task)` (unique uncached texts, no API call, for dry runs) |
| `src/.../infrastructure/embeddings/gemini_embedder.py` | First-429 raw-body log with `redact_key` (Step 0b) |
| `src/.../infrastructure/vector_store/chromadb/chroma_store.py` (new) | `ChromaVectorStore` (details below) |
| `src/.../application/ingestion/build_chunks.py` | `record_to_chunk`, `load_chunks` (inverse of `chunk_to_record`) |
| `src/.../application/ingestion/index_corpus.py` (new) | `IndexCorpus`, `IndexReport`, `chunker_config_of` |
| `scripts/ingestion/build_index.py` (new) | `--arm A\|B [--dry-run]`; appends the report to `validation/retrieval/indexing-log.jsonl` |
| `scripts/utilities/peek_retrieval.py` (new) | top-k for one question; `--out` appends Markdown |
| `tests/unit/infrastructure/test_chroma_store.py` (new) | 11 tests |
| `tests/unit/application/test_index_corpus.py` (new) | 7 tests |
| `tests/unit/infrastructure/test_embedding_cache.py` | +3 (protocol has no batching detail, conformance, `missing`) |
| `tests/unit/infrastructure/test_gemini_embedder.py` | +4 (daily 429 body logged before the stop, only the first 429, 503 not logged, key redacted) |
| `docs/architecture/decisions/0005-…md` | Amendment 2 (Step 0a/0b, accepted items, Chroma detail); inline notes in D15/D18 |
| `validation/retrieval/indexing-log.jsonl`, `sanity-2026-09-26.md` (new) | Real run output |
| `AGENTS.md`, `CLAUDE.md` | GitNexus index counts only (written by `npx gitnexus analyze`) |
| Docs | this report, prompt log, `AI_WORKLOG.md`, ledger row 06b, master plan, EPIC-03 |

No new dependency: `chromadb` was already in `pyproject.toml` and `requirements.txt`.

### Design notes
- **Collection:**
  - `kb_{chunker_config}_{model_id}`. Characters outside `[A-Za-z0-9._-]` become `-`, so `@` does; Chroma rejects `@`, which was checked.
  - Arm A: `kb_header-1600_gemini-embedding-001-768`; Arm B: `kb_fixed-1600_gemini-embedding-001-768`.
  - Metadata: `hnsw:space=cosine`, `chunker_config`, `embedding_model_id` (unsanitized), `created_at` (UTC).
  - The store checks the metadata on every open and raises `VectorStoreError` on a mismatch. So `m@8` and `m-8`, which sanitize to the same name, cannot share a collection (test).
  - Chroma 1.5.9 maps the metadata to `configuration.hnsw.space = "cosine"` (checked on a scratch collection).
  - Telemetry is off. Every client uses one module-level `Settings`, because Chroma rejects a second client on the same path with different settings.
- **Metadata conversion:**
  - The document is `embed_text`; the metadata holds every other D6 field.
  - `heading_path` is stored as a JSON array string. This is unambiguous even if a heading contained ` > `; none does today, checked.
  - A `None` `source_url` is left out and read back as `None`. The real chunk files have no `None` URLs and no empty heading paths, so only the tests exercise these conversions.
- **Score:** `1 - cosine distance`. The test separates cosine from its neighbours: a query `[2,0,0]` against a stored `[1,0,0]` scores 1.0. Inner product would score 2, and squared L2 would score 0.
- **`IndexCorpus`:**
  - All pending `embed_text`s go to **one** `embed()` call; only the Chroma upsert is batched (100).
  - The embedder and cache own the split into provider calls (ADR-0005 D18), so the planned throughput holds. The advisor noted that slicing chunks first would have broken D15's call plan.
  - Cost counters come from an injected `usage` callable (`CachingEmbedder.stats`). The application layer therefore depends only on core interfaces and a callable, not on the cache type.
- **`cache_hits` counts unique texts found in the cache.** Arm A's 24 duplicate `embed_text`s (733 chunks, 709 unique) are deduplicated inside the call, so they appear as `api_texts = 709`, not as hits.
- **`--dry-run`:**
  - Opens the store read-only (`create=False`), so no collection is created.
  - Looks the pending texts up in the cache.
  - Plans calls with `GeminiEmbedder.plan_calls` (no client is created).
  - Simulates the throttle on a fake clock.

## Commands run (real output)
- Offline suite: `.venv/Scripts/python.exe -m pytest` → `211 passed, 1 deselected` (186 before; +25 = 11 + 7 + 3 + 4).
- Mutations (each restored from a scratchpad copy; suite back to 211 passed):

  | Mutation | Result |
  |---|---|
  | `DISTANCE = "ip"` | 2 failed |
  | `IndexCorpus` does not skip ids already in the store | 2 failed |
  | score = `-distance` | 2 failed |
  | 429 body logged after the daily-quota check | 1 failed |
  | no key-shape redaction | 1 failed |
- Dry runs (no API), 09:0x UTC+7:
  ```
  DRY RUN arm A (header-1600), collection kb_header-1600_gemini-embedding-001-768 (not created yet)
  chunks in file: 733; already in store: 0; to index: 733
  unique texts to send (not in cache): 709; est. tokens (chars/4): 174842
  provider calls: 16; largest call: 45 texts
  quota requests (1 per text): 709 of 1000/day
  simulated: last call starts at 7.0 min (throttle 90 req/min, 25000 tok/min; call latency not included)
  DRY RUN arm B (fixed-1600), collection kb_fixed-1600_gemini-embedding-001-768 (not created yet)
  chunks in file: 859; already in store: 0; to index: 859
  unique texts to send (not in cache): 859; est. tokens (chars/4): 307285
  provider calls: 25; largest call: 42 texts
  quota requests (1 per text): 859 of 1000/day
  simulated: last call starts at 12.0 min (throttle 90 req/min, 25000 tok/min; call latency not included)
  ```
  Both arms match ADR-0005 D19 (709 / 174,842 and 859 / 307,285) and D15 (16 calls / 7.0 min and 25 calls / 12.0 min). The plan agrees with the quota-day decision: Arm A today, before 14:00 (6 + 709 = 715 of 1,000); Arm B after the reset.
- **Arm A, live** (`build_index.py --arm A`, 09:12:04–09:19:13 UTC+7):
  ```
  "chunks_total": 733, "already_present": 0, "newly_embedded": 733, "cache_hits": 0,
  "api_texts": 709, "api_requests": 709, "estimated_tokens": 174842, "duration_s": 426.937,
  "store_count": 733, "http_calls": 16, "retries": 0, "throttle_wait_s": 391.4
  store.count() = 733; lines in arm-a.jsonl = 733; MATCH
  ```
  7.1 min wall time against 7.0 min simulated (plus the last call). No 429, no retry; `data/logs/build-index-arm-a.log` is empty.
- **Arm A re-run** (09:19:32):
  ```
  "already_present": 733, "newly_embedded": 0, "cache_hits": 0, "api_texts": 0, "api_requests": 0,
  "estimated_tokens": 0, "duration_s": 0.125, "store_count": 733, "http_calls": 0
  store.count() = 733; lines in arm-a.jsonl = 733; MATCH
  ```
- **Arm B dry-run again** (14:09 UTC+7, after the reset): same as above; the collection was not created yet, and there were 859 texts, 307,285 est. tokens and 25 calls, 12.0 min simulated.
  - The background waiter meant to start Arm B at 14:05 had been stopped by Claude Code for low memory at about 10:13, so nothing had run.
  - Arm B was started by hand at 14:09.
- **Arm B, live** (`build_index.py --arm B`, 14:09:55–14:22:04 UTC+7):
  ```
  "chunks_total": 859, "already_present": 0, "newly_embedded": 859, "cache_hits": 0,
  "api_texts": 859, "api_requests": 859, "estimated_tokens": 307285, "duration_s": 728.44,
  "store_count": 859, "http_calls": 25, "retries": 0, "throttle_wait_s": 669.0
  store.count() = 859; lines in arm-b.jsonl = 859; MATCH
  ```
  12.1 min wall time against 12.0 min simulated (plus the last call). No 429, no retry; `data/logs/build-index-arm-b.log` is empty.
- **Arm B re-run** (14:22:21):
  ```
  "already_present": 859, "newly_embedded": 0, "cache_hits": 0, "api_texts": 0, "api_requests": 0,
  "estimated_tokens": 0, "duration_s": 0.148, "store_count": 859, "http_calls": 0, "retries": 0
  store.count() = 859; lines in arm-b.jsonl = 859; MATCH
  ```
- **Both arms after Arm B:**
  - Dry-runs show "already in store: 733 / to index: 0" (A) and "859 / 0" (B).
  - A direct `ChromaVectorStore(..., create=False)` check with `.env` loaded: A `733 == 733`, B `859 == 859`, both collections `hnsw:space = cosine`.
  - Arm A is unchanged by the Arm B run.
- **Where the index actually is: `D:\ChromaDB`, not `data/chroma/`.**
  - The owner's local `.env` sets `CHROMA_PATH=D:\ChromaDB`. Both scripts call `load_dotenv`, so Arm A (09:12) and Arm B (14:09) were both written there.
  - `get_chroma_path()` without `.env` gives `data/chroma` (the ADR-0005 D16 / OD-7 default).
  - I found this at 14:22 when a check I ran without `.env` saw 0 items.
  - `D:\ChromaDB\chroma.sqlite3` holds exactly the two collections of this task. It also has two folders dated 2026-09-24 that this task did not create, and I left them alone.
  - I did **not** edit `.env` (owner's file, holds the key), did not re-index into `data/chroma/`, and did not copy the store: RAG-002 reads the same `.env`, so one store stays the single source.
  - **DECISION REQUIRED (owner):** keep `D:\ChromaDB` and amend OD-7 / ADR-0005 D16, or set `CHROMA_PATH=data/chroma` and rebuild. A rebuild should cost 0 quota because every vector is in the embedding cache; that is expected, not verified.
  - Side effect of my check: it created an empty `data/chroma/chroma.sqlite3` (0 collections, git-ignored). My attempt to delete it was blocked by the permission check, so it is still there for the owner to remove.
- **Sanity check** (live, 1 request; [sanity-2026-09-26.md](../../../validation/retrieval/sanity-2026-09-26.md)):
  ```
  | 1 | 0.7325 | 10:header-1600:0005 | Dependency injection in ASP.NET Core > Overview of dependency injection |
  | 2 | 0.7303 | 10:header-1600:0027 | Dependency injection in ASP.NET Core > Scope validation |
  | 3 | 0.7244 | 10:header-1600:0016 | Dependency injection in ASP.NET Core > Service lifetimes |
  | 4 | 0.7190 | 17:header-1600:0036 | Integration tests in ASP.NET Core > Inject mock services |
  | 5 | 0.7183 | 10:header-1600:0021 | Dependency injection in ASP.NET Core > Lifetime and registration options |
  ```
  - 4 of the 5 hits come from doc 10 (DI in ASP.NET Core), including "Service lifetimes" and "Lifetime and registration options".
  - This is a smoke check of one question, not a retrieval metric.
  - The question is not in `eval-v1.jsonl` or `dev-v1.jsonl`. The nearest eval items (Q-EVAL-013/014/017/029/035) ask about middleware, DbContext lifetime and scope validation.
- **Key-leak check** (a script that prints counts only):
  - The real key: 0 matches in tracked files (`git grep -F`), and 0 in `data/logs/`, `validation/retrieval/` and `data/chroma/`.
  - Its 8-character prefix: also 0 everywhere.
  - Generic `AIza`: 19 hits in tracked files. All are verifier secret-scan commands in `docs/reviews/…`, the redaction regex, or the fake keys in tests.
  - **Correction (14:25):** the `data/chroma/` part of this scan checked an empty folder; the store is in `D:\ChromaDB` (see above).
- **Key-leak check, after Arm B** (14:25; raw bytes, the key read from the environment, counts only):
  - Files scanned: `D:\ChromaDB` (every file, 39 MB sqlite included), `data/cache/*`, `data/logs/*`, `validation/retrieval/*`, and the Arm B console output. That is 27 untracked files, with 0 matches of the full key, 0 of its 8-character prefix and 0 of `AIza`.
  - Tracked files: 0 matches of the full key and 0 of the prefix.
  - Generic `AIza` in tracked files (`git grep -o AIza <commit>`):
    - 24 occurrences in 17 files at `bd2fee8`, and 22 in 17 at `456f2f8`.
    - Every one is of the same kinds as before: verifier scan commands in `docs/reviews/…`, this report and ADR-0005 describing the scan, the redaction regex, and fake test keys.
    - I did not re-derive the morning figure of 19; it was not produced with this same command.
- **Quota** (V-1 accounting, 1 request per text; not checked against the AI Studio dashboard):
  - Quota day ending 14:00 UTC+7: 6 before this task + Arm A 709 + sanity query 1 = **716 of 1,000**.
  - Quota day starting 14:00 UTC+7: Arm B **859 of 1,000**. The re-run and the dry-runs cost 0.
- **GitNexus:**
  - `npx gitnexus analyze`, then `detect_changes(compare, origin/dev)` before the milestone-1 commit: 52 symbols in 14 files, risk **medium**.
  - Affected flows: only the embed/cache flows (`Embed → …`, `_embed_and_store → _from_blob`, `Missing → _from_blob`) and the new `Run → Record_to_chunk`.
  - No chunking, parsing or evaluation flow is affected.
  - **Before the final commit (14:30):** the GitNexus MCP server failed to connect in this session, so I used the CLI.
    - `npx gitnexus analyze` crashed with `COPY failed for File: bad allocation`. The machine was low on memory, the same cause that stopped the Arm B waiter. The index stays stale at `1865607`.
    - `npx gitnexus detect-changes -s unstaged` reported "No changes detected". That is expected: this commit changes only docs and `indexing-log.jsonl`, with no code symbol.
    - `-s compare -b origin/dev` also reported "No changes detected". That is **not credible** for a branch with code changes, so I treat it as inconclusive (stale index). The milestone-1 MCP result above (52 symbols, medium) is the valid one for the code, because `git diff --stat efc11e3 bd2fee8 -- src scripts tests` is empty: no code changed after that check.
- **Offline pytest after all edits:** 211 passed, 1 deselected (the live Gemini test).

## Unverified / limits
- **The store path differs from ADR-0005 D16:** it is `D:\ChromaDB` (owner's `.env`), not `data/chroma/`. This is DECISION REQUIRED, see Checks.
- The daily-quota 429 classifier has still not seen a real response: no 429 happened in either arm.
- Chroma behaviour was checked on Windows only.
- The Chroma data is outside the repo and not committed (ADR-0005 D16). It can be rebuilt from the chunk files plus the embedding cache set in `.env`, expected at 0 quota; that rebuild was not tried.
- I did not print the effective cache path. My attempt to print the path settings was blocked by the permission check, so the cache location is unverified. The key scan covered `data/cache/*`.
- The sanity check is one question and one arm.

## Deviations from the prompt
1. **`IndexCorpus` reads the chunk file through `load_chunks(path)`,** an application function next to `chunk_to_record`, instead of an injected reader interface. It is pure stdlib JSON, the inverse of the existing writer.
2. **`IndexReport` has extra fields:**
   - `api_texts` (cache misses) next to `api_requests`, plus `store_count`, `started_at`, `chunker_config` and `embedding_model_id`;
   - the script adds `http_calls`, `retries` and `throttle_wait_s`.

   `newly_embedded` means chunks embedded and upserted by this run.
3. **`--dry-run` also prints a simulated duration** and creates no Chroma collection. Opening the client still creates an empty `chroma.sqlite3` at the path if missing. It also creates an empty embedding cache file if missing. Both are git-ignored or outside the repo.
4. **`ChromaVectorStore` has a `create=False` read-only mode,** used by `--dry-run` and `peek_retrieval.py`.
5. **`VectorStoreError` is a core exception,** so the application layer can catch it.

## Explain it back
- **Why one collection per arm, named from the chunker config and the model id:**
  - ADR-0003 D7 holds everything constant except chunking, so each arm needs its own index to compare.
  - Because the embedding `model_id` (`model@dim`) is in the name and checked in the metadata, changing the model or dimension creates a new collection instead of silently mixing vectors from two embedding spaces.
  - The alternative, one fixed name per arm, would reuse a stale index after a config change.
- **Why the score is `1 - distance`, and how the test proves cosine:**
  - Chroma returns a cosine *distance* (0 = same direction); the app wants a similarity where higher is better.
  - On unit vectors, cosine and inner product rank identically, so "identical vector scores 1" proves nothing.
  - A query twice as long in the same direction does: cosine gives 1, inner product 2, squared L2 0.
- **Why resume = skip ids already in the store, plus the embedding cache:**
  - The store skip makes a re-run of a finished arm a no-op (733 present → 0 embedded, 0 API requests).
  - The SQLite cache covers a run that stopped halfway (a quota stop before the upsert): every paid vector is already committed there, so the re-run pays only for texts never embedded.
  - The resume test uses a bare fake embedder, so the cache cannot hide a broken skip.
- **Why `IndexCorpus` makes one `embed()` call and batches only the upsert:**
  - The embedder owns the split into provider calls (≤ 45 texts and ≤ 12.5K est. tokens, ADR-0005 D15/D18).
  - Pre-slicing into 100-chunk groups would add small tail calls that waste the 60 s windows. The live run used exactly the 16 planned calls in 7.1 min.
- **Why `plan_calls` left core:**
  - How a provider splits calls is a Gemini batching detail. Core describes only what the application needs: `model_id` and `embed`.
  - Moving it to an infrastructure protocol lets `CachingEmbedder` satisfy the core `Embedder` without faking a method, and keeps core provider-free (CLAUDE.md rule 3).
- **Why the index stayed in `D:\ChromaDB` instead of being moved to `data/chroma/`:**
  - The path comes from `CHROMA_PATH` in the owner's `.env`. Every script and the future RAG-002 retrieval read the same setting, so the index they use is the one they will find.
  - Editing `.env` (it holds the key) or keeping a second copy in `data/chroma/` would split one index into two that can drift apart. Changing where the data lives is the owner's decision (OD-7).
  - Either way, a rebuild is cheap: the vectors are in the embedding cache, so rebuilding should need no new quota.

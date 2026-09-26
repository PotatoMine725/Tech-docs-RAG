# RAG-001a execution report: Gemini embedder + embedding cache (no indexing)

Date: 2026-09-26 · Branch: `rag-001a` (from `origin/dev` `739676f`) · Prompt: [prompt-log](../../prompt-log/claude-code/RAG-001a.md) · Environment: Windows 11, `.venv` Python 3.13.3, `google-genai` 1.75.0

## Entry check
- Tag `eval-freeze-v1` exists and points to `739676f` (= `origin/dev` at start).
- Ledger:
  - Row 02 (EVAL-002): `verified`, frozen.
  - Row 04 (INGEST-002): `verified`; G2 passed.
  - Row 04a (INGEST-004): `verified`.
- `git status`: only `.claude/worktrees/` was untracked. It is not mine and was left alone; files are staged by explicit path only.
- Pre-edit impact (GitNexus): `Embedder` upstream → LOW, 0 callers; `get_chroma_path` upstream → LOW, 0 callers (the default is asserted by `tests/unit/test_config.py`, updated in the same commit).

## Step 0 decisions → [ADR-0005](../../architecture/decisions/0005-embedding-and-vector-store-settings.md)
| Decision | Result | By |
|---|---|---|
| Output dimensionality | 768, L2-normalized (D14) | owner (AskUserQuestion) |
| OD-7 Chroma path | `data/chroma/`, git-ignored, rebuilt by script (D16) | owner |
| OD-8 distance | cosine (D17) | owner |
| Batch size | 45 texts, and ≤ 12.5K est. tokens per call; throttle counts texts (D15) | owner confirmed 45; token cap after the owner's throughput check |
| Quota plan | Arm A before today's 14:00 UTC+7 reset, Arm B after it (D19) | owner, from V-1 |

## V-1 probe (live, 1 call, 3 texts)
`scripts/utilities/probe_embedding_quota.py`, run once at 2026-09-26 00:44:38 UTC. It refuses to run again because its output file exists.

Real output:
```
sent_at_utc=2026-09-26T00:44:38+00:00 model=gemini-embedding-001 texts=3 http_requests=1
embeddings returned: 3; metadata: None
  01:header-1600:0000: chars=1487 chars/4=371 dim=768 l2_norm=0.5809 statistics=None
  01:header-1600:0011: chars=1116 chars/4=279 dim=768 l2_norm=0.5802 statistics=None
  08:header-1600:0000: chars=107 chars/4=26 dim=768 l2_norm=0.5853 statistics=None
saved data\cache\probe-v1.json
```

The owner read AI Studio → Usage → "Gemini Embedding 1" before (07:44) and after (07:52), from screenshots:
- RPM: 0 → **3**.
- TPM: 0 → **≈ 585**.
- RPD: shows a **3** peak.

**1 batched request = N requests.** The chars/4 estimate (678) is ≈ 15% above the chart's tokens.

## Files changed
| File | Change |
|---|---|
| `src/.../core/interfaces/embedding.py` | `EmbeddingTask` enum (DOCUMENT/QUERY); `Embedder.model_id` property; `embed(texts, task)` |
| `src/.../core/exceptions/__init__.py` | `EmbeddingError` |
| `src/.../config.py` | `EmbeddingSettings` + `get_embedding_settings()` (model, dim, batch size, RPM/TPM limits, attempts, timeout, cache path; env-overridable). `CHROMA_PATH` default → `data/chroma` (OD-7) |
| `src/.../infrastructure/embeddings/throttle.py` (new) | `SlidingWindowThrottle` (60 s window, requests and estimated tokens, injectable clock/sleep; raises if one call can never fit); `estimate_tokens` (chars/4) |
| `src/.../infrastructure/embeddings/gemini_embedder.py` (new) | `GeminiEmbedder`. Batching capped by count, per-minute requests and half the per-minute tokens. Throttle charged `len(batch)` requests (V-1). Retry on 429/500/503/504/timeouts: backoff 1-2-4-8 s + jitter, `Retry-After`/`RetryInfo` honoured, then `EmbeddingError`. Explicit 60 s client timeout. L2-normalizes below 3,072 and checks the dimension. Counters: `http_calls`, `api_requests`, `retries`, `estimated_tokens`, `throttle_wait_s` |
| `src/.../infrastructure/persistence/embedding_cache.py` (new) | `CachingEmbedder`. SHA-256 key over `model_id\|task\|text`; SQLite with columns key, model_id, task, dim, vector (float32 LE), created_at. Misses deduplicated and sent in batches, committed per batch. Results keep input order. Counters: hits, misses, inner_calls, estimated_tokens (+ inner `api_requests`) |
| `scripts/utilities/probe_embedding_quota.py` (new) | V-1 probe |
| `tests/fakes.py` (new) | `FakeEmbedder` (deterministic unit vectors from a hash, records calls) |
| `tests/unit/infrastructure/test_gemini_embedder.py` (new) | 23 tests: config, request shape, batching, normalization, dimension, retry, throttle (incl. two worst-case calls in one 60 s window, real defaults on worst-case chunks), V-1 accounting |
| `tests/unit/infrastructure/test_embedding_cache.py` (new) | 9 tests: 0 inner calls on repeat, misses only, order, in-call dedup, per-batch persistence + resume, key includes task/model_id, re-open, float32 parity, counters, wrong count |
| `tests/integration/retrieval/test_gemini_embedding_live.py` (new) | `@pytest.mark.gemini` EN/VI/unrelated similarity; cached in `data/cache/live-tests.sqlite` |
| `tests/unit/test_config.py` | Default Chroma path assertion → `data/chroma` |
| `pyproject.toml` | pytest `pythonpath = ["src", "."]` so `from tests.fakes import FakeEmbedder` resolves (no `__init__.py` under `tests/`) |
| `.gitignore` | `data/cache/` |
| `.env.example` | `CHROMA_PATH=data/chroma`; commented embedding settings |
| `docs/architecture/decisions/0005-…md` (new) | ADR-0005 |
| `docs/architecture/tech-stack.md` | OD-7, vector-data policy, SQLite use recorded |
| `docs/plans/master-plan.md`, `epics/EPIC-03-rag-baseline.md`, `task-ledger.md` | OD-7/OD-8/V-1 answered, quota plan, EPIC-03 status, row 06a |
| `AGENTS.md`, `CLAUDE.md` | GitNexus index counts only (written by `npx gitnexus analyze`) |
| `AI_WORKLOG.md`, `docs/prompt-log/claude-code/RAG-001a.md` (new) | Worklog entry; prompt verbatim |

No new dependency. `httpx` is imported to catch timeouts; it is already installed as a dependency of `google-genai`.

## Commands run (real output)
- Offline suite, final: `.venv/Scripts/python.exe -m pytest` → `173 passed, 1 deselected in 4.77s`. This task adds 32 offline tests (23 + 9) and 1 live test. (171 before the owner's throughput check added 2.)
- Live, once: `.venv/Scripts/python.exe -m pytest -m gemini -k embed -s` (07:53:55 UTC+7):
  ```
  cos(EN, VI)=0.9055 cos(EN, unrelated)=0.6606 cos(VI, unrelated)=0.6172
  cache/API stats: {'hits': 0, 'misses': 3, 'inner_calls': 1, 'estimated_tokens': 51, 'api_requests': 3}
  1 passed, 171 deselected in 3.40s
  ```
- `git grep -n "gemini-embedding-001" -- src/` → one hit: `src/knowledge_assistant/config.py:37` (the config default).
- Mutations (each restored with `git checkout`; suite back to 171 passed):
  - Throttle charged 1 request per call instead of per text → 1 failed.
  - Normalization removed → 1 failed.
  - Cache sends all misses in one inner call → 2 failed.
  - Per-call token cap back to the full 25K (no half-budget cap) → 2 failed (restored from a scratchpad backup, byte-identical).
- GitNexus: `npx gitnexus analyze` (index was stale), then `detect_changes(compare, origin/dev)`:
  - 226 changed symbols in 21 files; risk **high**, driven by volume of new code.
  - All 9 affected processes are the new embed flows (`Embed → L2_normalize`, `_embed_and_store → _from_blob`, `Embed → _retry_after_s`, …). No pre-existing chunking, parsing or evaluation flow is affected.
- Quota spent by this task (V-1 accounting): probe 3 + live test 3 = **6 requests**. No indexing.

- Throughput simulation (offline; the real `GeminiEmbedder` + throttle, fake client + fake clock, real unique `embed_text`s, default settings):
  ```
  a 709 texts 174842 est tok avg 247
    new rule (cap 12.5K/call): calls, max, avg batch, last call at min, texts/min: (16, 45, 44.3, 7.0, 101.3)
  b 859 texts 307285 est tok avg 358
    new rule (cap 12.5K/call): calls, max, avg batch, last call at min, texts/min: (25, 42, 34.4, 12.0, 71.6)
  a old rule: calls 16 last call at min 7.0
  b old rule: calls 20 last call at min 18.0
  ```
  The printed "texts/min" divides by the *start* of the last call, so it overstates Arm A. The real rate is ≈ 90/min, request-bound, because 16 calls at 2 per minute span 8 windows.

## SDK inspection (`google-genai` 1.75.0, read from the installed package, not from memory)
- `Models.embed_content(self, *, model, contents, config=None) -> EmbedContentResponse`.
- `EmbedContentConfig` fields: `http_options, task_type, title, output_dimensionality, mime_type, auto_truncate, document_ocr, audio_track_extraction`.
- `EmbedContentResponse`: `embeddings` (each `ContentEmbedding.values`, `.statistics` = `truncated, token_count`) and `metadata`.
- For the Gemini API (not Vertex), `embed_content` sends a list of contents to `{model}:batchEmbedContents`, one HTTP call.
- `HttpOptions.timeout` is in **milliseconds** and defaults to `None` (no timeout), so the embedder sets 60,000 ms explicitly.
- `HttpOptions.retry_options` defaults to `None`, and `retry_args(None)` means stop after 1 attempt: the SDK does not retry. Our retry is the only layer.
- `errors.APIError(code, response_json, response)` exposes `.code`, `.status`, `.details` (the JSON body, where a `RetryInfo.retryDelay` can appear) and `.response` (headers for `Retry-After`).

## Unverified / limits
- V-1 rests on chart readings from owner screenshots of one probe; no exact tooltip values were recorded. RPM 0 → 3 is clear. The RPD chart shows a 3, but its day bins looked shifted, so the per-day count rests on that chart plus the same unit. The owner accepted "every text = 1 request" for both limits, and the plan is the conservative one. TPM ≈ 585 is approximate.
- Whether a failed (429) call counts against quota is unknown. The embedder counts it, which is conservative.
- chars/4 was checked against 3 texts only.
- The throttle and retry were tested with fakes only; no real 429/503 happened.
- Windows only; the suite was not run on Linux.

## Deviations from the prompt
1. **Retry codes:** 500 and 504 are retried in addition to 429/503/timeouts (both transient server errors). Non-retryable codes (e.g. 400) fail at once.
2. **Throttle unit = texts,** not HTTP calls. This follows V-1; the prompt says "requests", and V-1 shows each text is a request.
3. **Batching in two layers** (superseded by the verify fixes: the cache now follows the embedder's plan, see the addendum): `CachingEmbedder` slices misses into batches itself (constructor `batch_size`), so each batch is committed before the next call. Otherwise one inner call could hold all misses, and a crash would lose them.
4. **Dimension check raises `EmbeddingError`,** not a Python `assert`, because asserts vanish under `-O`.
5. **`CachingEmbedder` path is a constructor argument;** the default location (`data/cache/embeddings.sqlite`) is `EmbeddingSettings.cache_path`.
6. **The live test uses its own cache file** (`data/cache/live-tests.sqlite`) so its texts never mix into the index cache, and a re-run spends no quota.
7. **Per-call token cap = half the per-minute budget** (added after the owner's throughput check). The prompt's rule is "largest batch that stays under the per-minute token limit". With per-text quota and a throttle that admits whole calls, that rule lets one Arm B call take most of a window, so only one call per minute would run (simulated 18 min instead of 12). Half the budget lets two calls share every window.

## Explain it back
The first two bullets were partly wrong (verify C1/C2); the corrected versions are in the addendum below.

- **Why a cache, and why SQLite:** each paid embedding is committed in one transaction right after its batch returns. A crash or the 14:00 quota stop loses nothing, and a re-run sends only misses. JSONL could leave a torn last line, and using Chroma as the cache would tie paid vectors to collections we delete and rebuild.
- **Why the throttle counts texts:** the V-1 probe (1 HTTP call, 3 texts) moved AI Studio's RPM from 0 to 3, so batching saves HTTP overhead but not quota. Counting calls would have let a 45-text batch look like 1 request and hit 429s. The same fact makes indexing two quota days: 709 + 859 = 1,568 > 1,000/day. The throttle admits whole calls over a sliding 60 s window, so each call is also capped at half the token budget. Without the cap, two 45-text Arm B calls (≈ 32K) could not share a 25K window, and Arm B would take 18 min instead of 12.
- **Why normalize at 768:** only 3,072-d output is pre-normalized (the probe measured norms ≈ 0.58 at 768). Unit vectors make cosine, inner product and L2 rank the same, and cosine (OD-8) is also robust if a vector were ever left unnormalized. 768 keeps the store 4× smaller with a small quality cost.
- **Why `model_id = model@dim` is part of the key:** changing model, dimension or task type can never silently reuse old vectors. The alternative, a plain text hash, would mix incompatible vectors after a config change.
- **Why core has `EmbeddingTask` and not `RETRIEVAL_DOCUMENT`:** core stays provider-free (CLAUDE.md rule 3). The Gemini strings live only in the Gemini adapter, so a different provider could plug in without touching core or application code.

## Addendum 2026-09-26: fixes from 99-VERIFY
Input: [RAG-001a-verify](../../reviews/code/RAG-001a-verify.md), ACCEPT WITH FIXES, plus the owner's fix list (F1, F2, retry, paths). Offline only: **0 Gemini requests** in this session; the gemini-marked live test was edited (constructor call) but **not run**. First step: pushed the verifier's local commit `c53be1b` to `origin/rag-001a`.

### What was wrong
- **F1 (paid vectors lost):** `CachingEmbedder` cut misses into 45-text slices and committed per slice, but `GeminiEmbedder` re-split any slice over 12.5K est. tokens into several HTTP calls. If a later call in a slice failed, the earlier calls' paid vectors were dropped.
- **F2:** for the same reason the half-budget cap did not reach the real pipeline: Arm B ran in 39 calls with the last one at 18.0 min.
- My throughput simulation had modelled `GeminiEmbedder` alone, not the `CachingEmbedder(GeminiEmbedder)` pipeline RAG-001b will run, so it could not see this.

### Changes
| File | Change |
|---|---|
| `src/.../core/interfaces/embedding.py` | `Embedder.plan_calls(texts) -> list[list[str]]`: the groups `embed` sends; `embed(group)` on one group is one provider call |
| `src/.../core/exceptions/__init__.py` | `QuotaExhaustedError(EmbeddingError)` |
| `src/.../infrastructure/embeddings/gemini_embedder.py` | `_batches` → public `plan_calls` (GitNexus rename dry run: 1 call site). Daily-quota 429 (QuotaFailure `quotaId`/`quotaMetric` names a per-day quota) → `QuotaExhaustedError` at once, message "resume after the 14:00 UTC+7 reset". Other retries: wait = max(backoff, server delay) capped at **120 s**; each wait logged at `WARNING` (texts, HTTP code/status, attempt, seconds; no body, no key) |
| `src/.../infrastructure/persistence/embedding_cache.py` | No `batch_size`; misses go out in the inner embedder's planned groups, one commit per group before the next is sent. A plan that drops or reorders texts raises `EmbeddingError` |
| `src/.../config.py` | `PROJECT_ROOT`, `resolve_project_path`; `get_chroma_path()` and `cache_path` resolve relative values (default or env) from the repo root; new `get_chunks_dir()` (`data/processed/chunks`), `get_logs_dir()` (`data/logs`). Absolute values are kept |
| `.gitignore` | `**/data/chroma/*` + `!/data/chroma/.gitkeep`, `**/data/cache/`, `**/data/logs/` |
| `.env.example` | Note that relative paths resolve from the repo root; commented `CHUNKS_DIR`, `LOGS_DIR` |
| `tests/fakes.py` | `FakeEmbedder(batch_size=10)` + `plan_calls`; `FakeClock`, `FakeModels` (now with `fail_from_call`, call timestamps) and `api_error` (RetryInfo / QuotaFailure bodies) moved here from the embedder tests |
| `tests/unit/infrastructure/test_embedding_pipeline.py` (new) | 3 tests of `CachingEmbedder(GeminiEmbedder)` with real default limits (below) |
| `tests/unit/infrastructure/test_gemini_embedder.py` | +5: 120 s cap + logged waits, per-minute 429 retried with the server delay, daily 429 stops at once, `QuotaExhaustedError` is an `EmbeddingError`, `plan_calls` = what `embed` sends and re-planning a group returns it |
| `tests/unit/infrastructure/test_embedding_cache.py` | `batch_size` moved to `FakeEmbedder`; +1: a bad inner plan is rejected |
| `tests/unit/test_config.py` | Rewritten (pytest): root anchoring of defaults and relative env values, absolute values kept, a child process in another cwd resolves the same absolute files, `build_chunks.py` writes where config reads |
| `tests/integration/retrieval/test_gemini_embedding_live.py` | Constructor call without `batch_size` (not run) |
| ADR-0005, `tech-stack.md` | D15 pipeline numbers, 120 s cap, daily-quota rule; D16 root-relative paths + `.gitignore`; D18 one commit per provider call; D19 wall-time row source; amendment note |

### Commands run (real output)
- Offline suite (Windows, `.venv` Python 3.13.3): `.venv/Scripts/python.exe -m pytest -q` → **`186 passed, 1 deselected in 5.01s`** (173 before; +13 new: 3 pipeline, 5 embedder, 1 cache, 6 config − 2 replaced config tests).
- F1 pipeline tests (fake client, one fake clock, real defaults 45 / 90 / 25K / 5 attempts):
  - `test_a_failed_second_call_keeps_the_first_calls_paid_vectors_and_a_rerun_pays_only_the_rest`: 45 texts × 352 est. tokens are planned as 35 + 10. Calls: `[35] + [10] * 5` → `EmbeddingError`; **35 rows** in the SQLite file. The resumed run sends exactly one call with the other 10 texts (`api_requests == 10`), and the file then holds 45 rows.
  - `test_daily_quota_stop_keeps_earlier_calls_and_makes_no_retry`: call 2 is a daily 429 → `QuotaExhaustedError`, 2 HTTP calls, **no sleep**, 35 rows kept.
  - `test_through_the_cache_every_http_call_is_one_cache_group_and_windows_stay_under_the_token_budget`: 120 worst-case texts (435 est. tokens); HTTP calls == cache groups, no call over 12,500, every 60 s window ≤ 25,000.
- Mutation proofs (each file copied to the scratchpad first and restored from that copy, byte-identical by `cmp`; suite back to 186 passed):

| Mutation | Result |
|---|---|
| MF1 cache slices misses by count (45) instead of the embedder's plan | 6 failed: all 3 pipeline tests, `test_misses_are_sent_in_batches_and_each_batch_is_stored`, `test_stats_expose_counters`, `test_an_inner_plan_that_drops_or_reorders_texts_is_rejected` |
| MR1 retry wait not capped | 1 failed: `test_server_retry_delay_is_capped_at_120_s_and_every_wait_is_logged` (waits were 36,000 s) |
| MR2 daily 429 treated as retryable | 2 failed: `test_daily_quota_429_stops_at_once_with_the_reset_time`, `test_daily_quota_stop_keeps_earlier_calls_and_makes_no_retry` |
| MR3 retry waits not logged | 1 failed: the cap/log test |
| MP1 paths resolved from the cwd | 4 failed: defaults, relative env values, other-cwd child process, chunk builder |

  - The first MP1 run left the other-cwd test green: it compared the child's paths only with the parent's, and both were the same relative strings. The test now also asserts the absolute paths under the repo root; re-run → 4 failed.
- F2 re-simulation through the real pipeline: `CachingEmbedder(GeminiEmbedder)`, fake client, one fake clock for throttle and sleeps, temp SQLite per arm, **all** chunk `embed_text`s from `data/processed/chunks/arm-*.jsonl`, default settings:
  ```
  settings: batch=45 rpm=90 tpm=25000 dim=768
  arm A: chunks=733 unique=709 vectors=733 http_calls=16 cache_groups=16 api_requests=709 est_tokens=174842 avg_texts_per_call=44.3 max_call_tokens=12487 worst_60s_tokens=24648 worst_60s_requests=90 last_call_start_min=7.0 throttle_wait_s=420.0
  arm B: chunks=859 unique=859 vectors=859 http_calls=25 cache_groups=25 api_requests=859 est_tokens=307285 avg_texts_per_call=34.4 max_call_tokens=12499 worst_60s_tokens=24755 worst_60s_requests=79 last_call_start_min=12.0 throttle_wait_s=720.0
  ```
  Verifier's numbers before the fix: Arm A 20 calls / 7.0 min, Arm B 39 calls / 18.0 min.
- `.gitignore` check: `git check-ignore -v` ignores `data/cache/x`, `scripts/data/cache/x`, `src/data/chroma/x`, `data/chroma/x`, `data/logs/x`, `scripts/data/logs/x`; `data/chroma/.gitkeep` is **not** ignored. `git ls-files -ci --exclude-standard` is empty before and after (no tracked file newly ignored).
- GitNexus: `npx gitnexus analyze` (index was older than `c53be1b`); `impact` upstream on `CachingEmbedder`, `GeminiEmbedder`, `Embedder`, `get_embedding_settings`, `get_chroma_path`, `FakeEmbedder` → all **LOW** (callers are tests and the other embedding module). `detect_changes(all)`: 75 changed symbols in 15 files, risk "high" by volume; the 8 affected processes are all embed flows (`_embed_and_store → _from_blob`, `Embed → Get_gemini_api_key`, `Embed → L2_normalize`, `Embed → Estimate_tokens`, `Embed → _to_blob`, `Embed → _from_blob`, `_embed_and_store → Cache_key`, `Embed → _retry_after_s`). No chunking, parsing or evaluation flow.
- Quota spent in this fix session: **0**.

### Unverified / limits
- The daily-quota classifier is built from the documented `google.rpc.QuotaFailure` shape (`quotaId` like `...PerDay...`). No real daily 429 has been captured, so the exact field values Gemini sends are not verified. If a real daily 429 does not match, it falls back to the retry path: at most 4 waits of ≤ 120 s, each logged, then `EmbeddingError`. The run stops within about 8 minutes instead of hanging.
- A 429 whose QuotaFailure names neither a per-minute nor a per-day quota is treated as per-minute (retried).
- The live test's constructor call changed; it was not re-run (quota rule).
- The throughput numbers are simulated (no call latency); a real run adds network time per call.
- Scripts under `scripts/` already anchor their own paths with `Path(__file__).parents[2]`. They were not changed; a test pins that `build_chunks.py` writes to `get_chunks_dir()`.
- Windows only.

### Deviations
1. **`plan_calls` joins the core `Embedder` protocol.** The owner offered "the cache forms groups with the same half-budget token cap" or a commit callback. Copying the cap into the cache would give two copies of the split rule that can drift, and a callback would change the `embed` signature. With `plan_calls` the embedder stays the only owner of the rule and the cache commits per call by construction; `FakeEmbedder` implements it too.
2. **`get_chroma_path()` returns a `Path`**, not a `str` (no production caller yet). `EmbeddingSettings.cache_path` is a `Path` too.
3. **New `CHUNKS_DIR` / `LOGS_DIR` settings** (defaults `data/processed/chunks`, `data/logs`) so RAG-001b has one root-anchored source for them; no logs directory existed before.
4. **Retry waits are logged at `WARNING`** via the standard `logging` module; nothing configures a handler yet, so the host script decides where logs go.

### Explain it back (corrected)
- **Why a cache, and why SQLite:** the embedder decides how texts are split into provider calls (`plan_calls`), and the cache sends misses in exactly those groups, committing each group in one SQLite transaction before the next call. So every paid call's vectors are stored before anything else is sent; a crash, a 503 run-out or the 14:00 daily stop loses nothing, and a re-run sends only the missing texts. My first version committed per 45-text slice while the embedder split slices further, so one failure could drop a paid call.
- **Why each call is capped at half the token budget, and why that now reaches indexing:** the throttle admits whole calls in a sliding 60 s window, so two calls per window must each stay ≤ 12.5K est. tokens. Because the cache no longer re-slices, the real pipeline runs Arm B in 25 calls with the last at 12.0 min (18.0 min before). Arm A is request-bound at 7.0 min either way.
- **Why a daily-quota 429 stops at once but a per-minute one is retried:** a per-minute 429 clears within a minute, so backing off (server delay honoured, capped at 120 s, logged) works. A daily 429 cannot clear before 14:00 UTC+7, so retrying would only burn time; `QuotaExhaustedError` stops the run cleanly and the cache already holds everything paid for.
- **Why paths resolve from the repo root:** a relative path follows the working directory, so a script started from `scripts/` would open a new, empty cache there (paying for every text again) in a folder `.gitignore` did not cover. Now every relative data path is joined to the repo root, and `.gitignore` covers a `data/` folder anywhere.
- **Why the tests use the real pipeline:** each class was already tested alone. The bug was in how the two classes fit together, so only a test of `CachingEmbedder(GeminiEmbedder)` with real limits could catch it.

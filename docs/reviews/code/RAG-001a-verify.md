# VERIFY RAG-001a

Verifier session, 2026-09-26 (08:15–08:40 UTC+7), Windows 11, `.venv` Python 3.13.3. Reviewed branch `rag-001a` (`a8e4a2d`, `05ec4d6`, `39fefd5`, `eeed2dd`; base `dev` `739676f`; PR #9 into `dev`, open) against `agents/prompts/06a-RAG-001a-embedder-and-cache.md`, `_common.md`, ADR-0004/0005, CLAUDE.md and the owner's extra checks 1–7.

**Quota rule: zero Gemini requests were spent.** No `@pytest.mark.gemini` test and no probe was run. Live claims were checked against the execution report, `data/cache/probe-v1.json` and `data/cache/live-tests.sqlite` only.

Method:
- All numbers below come from my own commands.
- Mutations were applied in place with `sed` or a Python rewrite, then restored with `git checkout -- <file>`. `git status --short src/ tests/` was empty after each restore, and the full suite was re-run afterwards (173 passed).
- Simulations used the real `GeminiEmbedder`, `SlidingWindowThrottle` and `CachingEmbedder` with a fake client, a fake clock and a temp SQLite file. There were no repo writes.

## A. Acceptance / gate items (prompt + owner's extra checks X1–X7)

| # | Item | Result | Evidence |
|---|---|---|---|
| Entry | Tag `eval-freeze-v1`, INGEST-002 G2 | PASS | The report's entry check matches the ledger. `git diff --stat 739676f..HEAD -- corpus data/evaluation` → empty (the corpus and eval set are untouched since the freeze). |
| Step 0 | ADR-0005 with dim / batch / OD-7 / OD-8 | PASS | `decisions/0005-…md` D14 768, D15 batch 45, D16 `data/chroma/`, D17 cosine; owner decisions recorded. |
| Iface | `EmbeddingTask`, `Embedder.model_id`, `embed(texts, task)`; core provider-free | PASS | `core/interfaces/embedding.py:5-18`. `grep -rnE "chromadb\|google\.genai\|from google\|PySide6\|RETRIEVAL_(DOCUMENT\|QUERY)\|gemini-embedding" src/.../core src/.../application` → no hits (rc=1). |
| Do 1 | Model + dim from config | PASS | `gemini_embedder.py:135,145` read `self._settings`. `git grep -n "gemini-embedding-001" -- src/` → only `config.py:37`. No hits in `scripts/` or `tests/`: the probe and the live test read `get_embedding_settings()`. |
| Do 1 | Retry 429/503/timeouts, backoff 1-2-4-8 + jitter, Retry-After, max attempts → `EmbeddingError` | PASS | `gemini_embedder.py:137-163`; tests `test_503_twice…` (sleeps `[1,2]`), `test_always_failing…` (`[1,2,4]`, 4 calls), `test_timeouts…`, `test_429_honours_retry_delay…` (17 s), `test_non_retryable…`. 500/504 are also retried (disclosed deviation 1). |
| Do 1 | SDK signature inspected, not guessed | PASS | Calls match `embed_content(*, model, contents, config)` and `EmbedContentConfig(task_type, output_dimensionality)`; the fake client uses keyword-only arguments, so a positional mismatch would fail the tests. |
| Do 2 | Cache columns, SQLite path, `data/cache/` ignored | PASS | `embedding_cache.py:17-26`. `live-tests.sqlite` schema is identical. `git check-ignore -v data/cache/x` → `.gitignore:233`. |
| Do 3 | Offline tests listed in the prompt | PASS | 23 embedder + 9 cache tests (counted from `def test_` lines); `FakeEmbedder` in `tests/fakes.py`. |
| Do 3 | Live test (EN/VI/unrelated) | PASS (from cache, 0 quota) | I recomputed the cosines from the three stored vectors in `live-tests.sqlite` (keys = `cache_key("gemini-embedding-001@768", DOCUMENT, text)` for the test's strings): **EN–VI 0.9055, EN–unrelated 0.6606, VI–unrelated 0.6172**, the same as the report. `created_at` = `2026-09-26T00:53:59+00:00` = 07:53:59 UTC+7, the same as the report. |
| Acc | `pytest` green, no network | PASS | See B: `173 passed, 1 deselected`. |
| **X1a** | Throttle: sliding 60 s window on **both** requests and estimated tokens | PASS | `throttle.py:48-60`: entries older than `now-60` are dropped, then both sums are checked (`:54`). Requests are charged per text: `gemini_embedder.py:139` `requests=len(batch)`, pinned by `test_every_text_in_a_batched_call_counts_as_one_quota_request`. Every retry attempt is charged again (`:139` inside the attempt loop), which is conservative. |
| **X1b** | Half-budget per-call cap | PASS in `GeminiEmbedder`, but see C1 | `gemini_embedder.py:105` `max_tokens = tokens_per_minute // 2`. A single text above the cap becomes its own batch; a call above the full budget raises (`throttle.py:42`). |
| **X1c** | The two new tests fail under mutation | PASS | **M1, drop the token check** (`throttle.py:54` → requests only): 3 failed. They are `test_throttle_waits_when_tokens…`, **`test_throttle_holds_two_worst_case…`** and **`test_production_settings_keep_every_60s…`**. **M2, drop the cap** (`:105` → full TPM): 2 failed, `test_batches_are_capped_at_half…` (renamed test) and **`test_production_settings…`**. `test_throttle_holds_two_worst_case…` passes under M2, as expected: it tests the throttle, not batching. So each new test is killed by at least one mutation. Both mutations were restored; the suite was back to 173 passed. |
| **X2a** | Key = sha256(model_id \| task \| text); model_id includes dim | PASS | `embedding_cache.py:31`; `config.py:31` `f"{model}@{dim}"`; `test_default_settings…` asserts `some-model@1536`. |
| **X2b** | Different task or dim → different key | PASS | `test_task_and_model_id_are_part_of_the_key` (key-level `m@8` vs `m@768`, plus end-to-end inner call counts). The stored `model_id` in `live-tests.sqlite` is `gemini-embedding-001@768`. |
| **X2c** | Re-run sends only misses | PASS | `test_mixed_batch_sends_only_misses…`, `test_misses_are_sent_in_batches_and_each_batch_is_stored` (resume sends only `["5"]`), `test_cache_survives_reopening_the_file`. |
| **X2d** | A batch is committed right after it returns | **FAIL** (C1) | It is true for the cache's own 45-text slice (`embedding_cache.py:126-127`, one transaction). It is not true for the paid HTTP calls inside the slice; see C1. |
| **X2e** | Mutation on the per-batch commit | PASS | **M3**: writes deferred until after the last slice (Python rewrite of `embed` / `_embed_and_store`) → `test_misses_are_sent_in_batches_and_each_batch_is_stored` failed (1 failed, 8 passed). Restored. |
| **X3** | L2-normalized at 768, length asserted; no task strings in core; model only in config | PASS | `gemini_embedder.py:172-174` (length check raises `EmbeddingError`; normalize when `dim < 3072`); tests `test_vectors_below_full_size…`, `test_wrong_dimension_raises`. The three stored live vectors have norm **1.000000** (recomputed from the float32 blobs). Core grep: see *Iface*. |
| **X4** | ADR-0005 content | PASS | V-1 section: 1 call / 3 texts at 00:44:38 UTC, RPM **0 → 3**, TPM ≈ 585, RPD caveat ("day bins appear shifted… the per-day count rests on that chart plus the same unit"), "Re-check if a quota error contradicts this". D14 768, D17 cosine, D16 `data/chroma/`, D15 batch 45, D18 SQLite reasons (atomic writes, resume, alternatives rejected). D19: Arm A before 14:00 UTC+7 today, Arm B after. The D15 throughput table is wrong for the real pipeline; see C2. |
| **X5a** | Known risk: uncapped server retry-after | CONFIRMED, **MEDIUM** | `gemini_embedder.py:160` `sleep(max(backoff, retry_after or 0.0))`, with no upper bound. Offline repro: a 429 with `retryDelay: "36000s"` → `EmbeddingError` after 5 attempts, sleeps `[36000, 36000, 36000, 36000]` = **40 h** of silent blocking. Each retry also charges quota. Likelihood is low: Google usually sends short delays. The impact is high on a 14:00 deadline, because the run hangs with no log line. Not fixed (owner: confirm and rate). |
| **X5b** | Known risk: relative default paths | CONFIRMED, **MEDIUM** | `config.py:7,44` default to `data/chroma` and `data/cache/embeddings.sqlite`, relative to the working directory. From a scratch directory, both resolved under that directory, and `CachingEmbedder` created a new empty SQLite file there (`Path.parent.mkdir(parents=True)`, `embedding_cache.py:48`), so every text was a miss and would be paid again. It is also worse than stated: `git check-ignore -v scripts/data/cache/x src/data/chroma/x` → no match (rc=1), because the `.gitignore` patterns are anchored to the repo root. A run from `scripts/` would leave paid vectors in an **unignored** file. Mitigation until fixed: always run from the repo root. Not fixed (owner: confirm and rate). |
| **X6** | Secrets | PASS | `git grep -nI AIza` → only earlier reviews quoting the grep command. I compared the real key (from `.env`, never printed) byte-wise against `live-tests.sqlite`, `probe-v1.json`, the execution report, `AI_WORKLOG.md` and the prompt-log → all `False`. `git grep -lF <key>` → none. `.env` is ignored (`.gitignore:223`) and untracked. There is no `logs/` directory; the cache stores only key hash, model_id, task, dim, vector and timestamp. |
| **X7** | Full offline pytest (Windows) | PASS | `.venv/Scripts/python.exe -m pytest -q` → **`173 passed, 1 deselected in 7.00s`** (again after the mutations: `173 passed, 1 deselected in 5.84s`). |

## B. Tests
- Summary: `173 passed, 1 deselected` (the deselected test is the gemini-marked live test).
- The new tests assert behaviour, not only that code runs:
  - Throttle waits are exact times on a fake clock (57 s, 40 s, 5 s, 59 s, 120 s total).
  - Retry sleep sequences and call counts are asserted.
  - Batching asserts the exact batch sizes.
  - Normalization asserts `[0.6, 0.8, 0, 0]` and the norm.
  - Cache tests count inner calls and exact inner inputs.
- All three mutations were killed (A X1c, X2e).
- Gap: no test runs `CachingEmbedder` over `GeminiEmbedder`. Each is tested alone with fakes, so the interaction in C1/C2 is not covered.
- `test_production_settings…` sends 90 identical texts through `GeminiEmbedder` directly, so it cannot see the cache's slicing.

## C. Claims vs reality

| # | Claim | Result | Evidence |
|---|---|---|---|
| C0 | Numbers in the report / ADR | PASS | Arm A 733 chunks / 709 unique / 174,842 est. tokens; Arm B 859 / 859 / 307,285; 0 texts shared; worst chunk 1,738 chars = 435 tokens; probe norms 0.5809/0.5802/0.5853, dim 768, `metadata: None`, `statistics: None`; ceil(chars/4) sum 678. All recomputed from `data/processed/chunks/arm-*.jsonl` and `probe-v1.json`. The owner's AI Studio readings (RPM 0→3, TPM ≈ 585) cannot be traced to a file. The report and ADR say this plainly, so this is not a fabrication finding. |
| **C1** | ADR D18 / report: "every batch of paid vectors is committed in one transaction right after it returns… never loses paid vectors" | **FAIL (MEDIUM)** | `CachingEmbedder` cuts misses into 45-text slices (`embedding_cache.py:92-94`). `GeminiEmbedder._batches` then re-splits any slice over 12,500 est. tokens into several HTTP calls (`gemini_embedder.py:104-118`). The cache commits only when the whole slice returns. If a later HTTP call in the slice fails after all retries, the earlier calls' paid vectors are thrown away. Offline repro (real defaults, 45 texts × ~352 tokens, 2nd HTTP call always 503): `EmbeddingError`, **6 HTTP calls, 85 quota requests charged, 0 rows stored** (35 paid vectors lost). Exposure per arm (simulation over the real unique texts): **Arm A 4 of 16 slices split, Arm B 19 of 20**. |
| **C2** | ADR D15 / report throughput table: Arm B last call at **12.0 min** with the half-budget cap | **FAIL (MEDIUM)** | The 12.0-min figure is right for `GeminiEmbedder` alone (I reproduced it: 25 calls, last start 12.0 min). RAG-001b will run `CachingEmbedder(GeminiEmbedder)` (ADR-0005 Consequences). Through the cache, each 45-slice splits into two uneven calls (e.g. 35 + 10). Arm B then takes **39 HTTP calls, last start 18.0 min**, the same as without the cap. The owner's throughput fix does not reach the production pipeline. Arm A is unchanged: 20 calls, last start **7.0 min**. |
| C3 | Worklog RAG-001a entry: "30 offline tests", "171 passed offline" | FAIL (LOW, stale) | Now 32 offline tests (23 + 9) and 173 passed; the execution report is correct. |
| C4 | Report V-1 block prints `chars/4=371 … 26`; ADR says the estimate is 678 | NOTE | The probe prints floor(chars/4) (sum 676); `estimate_tokens` uses ceil (sum 678). Both are correct for what they label; this is a wording inconsistency only. |
| C5 | Quota spent by this task = 6 requests | PASS | `probe-v1.json` 3 texts, 1 call. `live-tests.sqlite` 3 rows, one `created_at`. |
| C6 | Mutations in the report | PASS (consistent) | I re-ran the throttle (M1), cap (M2) and commit (M3) mutations myself. Mine differ from the report's set but agree where they overlap: the cap mutation → 2 failed. |

## D. Project rules
- Layers: the structure test is in the green suite; the core/application grep is clean (A *Iface*).
- `infrastructure/persistence/embedding_cache.py` imports `infrastructure/embeddings/throttle.estimate_tokens`, which is infrastructure → infrastructure. That is allowed.
- Model name only in config: PASS (A Do 1).
- Key: PASS (X6).
- Corpus and eval set untouched since `eval-freeze-v1`: PASS (Entry).
- Excluded docs: not touched (no corpus or chunk code changed).
- SQLite use is justified in ADR-0005 D18, as CLAUDE.md rule 2 requires.

## E. Scope
- `pyproject.toml` `pythonpath = ["src", "."]`: needed for `from tests.fakes import FakeEmbedder`; disclosed.
- `CLAUDE.md` / `AGENTS.md`: GitNexus index counts only (tool-written); disclosed.
- The half-budget cap was added after an owner check and is recorded as deviation 7. The owner requested it, so it is not an unasked decision.
- No indexing was done.
- No finding.

## F. Quality spot-read
1. `SlidingWindowThrottle.acquire`:
   - Correct. The prune condition `<= now - window` guarantees a positive wait.
   - The loop re-checks after each sleep.
   - One call that could never fit raises instead of looping forever.
   - State is per process, so a restart right after a crash forgets the calls of the last minute. That can mean one 429 and a retry; LOW.
2. `GeminiEmbedder._embed_batch`:
   - Non-retryable `APIError`s become `EmbeddingError` at once. Good.
   - A non-timeout transport error (e.g. `httpx.ConnectError`) is neither retried nor wrapped: it escapes as a raw httpx exception. The prompt only requires 429/503/timeouts, so this is LOW; worth wrapping in RAG-003.
   - `retry_after` is uncapped: see X5a.
3. `CachingEmbedder.embed`:
   - Order is preserved and in-call duplicates are sent once.
   - A miss returns the float32 round-trip, so results do not depend on cache state (a good detail).
   - The slice/commit granularity does not match the HTTP-call granularity: C1/C2.

## G. Explain-it-back (report's final bullets)
- "Why a cache, and why SQLite… A crash or the 14:00 quota stop loses nothing" → **partly wrong.** A stop between cache slices loses nothing. A failure inside a slice that the embedder split into two calls loses the first call's paid vectors (C1). That affects 19 of 20 Arm B slices.
- "Why the throttle counts texts": correct.
- "…each call is also capped at half the token budget… Arm B would take 18 min instead of 12" → **correct for `GeminiEmbedder`, wrong for the pipeline RAG-001b will run.** Through `CachingEmbedder` Arm B still takes 18 min (C2).
- "Why normalize at 768", "Why model_id = model@dim", "Why core has EmbeddingTask": correct.

## Verdict: **ACCEPT WITH FIXES**
- FAIL: 4 (X2d/C1, C2, C3 LOW; C1 and X2d are the same defect).
- UNVERIFIED: 0. The owner's AI Studio chart readings cannot be traced to a file; this is disclosed and accepted.
- Confirmed risks: X5a MEDIUM and X5b MEDIUM, both kept open, not in the fix list (owner: confirm and rate).

**Can Arm A start before 14:00?** Under the ledger rules as written, **no**. `task-ledger.md` "Rules" says a task starts only when every prerequisite is `verified`, and `verified with fixes` does not count. So RAG-001b is blocked until the fixes are re-verified. The fixes are small and offline (about 1 fix session + 1 re-verify), which fits before 14:00.

On the technical risk alone, the owner could waive the rule for Arm A:
- Arm A's run time is the same with or without F1 (7.0 min).
- Only 4 of its 16 slices split, so a failure could lose at most one sub-call of paid vectors, and only in those 4 slices.

That waiver is the owner's decision, not the verifier's. Either way:
- Run every indexing command **from the repo root** (X5b).
- **F1 must land before Arm B.** 19 of 20 Arm B slices split, and the fix brings Arm B back to ≈ 12 min.

## Fix prompt (run in a new session on branch `rag-001a`)

```
Fix RAG-001a verifier findings (docs/reviews/code/RAG-001a-verify.md). Offline only: spend ZERO Gemini requests.
Run gitnexus_impact on every symbol before editing it; run detect_changes before committing.

1. Cache commits per HTTP call, and the cache and embedder use one batch plan
   (src/knowledge_assistant/infrastructure/persistence/embedding_cache.py, infrastructure/embeddings/gemini_embedder.py).
   Expected: every paid HTTP call's vectors are committed before the next HTTP call is sent. The cache's slicing
   must not undo the half-budget token cap. Option: the cache slices misses with the same rule as
   GeminiEmbedder._batches (count <= min(batch_size, RPM) AND est. tokens <= TPM // 2), e.g. via a shared
   plan_batches() function in infrastructure/embeddings. Then each cache slice is exactly one HTTP call.
   Checks:
   a) New test: CachingEmbedder over GeminiEmbedder (fake client + fake clock, real default settings),
      45 texts of ~352 est. tokens, the 2nd HTTP call always 503 -> EmbeddingError, and the rows from the
      1st HTTP call ARE in the SQLite file; a resumed run sends only the rest.
   b) New test: the same pipeline over 90+ worst-case texts keeps every 60 s window <= 25K est. tokens,
      and the number of HTTP calls equals the number of cache slices.
   c) Re-run the offline simulation over the unique embed_texts of arm-a.jsonl / arm-b.jsonl through
      CachingEmbedder(GeminiEmbedder): expect Arm A last call ~7.0 min, Arm B ~12.0 min (was 18.0).
   d) Mutation: revert to slicing by count only -> test (a) or (b) fails. Restore.
2. ADR-0005 D15/D18 and the execution report: state the throughput and "never loses paid vectors" for the
   CachingEmbedder(GeminiEmbedder) pipeline, with the re-run numbers from 1c. Add an ADR note dated today.
3. AI_WORKLOG.md RAG-001a entry: "30 offline tests" -> the real count, "171 passed" -> the real count, and add
   the verifier findings (C1/C2) under "AI got wrong".
Acceptance: .venv/Scripts/python.exe -m pytest -> green, no network; paste the summary.
Not in scope (owner decision, open items): capping server retry-after (X5a), anchoring default paths to the
project root (X5b).
```

## Open items (not fixes)
- X5a: cap `retry_after` (e.g. ≤ 120 s) and log each retry wait. MEDIUM; the owner decides when (RAG-001b or RAG-003).
- X5b: resolve `CHROMA_PATH` / `EMBEDDING_CACHE_PATH` defaults against the project root, or refuse to run outside it. MEDIUM. Until then, run every indexing command from the repo root.
- F LOW: a non-timeout transport error (`httpx.ConnectError`) is not wrapped in `EmbeddingError` and not retried.
- F LOW: the throttle's state is per process, so a restart right after a crash may cause one 429 (the retry covers it).

---

## Re-verify of the fix commit (2026-09-26, 08:45–09:00 UTC+7)

This was a new verifier session on the same machine: Windows 11, `.venv` Python 3.13.3. It checked the fix commit `94fdef2` ("RAG-001a: fixes from verify") on `rag-001a`.
- **Zero Gemini requests.** No gemini-marked test and no probe was run.
- **Scope:** the four FAIL/risk rows the owner named: F1 (= X2d/C1), F2 (= C2), retry (= X5a) and paths (= X5b). The run also covers the full offline suite and every row that passed before but whose code the fix touched (Iface, X1c/M2, X2e, X6).
- **Method:** mutations were applied in place by a Python rewrite, then restored with `git checkout -- <file>`. `git status --short src tests` was empty after each one. Simulations used the real `CachingEmbedder(GeminiEmbedder)` with the real default settings, `tests.fakes.FakeModels`, a `FakeClock` and a temp SQLite file.

| Row | Result | Evidence (my commands) |
|---|---|---|
| **F1 = X2d/C1**: every paid HTTP call is committed before the next one | **PASS** | `embedding_cache.py:93-102`: the cache walks `self._inner.plan_calls(...)` and calls `_embed_and_store` once per group. It checks that the plan covers every text once, in order. `gemini_embedder.py:125` `embed` sends exactly `plan_calls(texts)`. The plan is greedy, so a planned group re-plans to itself; this is pinned by `test_plan_calls_is_what_embed_sends_and_replanning_a_group_returns_it_unchanged`. **Repro from the first verify, re-run** (45 × ~352 tokens, 2nd HTTP call always 503): `EmbeddingError`, 6 HTTP calls, 85 quota requests, **35 rows stored** (was 0). **Mutations:** MF1 (cache slices by count 45, the pre-fix rule) → 6 failed, including all 3 `test_embedding_pipeline.py` tests. M3′ (defer every DB write until after the loop, on the new code) → 3 failed: `test_misses_are_sent_in_batches_and_each_batch_is_stored`, `test_a_failed_second_call_keeps_the_first_calls_paid_vectors…`, `test_daily_quota_stop_keeps_earlier_calls…`. |
| **F2 = C2**: throughput of the real pipeline | **PASS** | I ran my own simulation over the unique `embed_text`s of `data/processed/chunks/arm-*.jsonl` through `CachingEmbedder(GeminiEmbedder)`. **Arm A:** 709 unique, **16 HTTP calls = 16 cache groups**, last start **7.0 min**, max call 12,487 est. tokens, worst 60 s window 24,648. **Arm B:** 859 unique, **25 = 25**, last start **12.0 min** (was 39 calls / 18.0 min), max call 12,499, worst window 24,755. These match the report addendum and ADR-0005 D15/D18 exactly. |
| **Retry = X5a**: server retry-after capped, daily quota stops | **PASS** | `gemini_embedder.py`: `wait = min(max(backoff, retry_after), MAX_RETRY_WAIT_S=120)`, and each wait is logged at WARNING. The first verify's `retryDelay: "36000s"` repro now sleeps `[120, 120, 120, 120]` (was 40 h). A 429 whose `QuotaFailure` names a per-day quota raises `QuotaExhaustedError` (a subclass of `EmbeddingError`) with no retry and no sleep. A per-minute 429 is still retried. **Mutations:** MR1 (no cap) → 1 failed. MR2 (daily detection off) → 2 failed. MR3 (every `QuotaFailure` 429 treated as daily) → 1 failed (`test_per_minute_429_is_retried_with_the_server_delay`). |
| **Paths = X5b**: data paths are independent of the working directory | **PASS** | `config.py`: `PROJECT_ROOT = Path(__file__).resolve().parents[2]`. Relative defaults and env values resolve against it; absolute values are kept. From the scratchpad directory (`PYTHONPATH=src`), `get_chroma_path()` → `D:\Code\Python\Knowledge assistant\data\chroma` and the cache → `…\data\cache\embeddings.sqlite`. The package is **not** installed in `.venv`: from another directory, `import knowledge_assistant` fails with no PYTHONPATH, and there is no `.pth` or editable entry. Every entry point loads `config.py` from the repo's `src/`, either through `sys.path.insert(0, ROOT/"src")` in the scripts or through pytest `pythonpath`, so `parents[2]` is always the repo root. `git check-ignore -v scripts/data/cache/x src/data/chroma/x scripts/data/logs/x` → matched by `**/data/…` (`.gitignore:227/234/236`). `git ls-files -ci --exclude-standard` → empty, so no tracked file is newly ignored. `data/chroma/.gitkeep` is still tracked and not ignored. **Mutation:** MP1 (resolve relative to the cwd) → 4 failed. |
| C3: stale worklog counts | PASS | The worklog now says 32 offline tests and 173 passed (before the fixes), and the fix entry says 186. |
| Touched rows that passed before | PASS | **Iface:** the core/application grep for `chromadb\|google\.genai\|from google\|PySide6\|RETRIEVAL_…\|gemini-embedding` → no hits (rc=1). `plan_calls` is provider-free. **X1c/M2** (token cap at the full TPM) → 5 failed, still killed. **X2e:** see M3′ above. **X6:** `git grep -nI AIza` → only earlier reviews quoting the grep command. |
| **Tests** | PASS | `.venv/Scripts/python.exe -m pytest -q` → **`186 passed, 1 deselected in 4.96s`**. After all mutations were restored: `186 passed, 1 deselected in 5.02s`. The new pipeline tests assert exact call sizes (`[35] + [10] * 5`), stored row counts, the resumed call's exact inputs, no sleep after a daily 429, and 60 s token windows. They are not "runs without error" tests. |

**Scope (E):**
- The fix put `plan_calls` on the core `Embedder` protocol. The fix prompt had suggested a shared infrastructure helper instead.
- This is disclosed in ADR-0005 (D18, and the amendment list "F1: `Embedder.plan_calls` added to the core protocol"). It stays provider-free.
- It is a recorded design choice, not a defect.

### Re-verify verdict: **ACCEPT**
- FAIL: 0. UNVERIFIED: 0.
- All four rows now PASS.
- RAG-001b is unblocked. Run Arm A before the 14:00 UTC+7 reset and Arm B after it (ADR-0005 D19).

### Open items (non-blocking)
- **LOW:** `CachingEmbedder` has no `plan_calls`, so it no longer structurally satisfies the core `Embedder` protocol. This only matters if RAG-001b types the cache as `Embedder`, runs a type check, or stacks one cache on another. Either add a pass-through or type the wiring as `CachingEmbedder`.
- **LOW:** the daily-quota classifier is built from the documented `google.rpc.QuotaFailure` shape; no real daily 429 has been seen yet (disclosed). If a real one does not match, the fallback is 4 × 120 s of capped, logged retries and then `EmbeddingError`, so the stop is bounded.
- **LOW, carried over:** a non-timeout transport error (`httpx.ConnectError`) is neither wrapped nor retried.
- **LOW, carried over:** the throttle's state lives in one process, so a restart right after a crash may cause one 429.

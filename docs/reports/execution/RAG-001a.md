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
| Batch size | 45 texts; throttle counts texts (D15) | from V-1 |
| Quota days | two: Arm A in one quota day, Arm B in the next (D19) | from V-1 + stats |

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
| `src/.../infrastructure/embeddings/gemini_embedder.py` (new) | `GeminiEmbedder`. Batching capped by count, per-minute requests and tokens. Throttle charged `len(batch)` requests (V-1). Retry on 429/500/503/504/timeouts: backoff 1-2-4-8 s + jitter, `Retry-After`/`RetryInfo` honoured, then `EmbeddingError`. Explicit 60 s client timeout. L2-normalizes below 3,072 and checks the dimension. Counters: `http_calls`, `api_requests`, `retries`, `estimated_tokens`, `throttle_wait_s` |
| `src/.../infrastructure/persistence/embedding_cache.py` (new) | `CachingEmbedder`. SHA-256 key over `model_id\|task\|text`; SQLite with columns key, model_id, task, dim, vector (float32 LE), created_at. Misses deduplicated and sent in batches, committed per batch. Results keep input order. Counters: hits, misses, inner_calls, estimated_tokens (+ inner `api_requests`) |
| `scripts/utilities/probe_embedding_quota.py` (new) | V-1 probe |
| `tests/fakes.py` (new) | `FakeEmbedder` (deterministic unit vectors from a hash, records calls) |
| `tests/unit/infrastructure/test_gemini_embedder.py` (new) | 21 tests: config, request shape, batching, normalization, dimension, retry, throttle, V-1 accounting |
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
- Offline suite, final: `.venv/Scripts/python.exe -m pytest` → `171 passed, 1 deselected in 5.05s`. This task adds 30 offline tests (21 + 9) and 1 live test.
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
- GitNexus: `npx gitnexus analyze` (index was stale), then `detect_changes(compare, origin/dev)`:
  - 226 changed symbols in 21 files; risk **high**, driven by volume of new code.
  - All 9 affected processes are the new embed flows (`Embed → L2_normalize`, `_embed_and_store → _from_blob`, `Embed → _retry_after_s`, …). No pre-existing chunking, parsing or evaluation flow is affected.
- Quota spent by this task (V-1 accounting): probe 3 + live test 3 = **6 requests**. No indexing.

## Unverified / limits
- V-1 rests on chart readings from owner screenshots (no exact tooltip values), one probe. RPM and RPD agree, so it is recorded as verified; TPM ≈ 585 is approximate.
- Whether a failed (429) call counts against quota is unknown. The embedder counts it, which is conservative.
- chars/4 was checked against 3 texts only.
- The throttle and retry were tested with fakes only; no real 429/503 happened.
- Windows only; the suite was not run on Linux.

## Deviations from the prompt
1. **Retry codes:** 500 and 504 are retried in addition to 429/503/timeouts (both transient server errors). Non-retryable codes (e.g. 400) fail at once.
2. **Throttle unit = texts,** not HTTP calls. This follows V-1; the prompt says "requests", and V-1 shows each text is a request.
3. **Batching in two layers:** `CachingEmbedder` slices misses into batches itself (constructor `batch_size`), so each batch is committed before the next call. Otherwise one inner call could hold all misses, and a crash would lose them.
4. **Dimension check raises `EmbeddingError`,** not a Python `assert`, because asserts vanish under `-O`.
5. **`CachingEmbedder` path is a constructor argument;** the default location (`data/cache/embeddings.sqlite`) is `EmbeddingSettings.cache_path`.
6. **The live test uses its own cache file** (`data/cache/live-tests.sqlite`) so its texts never mix into the index cache, and a re-run spends no quota.

## Explain it back
- **Why a cache, and why SQLite:** each paid embedding is committed in one transaction right after its batch returns. A crash or the 14:00 quota stop loses nothing, and a re-run sends only misses. JSONL could leave a torn last line, and using Chroma as the cache would tie paid vectors to collections we delete and rebuild.
- **Why the throttle counts texts:** the V-1 probe (1 HTTP call, 3 texts) moved AI Studio's RPM from 0 to 3, so batching saves HTTP overhead but not quota. Counting calls would have let a 45-text batch look like 1 request and hit 429s. The same fact makes indexing two quota days: 709 + 859 = 1,568 > 1,000/day.
- **Why normalize at 768:** only 3,072-d output is pre-normalized (the probe measured norms ≈ 0.58 at 768). Unit vectors make cosine, inner product and L2 rank the same, and cosine (OD-8) is also robust if a vector were ever left unnormalized. 768 keeps the store 4× smaller with a small quality cost.
- **Why `model_id = model@dim` is part of the key:** changing model, dimension or task type can never silently reuse old vectors. The alternative, a plain text hash, would mix incompatible vectors after a config change.
- **Why core has `EmbeddingTask` and not `RETRIEVAL_DOCUMENT`:** core stays provider-free (CLAUDE.md rule 3). The Gemini strings live only in the Gemini adapter, so a different provider could plug in without touching core or application code.

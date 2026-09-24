# RAG-001a — Gemini embedder + embedding cache (no indexing yet)

Read `agents/prompts/_common.md` first and follow it.
Read: ADR-0004 (D10, D13, Consequences), ADR-0003 D5/D9, master-plan §5 (quota), `src/knowledge_assistant/core/interfaces/embedding.py`, `config.py`.
**Entry (hard): git tag `eval-freeze-v1` exists and INGEST-002 gate G2 passed. Otherwise STOP.**

## Step 0 — decisions (ask the user, then write `docs/architecture/decisions/0005-embedding-and-vector-store-settings.md`)
| Decision | Options | Recommendation |
|---|---|---|
| Output dimensionality | 3072 (default) / 1536 / 768 | 768: 4× smaller store, faster; L2-normalize because only 3072 is pre-normalized. Record it as a constant for both arms. |
| Batch size | 1 … 100 texts per request | Largest batch that stays under the per-minute token limit; decided after V-1. |
| OD-7 Chroma path | `D:\ChromaDB` / `data/chroma/` | `data/chroma/`, git-ignored, rebuilt by script (reproducible). Update `.env.example` and `config.py` default. |
| OD-8 distance | cosine / l2 / ip | cosine, same for both arms. |

**V-1 probe (live, ≤ 3 texts):** write `scripts/utilities/probe_embedding_quota.py` that sends ONE request with 3 texts. Before running, ask the user to note the request count on the AI Studio usage page; after running, ask again. Record "1 batched request = N requests" in ADR-0005. Then compute from `stats-arm-a.json` / `stats-arm-b.json`: total chunks, estimated tokens (chars / 4), requests needed, minutes at the per-minute limit → decide 1 or 2 quota days (daily reset = 14:00 UTC+7).

## Interface change (core — impact-check first)
```python
# core/interfaces/embedding.py
class EmbeddingTask(str, Enum): DOCUMENT = "document"; QUERY = "query"
class Embedder(Protocol):
    @property
    def model_id(self) -> str: ...          # e.g. "gemini-embedding-001@768" (model + dim), used as cache/collection key
    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]: ...
```
Core stays provider-free: the Gemini task-type strings (`RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`) appear only in infrastructure.

## Do
1. `infrastructure/embeddings/gemini_embedder.py` (`GeminiEmbedder`):
   - model name + dimensionality from config (`EMBEDDING_MODEL`, `EMBEDDING_DIM`), never hard-coded;
   - batching; **throttle** with a sliding 60 s window on both requests and estimated tokens (limits from config);
   - retry on 429/503/timeouts: exponential backoff 1-2-4-8 s + jitter, honour retry-after if present, max attempts from config; then raise `EmbeddingError` (new core exception);
   - L2-normalize when dim < 3072; assert every returned vector has the configured length;
   - inspect the installed `google-genai` package for the exact `embed_content` signature and config class — do not guess from memory.
2. `infrastructure/persistence/embedding_cache.py` (`CachingEmbedder` decorator, wraps any `Embedder`):
   - key = sha256(`model_id | task | text`); storage = SQLite file `data/cache/embeddings.sqlite` (stdlib `sqlite3`; CLAUDE.md rule 2 allows SQLite only for a concrete need — record the reason, atomic writes + resume, in ADR-0005) with columns key, model_id, task, dim, vector (float32 bytes), created_at;
   - on `embed`: look up all keys, call the inner embedder only for misses, write misses immediately after each batch (a crash never loses paid vectors);
   - counters: hits, misses, API requests, estimated tokens → exposed for logging.
   - `data/cache/` added to `.gitignore`.
3. Tests (offline):
   - `FakeEmbedder` (deterministic vectors from a text hash, counts calls) in `tests/fakes.py` — reused by later tasks;
   - cache: second call with same texts = 0 inner calls; mixed hit/miss batch only sends misses; order of results preserved; different task or model_id = different key; survives re-open of the SQLite file;
   - throttle: with a fake clock, N requests over the limit wait the expected time;
   - retry: fake client raising 503 twice then succeeding → 3 attempts; always failing → `EmbeddingError` after max attempts;
   - normalization and dimension assert.
   - Live test `@pytest.mark.gemini`: embed 2 texts (1 EN, 1 VI with the same meaning) → correct dim, cosine(EN, VI) > cosine(EN, unrelated text). Print the three similarities.

## Acceptance
```
.venv/Scripts/python.exe -m pytest                       # green, no network
.venv/Scripts/python.exe -m pytest -m gemini -k embed    # run once on purpose, green
git grep -n "gemini-embedding-001" -- src/   # 0 hits outside config
```
ADR-0005 exists with V-1 result and the quota-day decision. No indexing in this task.

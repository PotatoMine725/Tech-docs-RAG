# RAG-003 — Retry/fallback, token accounting, CLI, smoke checks (gate G3 / M2)

Read `agents/prompts/_common.md` first and follow it. Read ADR-0004 D11–D13.
Entry: RAG-002 done.

## Do
1. **OD-11** (ask user): max retries before fallback — recommend 3 attempts, exponential backoff + jitter, honor retry-after; then `gemini-3.5-flash` once. Record in ADR-0004 as an amendment.
2. Extend the basic Gemini LLM adapter from RAG-002 (`infrastructure/llm/gemini/` only): client-side throttle to the per-minute request limit (config), retry on 429/503/timeouts and connection errors (e.g. `httpx.ConnectError`/`httpx.ReadTimeout`, wrapped into a core `LLMError` subtype so callers never see raw httpx exceptions), fallback model, record `model_used`, `retry_count`, `fallback_used`, prompt/output token counts from the response usage metadata (needed for cost benchmarking later). Model names from config only.
3. CLI `scripts/ask.py "question" [--arm A|B] [--json]`: prints answer, numbered citations (doc, heading path, excerpt), insufficient flag, latency per stage, model, tokens.
4. **Smoke checks** (live, mark as "smoke check, not evaluation data") → `validation/generation/smoke-<date>.md`: 1 EN + 1 VI answerable question (NOT from the eval set), 1 out-of-corpus question → insufficient message. Paste real outputs.
5. Secret scan: key absent from repo, logs, outputs.
6. Offline tests: retry/backoff/fallback logic with a fake client that raises 503 then succeeds; a fake connection error then success (retried) and a persistent connection error (wrapped error after max attempts, no raw httpx exception escapes); fallback after N failures; token fields populated.

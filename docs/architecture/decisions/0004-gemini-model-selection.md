# ADR-0004 Gemini model selection (embedding, answer, fallback, retries)

Date: 2026-09-24
Status: Accepted (user decision, D10-D13; D11/D12 amended 2026-09-24 to resolve the evaluation quota issue). D13 amended 2026-09-26 (RAG-003, OD-11: retry policy, throttle, error classification); see the last section.
Related: ADR-0003 D9 (EN + VI queries require a multilingual embedding model).

## Evidence (2026-09-24, free tier, this project's API key)
**Model availability.** `models.list()` via `google-genai` 1.75.0, then one real call per candidate. One call each; latencies are anecdotal, NOT evaluation data.

| Model | Result | Single-call time |
|---|---|---|
| `gemini-3.5-flash-lite` | ok | 0.79 s |
| `gemini-3.5-flash` | ok | 1.44 s |
| `gemini-3.6-flash` | ok | 2.08 s |
| `gemini-3.8-flash` | 503 UNAVAILABLE (high demand), ok on retry | 3.57 s |
| `gemini-3.7-flash` | 503, ok on retry | 13.99 s |
| `gemini-3.1-flash-lite` | ok | 4.98 s |
| `gemini-flash-latest` | 503 | - |
| `gemini-2.5-flash` | 404 "no longer available to new users" | - |
| `gemini-embedding-001` | ok; 3072 dims; input limit 2,048 tokens; a 4-text request returned 4 vectors | 0.57 s |
| `gemini-embedding-2` | ok; 3072 dims; input limit 8,192 tokens; a 4-text request returned 1 vector (texts combined) | 0.62 s |

**Cross-lingual sanity check (one example, not evidence of quality).** Cosine similarity of a query to a matching routing text vs an unrelated DI text.
- `embedding-001`: VI query 0.734 vs 0.516, EN query 0.838 vs 0.513.
- `embedding-2`: VI query 0.707 vs 0.536, EN query 0.872 vs 0.561.

**Free-tier rate limits.** Read by the user from the AI Studio rate-limit page. Limits apply per project and per model; RPD resets at midnight Pacific.

| Model | RPM | TPM | RPD |
|---|---|---|---|
| Gemini 3.5 Flash / 3.6 / 3.7 / 3.8 Flash | 5 | 250K | 20 |
| Gemini 3.5 Flash Lite / 3.1 Flash Lite | 15 | 250K | 500 |
| Gemini Embedding 1 / Embedding 2 | 100 | 30K | 1K |

Pricing page (https://ai.google.dev/gemini-api/docs/pricing): free-tier content may be used to improve Google products. The corpus is public documentation, so this is acceptable here.

## Decisions
**D10 Embedding model: `gemini-embedding-001`.**
- Reasons: multilingual, supports multi-text requests (quota-friendly), and its 2,048-token limit exceeds the 1,600-char chunks (ADR-0003 D3).
- Use task types `RETRIEVAL_DOCUMENT` for chunks and `RETRIEVAL_QUERY` for questions.
- Both experiment arms use the same model and settings.

**D11 Answer model (app and evaluation): `gemini-3.5-flash-lite`.** (Amended; originally `gemini-3.5-flash`.)
- Reasons: 500 RPD / 15 RPM fits a full evaluation run in one day. It was the fastest in the availability check (speed is a user priority). The app and the evaluation use the same model, so reported results describe the real system.
- Pinned by exact name in configuration, never hard-coded in code and never a `-latest` alias (aliases can change silently and break reproducibility).

**D12 Fallback: `gemini-3.5-flash`. Answer-quality judge: `gemini-3.5-flash-lite`.** (Amended; originally fallback + judge = `gemini-3.5-flash-lite`.)
- The fallback is used when D11 fails after retries; its 20 RPD is enough for occasional fallback use only.
- The judge shares D11's quota. Because the judge is the same model that wrote the answers (self-grading bias), a manual spot-check of a sample of judge verdicts is required and reported.
- Every answer records which model produced it, so fallback answers are visible in evaluation.
- Optional: an answer-model comparison on a subset of <= 20 questions answered by `gemini-3.5-flash` (fits one day's quota).

**D13 Transient errors.**
- On 503/429: retry with exponential backoff (e.g. 1 s, 2 s, 4 s; max attempts TBD), then fall back to D12. (Max attempts and the details are decided in the amendment below.)
- Latency reporting records retry count and fallback use separately; retried calls are not mixed into normal-call latency statistics.

## Consequences
- Model names live in configuration only (`infrastructure/llm/gemini/` reads them; core stays provider-free).
- Embedding the index: ~0.86 M chars after ADR-0003 dedup, very roughly 200-300 K tokens per arm (estimate, not measured). At 30K TPM that is about 10+ minutes per arm, so the embedder must batch and throttle to TPM. Whether a multi-text request counts as one request against RPD is not verified.
- A provider change (non-Gemini LLM) would require amending CLAUDE.md rules 2 and 6, `tech-stack.md` and a new ADR, and needs measured evidence (e.g. failure rate on a real evaluation run).

## Resolved issue: evaluation quota
Resolved by the D11/D12 amendment (option 2 below, extended: Flash Lite is also the app's answer model). History:
- `gemini-3.5-flash` allows 20 RPD. The accepted evaluation (>= 30 questions, EN + VI, 2 arms) needs roughly 120+ answer calls, i.e. about 6+ days of D11 quota per full run, before any re-runs.
- The judge (D12) shares the 500 RPD of Flash Lite with fallback answers.
- Options considered:
  1. Accept multi-day evaluation runs, with a resumable, checkpointed runner.
  2. Run full evaluations with `gemini-3.5-flash-lite` (500 RPD) and use `gemini-3.5-flash` for the interactive app plus a small comparison subset.
  3. Run the retrieval-only chunking metrics (embedding calls only) at full scale and answer generation on a subset.
  4. Enable paid tier.
- Budget per full run with the amendment: ~120 answers + ~120 judge calls ~= 240 of 500 Flash Lite RPD (estimate).

## Amendment 2026-09-26 (RAG-003): OD-11 retry policy, limits, error classification, accounting
Decided by the owner in the RAG-003 run addendum (2026-09-26); OD-11 is closed. Code: `infrastructure/llm/gemini/gemini_llm.py`; the retry, retry-after, quota-classification and key-redaction helpers moved out of the embedder into `infrastructure/gemini_retry.py`, which the embedder and the LLM adapter both use.

**D13 resolved: retry policy of the answer model (`gemini-3.5-flash-lite`).**
- Up to **3 attempts in total** (1 + 2 retries) on a per-minute 429, 503, timeouts and connection errors.
- Exponential backoff with jitter: the wait after attempt n is `1 s * 2^(n-1) + jitter` (jitter in [0, 1) s), or the server's retry-after (HTTP `Retry-After` or the `RetryInfo` delay) when that is longer. Any single wait is capped at **120 s** (the embedder's cap).
- Then the fallback model (`FALLBACK_MODEL`, `gemini-3.5-flash`) gets **one attempt**, never a retry. Its RPD is 20, so it is a safety net.
- A **daily-quota 429** (a per-day quota id in the error's `QuotaFailure`): no retries; straight to the single fallback attempt. If that also fails with a quota error, the quota error is raised.
- `ALLOW_FALLBACK` (default `true` for the app and the CLI). The evaluation runner sets it to `false`, so every answer and judgment comes from `gemini-3.5-flash-lite` (no mixed-model results); a case whose attempts all fail is recorded as an error and re-run later. With `ALLOW_FALLBACK=false` the fallback model is never called and the answer model's classified error is raised. An unrecognised value (e.g. `flase`) is a configuration error, not a silent `true`.

**Limits and throttle (config, `AnswerSettings`).** Read by the owner from AI Studio on 2026-09-26, free tier. Each model has its own client-side per-minute throttle, applied to every attempt (retries and the fallback call included).

| Model | RPM | TPM | RPD | Throttle |
|---|---|---|---|---|
| `gemini-3.5-flash-lite` (answer, judge) | 15 | 250K | 500 | 13 RPM |
| `gemini-3.5-flash` (fallback) | 5 | 250K | 20 | 4 RPM |

TPM and RPD are configuration for planning a run; the adapter enforces the request throttle only (13 requests a minute of a ~3K-token prompt cannot reach 250K TPM). One `GeminiLLM` instance shares its throttles across its calls; a second instance of the same model (e.g. a judge) would get its own window unless the throttles are shared explicitly.

**Error classification.** No `google.genai` or `httpx` exception leaves infrastructure. Provider and transport failures are wrapped into core `LLMError` subtypes, whose `kind` is the GUI's `AskQuestionError.kind`, 1:1:

| Core error | `kind` | Raised when |
|---|---|---|
| `LLMQuotaError` (`daily` flag) | `quota` | HTTP 429: the daily quota is used up, or the per-minute limit persisted through every attempt |
| `LLMUnavailableError` | `unavailable` | 5xx, timeout or connection error that persisted through every attempt |
| `LLMRequestError` | `other` | anything no retry can fix: 400/401/403/404, an unparsable reply, an unsupported URL |

`GenerationError` (unusable output: `MAX_TOKENS`, empty, not JSON) stays separate and maps to `other` in the GUI wiring; `ConfigurationError` and `RetrievalError` likewise.

**Choices inside the owner's rules (not spelled out in the addendum; the owner can veto them at 99-VERIFY).**
1. **Retryable statuses** are the embedder's set: 429, 500, 503, 504, plus timeouts and connection errors (`httpx.TimeoutException`, `NetworkError`, `RemoteProtocolError`, `TimeoutError`, `ConnectionError`). 500 and 504 go beyond the owner's list because the two adapters share one classifier.
2. **Errors no retry can fix** (400, 401, 403, 404, unparsable reply) are raised at once as `other`: no retry and no fallback, since the fallback would fail the same way and its daily quota is scarce.
3. **When both models fail,** the error raised describes the **answer model's** failure, with the fallback's failure named in its message; `__cause__` is the answer model's provider error. A daily-quota primary whose fallback returns 503 is therefore still a quota error (retrying will not help before the reset), and a 503 primary whose fallback is out of daily quota is still "unavailable" (transient).
4. **`retry_count`** counts retries on the answer model only (0 to 2). The fallback call is not a retry: it sets `fallback_used` and `model_used`. The latency report keeps its rule (D13): retried and fallback answers stay out of the normal-call statistics.
5. **Unusable output** (`GenerationError`) is not retried and does not trigger the fallback.
6. The client SDK's own retry is left off (no `retry_options`), so attempts are counted in one place.
7. The embedder keeps its owner-accepted rule (ADR-0005 amendment 2): it does **not** retry connection errors (indexing is resumable). What changed with the move is only that a connection error, or any other provider-side `httpx` exception, now becomes an `EmbeddingError` instead of escaping raw. Timeouts and 429/5xx are retried exactly as before; the existing embedder tests pass unchanged. The LLM adapter does retry connection errors, as ADR-0005 said RAG-003 would.

**Accounting (`LLMResponse`, copied into `AnswerResult.llm`).** `model_used`, `retry_count`, `fallback_used`; `prompt_tokens`, `output_tokens`, `thoughts_tokens` (None when the provider does not report them, never 0); `latency_ms` is the model time of the call that produced the answer; `retry_wait_ms` is the total time spent in backoff. `AnswerResult.latency_ms` gains `retry_wait` (backoff) and `throttle_wait` (client-side throttle) next to `generate` (the wall time of the whole call), so the latency report can separate model time from waiting. Both keys are absent when the retrieval gate answered without an LLM call. `throttle_wait` is an addition to the owner's list, needed because at 13 RPM a full run is throttled and would otherwise inflate `generate`.

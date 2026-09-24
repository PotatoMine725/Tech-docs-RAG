# ADR-0004 Gemini model selection (embedding, answer, fallback, retries)

Date: 2026-09-24
Status: Accepted (user decision, D10-D13; D11/D12 amended 2026-09-24 to resolve the evaluation quota issue). Implementation not started.
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
- On 503/429: retry with exponential backoff (e.g. 1 s, 2 s, 4 s; max attempts TBD), then fall back to D12.
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

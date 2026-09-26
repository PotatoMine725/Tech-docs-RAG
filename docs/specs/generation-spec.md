# Generation specification

Status: decided for RAG-002 (2026-09-26); resilience, accounting and CLI added by RAG-003 (2026-09-26). Code: `application/generation/`, `infrastructure/llm/gemini/gemini_llm.py`, `infrastructure/gemini_retry.py`, `composition.py`, `scripts/ask.py`.

## Known facts
- Questions may be in English or Vietnamese; the corpus is English (ADR-0003 D9).

## Requirements
- The answer MUST be in the question's language.
- The "insufficient information" message MUST be in the question's language.
- Answer model `gemini-3.5-flash-lite`; on repeated 503/429, retry with backoff then fall back to `gemini-3.5-flash`; each answer records the model used (ADR-0004). The retry policy (OD-11) is in the section "Resilience" below and in the ADR-0004 amendment of 2026-09-26.
- When the answer is insufficient, keep `missing_information` (what the documents don't cover). Optional related citations are allowed, but related content must not be presented as the answer (owner decision D2, 2026-09-24).

## Language
`application/common/language.py`: `detect_language(text)` = "vi" if the NFC-normalized text holds a Vietnamese-specific
letter (ă â đ ê ô ơ ư) or a tone-marked vowel, else "en". Limitations (tested): Vietnamese without diacritics → "en";
a word with a letter shared with other languages (e.g. "café") → "vi".

## OD-10 prompt (decided 2026-09-26, owner-approved before the live run)
- Template: `config/prompts/answer_v1.md`; the version string is the file name (`ANSWER_PROMPT_VERSION`, recorded in
  every `AnswerResult.prompt_version`). Prompts are never inlined in code. The file holds exactly the text sent.
- Current version: `answer_v2` (RAG-002 fix F1, 2026-09-26) = `answer_v1` + rule 4 "Wrap code, identifiers and
  expressions in backticks." so code indexers are not read as citation markers (citation-spec.md). `answer_v1.md` is
  kept unchanged; the first live dev answers were produced with it.
- Rule 2 is the owner's text (RAG-002 addendum 3). Two small additions, shown to and approved by the owner: rule 3 adds
  "and list every passage number you cite in "cited_passages""; rule 4 covers "answer" and "missing_information".
- Passages: numbered 1..k in rank order, each `[n] {document_name} — {heading path}` + newline + the link-stripped
  chunk body; blank line between passages. Placeholders `{answer_language}` (English | Vietnamese), `{passages}`,
  `{question}` are filled in one regex pass (braces in passages or questions are copied unchanged).
- JSON mode: `response_mime_type="application/json"` + `response_json_schema` (google-genai 1.75.0), schema
  `{"insufficient": bool, "answer": string, "cited_passages": [int], "missing_information": string}`, all required.
  Temperature 0.0, `max_output_tokens` 1024.

## Answer flow (`AnswerQuestion.ask`)
1. Detect the language; retrieve (retrieval-spec.md). Top-1 < threshold → gate answer (no LLM call).
2. Build the prompt; call the LLM; parse the JSON. Unusable output (not JSON, missing or mistyped key,
   `insufficient=false` with an empty answer, truncated at `MAX_TOKENS`, empty) raises `GenerationError` with the raw
   text; it is never turned into "insufficient".
3. `insufficient=true` → `answer` = localized message from `config/messages.json`, `insufficient_reason="llm"`,
   `missing_information` kept, citations = related content only (D2). Otherwise the answer text is shown with its
   markers resolved (citation-spec.md); a non-empty `missing_information` on a partial answer is kept too.
4. `latency_ms`: `embed_query`, `retrieve`, `generate` (wall time of the LLM call: model time, waits and failed attempts), `retry_wait` and `throttle_wait` (both from the LLM response; see Resilience), `total`. The three LLM keys are absent when the gate fired.

## Messages
`config/messages.json`: EN "The document collection does not contain enough information to answer this question.";
VI "Bộ tài liệu hiện có không chứa đủ thông tin để trả lời câu hỏi này."

## Resilience (RAG-003; ADR-0004 amendment 2026-09-26, OD-11)
Code: `infrastructure/llm/gemini/gemini_llm.py`; the shared retry helpers are in `infrastructure/gemini_retry.py`.
- **Attempts.** The answer model gets up to 3 attempts (`ANSWER_MAX_ATTEMPTS`) on a per-minute 429, a 500 / 502 / 503 / 504, a timeout or a connection error: exponential backoff (1 s, 2 s) plus jitter in [0, 1) s, or the server's retry-after when longer, each wait capped at 120 s.
- **Fallback.** Then `FALLBACK_MODEL` (`gemini-3.5-flash`) gets one attempt, with its own output budget `FALLBACK_MAX_OUTPUT_TOKENS` (default 2048; the answer model keeps 1024). A daily-quota 429 skips the retries and goes straight to it. `ALLOW_FALLBACK=false` (the evaluation runner's setting) never calls it. Errors no retry can fix (400/401/403/404, unparsable reply) raise at once, without the fallback. `GenerationError` (unusable output) is neither retried nor sent to the fallback. A `MAX_TOKENS` finish raises a `GenerationError` whose message names the model and the `max_output_tokens` it was sent with.
- **Throttle.** Each model has its own per-minute request throttle (answer model 13 RPM, fallback 4 RPM; provider limits 15 and 5). Every attempt passes it. TPM and RPD are configuration for run planning, not enforced by the adapter.
- **Errors.** No `google.genai` / `httpx` exception leaves infrastructure. The use case raises `LLMQuotaError` (kind `quota`, `daily` flag), `LLMUnavailableError` (`unavailable`) or `LLMRequestError` (`other`); `kind` is the GUI's `AskQuestionError.kind`. An LLM error is never turned into "insufficient". When both models fail, the error describes the answer model's failure and names the fallback's.
- **Accounting** (`LLMResponse`, reachable as `AnswerResult.llm`): `model_used`, `retry_count` (retries on the answer model; the fallback call is not a retry), `fallback_used`, `prompt_tokens`, `output_tokens`, `thoughts_tokens` (None when not reported), `latency_ms` (model time of the call that produced the answer), `retry_wait_ms`, `throttle_wait_ms`. Model time = `llm.latency_ms`; waiting = `latency_ms["retry_wait"]` + `latency_ms["throttle_wait"]`.
- **Limitations** (UNVERIFIED, not settled by any live call). In the smoke check (`validation/generation/smoke-2026-09-26.md`, one call, not evaluation data) `gemini-3.5-flash` took ~24 s and used 370 thinking tokens for an answer that `gemini-3.5-flash-lite` gave in 1-4 s; the flash-lite calls reported no `thoughts_token_count`. Whether thinking tokens count against `max_output_tokens` is not established (the installed SDK does not say). The adapter sets no `thinking_config`; the answer model's budget is 1024 and the fallback's is 2048 (`FALLBACK_MAX_OUTPUT_TOKENS`) so a thinking fallback is less likely to be cut off. A cut-off answer is reported as `GenerationError` (`MAX_TOKENS`), never as a partial answer. If the owner wants this settled, one owner-approved live call on `gemini-3.5-flash` with a small `max_output_tokens` can decide it (plan it for a later task's first live run).

## CLI (`scripts/ask.py`)
`python scripts/ask.py "question" [--arm A|B] [--json] [--gate-off]` prints the answer, numbered citations (document, heading path, excerpt), the insufficient flag and reason, `missing_information`, latency per stage, the model with retries and fallback, and the token counts. `--json` prints one JSON document (a failure is a JSON `error` object, see below). `--gate-off` disables the retrieval gate so a low-scoring question reaches the LLM: a diagnostic for checking the LLM's own "insufficient" answer, labelled in the output, never used by the evaluation runner. Exit codes: 0 answered, 2 provider failure (quota / unavailable / other), 3 unusable model output, 4 setup or retrieval failure. The key is read from the environment or `.env` and is never printed; a provider error body is saved to `data/logs/` with the key redacted.

### `--json` output
One JSON document on stdout. The keys below are exactly the keys of `result_to_dict` in `scripts/ask.py` (a nested key is written `parent.child`; `citations[]` is one list element); `tests/unit/test_ask_cli.py` fails when this table, the `--help` epilog, the module docstring and the code disagree. `llm_called`, `latency_ms`, `tokens` and `retrieval` are the accounting groups.

| Key | Type | Notes / when `null` |
|---|---|---|
| `question` | str |  |
| `arm` | str | "A" \| "B" |
| `language` | str | "en" \| "vi" |
| `answer` | str | the localized refusal message when insufficient |
| `insufficient` | bool |  |
| `insufficient_reason` | str \| null | "retrieval_gate" \| "llm"; null when answered |
| `missing_information` | str \| null | null when the model gave none (also when the gate refused) |
| `citations` | list | may be empty |
| `citations[].marker` | int | the [n] number in the answer |
| `citations[].document_name` | str |  |
| `citations[].location` | str | heading path, never a page number |
| `citations[].location_type` | str | "heading" \| "position" |
| `citations[].excerpt` | str | original English passage prefix, at most 300 characters |
| `citations[].source_id` | str |  |
| `citations[].chunk_id` | str |  |
| `citations[].source_url` | str | "" when the document has none |
| `citations[].related_only` | bool | true for every citation of an insufficient answer |
| `llm_called` | bool | false when the retrieval gate refused (no LLM request) |
| `model_used` | str \| null | null when llm_called is false |
| `retry_count` | int \| null | retries on the answer model; null when llm_called is false |
| `fallback_used` | bool \| null | null when llm_called is false |
| `tokens` | object |  |
| `tokens.prompt` | int \| null | null when llm_called is false or the provider did not report it |
| `tokens.output` | int \| null | same |
| `tokens.thoughts` | int \| null | same (flash-lite reports none) |
| `latency_ms` | object | stage -> ms (float): embed_query, retrieve, generate, retry_wait, throttle_wait, total; generate, retry_wait and throttle_wait are absent when the gate refused |
| `retrieval` | object |  |
| `retrieval.top1_score` | float | similarity of the best passage |
| `retrieval.threshold` | float \| null | null with --gate-off |
| `retrieval.gate_off` | bool |  |
| `retrieval.duplicates_dropped` | int |  |
| `prompt_version` | str |  |
| `dropped_markers` | list[int] | markers that pointed outside the passages |
| `uncited_sentences` | int | diagnostic count |

On failure `--json` prints `{"error": {"kind": str, "message": str}}` instead, with `kind` one of `quota`, `unavailable`, `other` (provider failures, exit 2), `generation` (unusable model output, exit 3), `setup` or `retrieval` (exit 4); the message has the API key redacted. Exit codes: 0 answered (an "insufficient" answer is still 0), 2 provider failure, 3 unusable model output, 4 setup or retrieval failure. Without `--json` the same error goes to stderr as `ERROR (kind): message`.

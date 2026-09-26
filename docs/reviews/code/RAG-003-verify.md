# RAG-003 verify (99-VERIFY)

Verifier session 2026-09-26, Windows, Python 3.13.3, branch `rag-003` at `6ca1ba0` (PR #14 into `dev`). **0 Gemini requests**, `.env` never opened, nothing merged. `OPENBLAS_NUM_THREADS=1` for every run; no pytest run was cut off, so no re-run was needed.
Scratch copies (`git archive dev` and `git archive rag-003`) lived in the session scratchpad; the repo tree was not edited.

## Verdict: ACCEPT WITH FIXES

The behaviour the owner asked for is implemented and tested: 3 attempts, backoff with jitter, retry-after capped at 120 s, daily-quota fast path, `ALLOW_FALLBACK`, no raw provider exception escaping, accounting on every path. Three mutations were caught. The two FAILs are small, and one of them (502) departs from the owner's own status list.

| | Count |
|---|---|
| PASS | every other row |
| FAIL | 3 (F1 502 not retried; F2 `--json` schema not documented; F3 boundary test does not cover 500 or 400) |
| UNVERIFIED | 1 (whether thinking tokens count against `max_output_tokens`; not decidable from the SDK, no live call allowed) |

## A. Acceptance / gate items (task prompt `08-RAG-003-resilience-cli-smoke.md`)

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | OD-11 asked, recorded as an ADR-0004 amendment | PASS | Amendment dated 2026-09-26 (`git diff dev...rag-003 -- docs/architecture/decisions/0004-*.md`, +42 lines); the owner decided it in the run addendum. |
| 2 | Adapter in `infrastructure/llm/gemini/` only, throttle from config, model names from config | PASS | `gemini_llm.py:60-77` (`build_throttles`), `config.py` `ModelLimits`; no model string in `src/` outside `config.py` (`git grep "gemini-3"` on `src/`). |
| 3 | Retry on 429/503/timeout/connection, wrapped into `LLMError` subtypes | PASS with F1 | `gemini_retry.py:16,24-42,125-149`. 502 is not retried (see OD-11 table). |
| 4 | Fallback; `model_used`, `retry_count`, `fallback_used`, token counts | PASS | `gemini_llm.py:134-218`; accounting section below. |
| 5 | CLI `scripts/ask.py "q" [--arm A\|B] [--json]` prints answer, numbered citations (doc, heading path, excerpt), insufficient flag, latency per stage, model, tokens | PASS | `ask.py --help` runs (output below); smoke steps a1/a2/c show every item. |
| 6 | Smoke: 1 EN + 1 VI answerable (not eval set) + 1 out-of-corpus, real output pasted | PASS | `validation/generation/smoke-2026-09-26.md`; questions Q-DEV-001 (en), Q-DEV-002 (vi), Q-DEV-005 (out of corpus) are `dev-v1.jsonl` rows (checked by id and text prefix). |
| 7 | Secret scan | PASS | see D. |
| 8 | Offline tests: 503-then-success, connection error then success, persistent connection error wrapped, fallback after N failures, token fields | PASS | `test_gemini_llm_resilience.py:94-135` (503 then success; `ConnectError`/`ReadTimeout` param), `:323` (persistent, all error types), `:164` (fallback after 3), `:390-403` (tokens). |

## Extra check 1. Scope: embedder behaviour unchanged

`git diff dev...rag-003 --stat`: 34 files, +3001 / -136. Source files: `config.py`, `composition.py`, `core/exceptions`, `core/interfaces/llm.py`, `gemini_retry.py` (new), `gemini_llm.py`, `gemini_embedder.py`, `answer_question.py`, `scripts/ask.py`, `scripts/generation/{dev_check,smoke_check}.py`. No `data/`, `corpus/`, GUI, ingestion or retrieval file changed.

- **Embedder diff** (`-86 / +20`): only the helper functions were moved to `gemini_retry.py` (the same code: `git diff` shows the deleted bodies match the new module line for line: `error_details`, `redact_key`, `raw_body`, `retry_after_s`, `daily_quota_id`, constants), and the `except` block now calls `classify_failure`. Retryable set `{429, 500, 503, 504}`, 1 s doubling backoff, 120 s cap, daily-quota `QuotaExhaustedError`, and the "first 429 body logged once" rule are unchanged. Connection errors (`ConnectError`, `ReadError`, `RemoteProtocolError`) become `EmbeddingError` at the first failure (`gemini_embedder.py:~145`, tests `test_connection_errors_are_wrapped_and_not_retried`). Not retried, as before.
- **Slightly wider than "connection errors" only** (informational, not a defect): other provider-side `httpx` errors (e.g. `UnsupportedProtocol`) and `UnknownApiResponseError` are now also wrapped in `EmbeddingError` instead of escaping raw. The ADR-0004 note 7 says so ("or any other provider-side httpx exception").
- **Proof nothing was weakened.** `git diff dev...rag-003 -- tests/` deleted lines (all four, of 3001 added): (1) `from ...exceptions import GenerationError` → the same import plus three more names; (2) `assert set(result.latency_ms) == {embed_query, retrieve, generate, total}` → the same equality with `retry_wait`, `throttle_wait` added (stricter: two new keys required); (3) `assert (prompt_tokens, output_tokens) == (120, 30)` → the same plus `thoughts_tokens == 5`; (4) `FORBIDDEN_CORE` gains `"httpx"`. No assertion was deleted or loosened.
- **RAG-001a tests re-run.** In a scratch copy of the branch I overwrote `test_gemini_embedder.py` with the **dev** version (the RAG-001a original) and ran it with the embedder cache and pipeline tests against the branch source: `48 passed`. The branch's own versions of the three files: `52 passed` (the 4 extra are the new connection-error tests). PASS.

## Extra check 2. OD-11 against the ADR-0004 amendment: one rule, one test

| Rule | Test (`tests/unit/infrastructure/test_gemini_llm_resilience.py`) | Result |
|---|---|---|
| 3 attempts in total | `:104` (`[503, 503]` then success = 3 calls), `:164` (3 failures then the fallback: calls `[P, P, P, F]`) | PASS; mutation M1 kills 9 tests |
| Backoff 1 s, 2 s doubling | `:104` (`sleeps == [1.0, 2.0]`) | PASS |
| Jitter added | `:113` (`jitter=0.5` → `[1.5, 2.5]`) | PASS |
| retry-after honoured when longer | `:138` (`retryDelay 17s` → sleep `[17.0]`) | PASS |
| retry-after capped at 120 s | `:145` (`36000s` → `[120.0, 120.0]`, `retry_wait_ms == 240000`) | PASS |
| Daily quota: no retry, 1 fallback attempt | `:184` (calls `[P, F]`, no sleep); `:193` (both daily: one call each, `daily=True`) | PASS; mutation M2 kills 3 tests |
| Fallback gets one attempt only | `:175` (fallback scripted to fail 5 times, only 1 call) | PASS |
| `ALLOW_FALLBACK=false` → fallback never called | `:251` (4 params: 503, 429 per-minute, ConnectError, 429 daily: `FALLBACK not in calls`), `:262` (via the environment variable) | PASS; mutation M3 kills 5 tests |
| 400 / 401 / 403 / 404: no retry, no fallback | `:279` (4 params: one call, no sleep, `fallback_attempted False`) | PASS |
| 500 / 503 / 504 / timeout / connection retried | `:130` (`ConnectError`, `ReadTimeout`, 503, 500, 429 per-minute) | PASS for these; **504 has no test of its own**; **502 is not retried** |
| **502 retried** | none | **FAIL (F1)** |

**F1 (502).** The owner's list (500/502/503/504) includes 502, but `RETRYABLE_STATUS = {429, 500, 503, 504}` (`gemini_retry.py:16`) leaves it out; the ADR amendment (choice 1) also lists the embedder's set without 502 and does not mention the omission. Probe run in the scratch copy with a script that calls the real adapter through the test fakes (`api_error(code)` × 5 on both models):

```
500 LLMUnavailableError unavailable ['primary','primary','primary','fallback'] sleeps [1.0, 2.0]
502 LLMUnavailableError unavailable ['primary','fallback']                      sleeps []
503 LLMUnavailableError unavailable ['primary','primary','primary','fallback'] sleeps [1.0, 2.0]
504 LLMUnavailableError unavailable ['primary','primary','primary','fallback'] sleeps [1.0, 2.0]
```

A 502 skips the retries and burns one of the fallback's 20 daily requests (with `ALLOW_FALLBACK=false` it would fail the case at once). Adding 502 to the shared set also changes the embedder (which today raises `EmbeddingError` on a 502); the fix prompt gives the choice.

## Extra check 3. Error boundary

- `grep -rnE "google\.genai|from google|import google|httpx" src scripts --include=*.py`, minus `src/.../infrastructure/`: **0 hits in `src/`**. Three hits in `scripts/`, all older than RAG-003 and not on the app path: `scripts/utilities/probe_embedding_quota.py:16-17`, `scripts/utilities/smoke_test.py:7` (standalone probes) and `scripts/ingestion/build_index.py:49` (logger names as strings). `git diff dev...rag-003 -- scripts/` adds none. The structure test forbids `google`, `httpx`, `chromadb`, `markitdown` in `core/` and `application/`, and the new `test_presentation_does_not_import_provider_libraries` covers the GUI. PASS.
- Parametrized proof: `test_no_raw_google_or_httpx_exception_escapes_and_the_kind_matches` (`:307-333`), 8 errors × fallback on/off = 16 cases: 429 per-minute, 429 daily, 503, `ConnectError`, `ReadTimeout`, `RemoteProtocolError`, `UnsupportedProtocol`, `UnknownApiResponseError`. Each asserts the exact type, that it is not an `APIError`/`httpx.HTTPError`/`TimeoutError`/`ConnectionError`, `error.model`, and `__cause__`. **The list you named has 500 and 400 too: neither is in this test.** 400 is covered by `:279` (raises `LLMRequestError`, kind `other`); 500 persistent is covered nowhere by an assertion on the error type (`:130` covers 500-then-success only). My probe above shows the behaviour is right (`LLMUnavailableError`). **F3, LOW: add 500 and 400 to the parametrized list.**
- `kind` maps 1:1: `test_the_llm_error_kinds_are_the_gui_kinds` (`{"quota","unavailable","other"}`), and `tests/presentation/desktop/test_llm_error_mapping.py` (73 lines, 4 tests) checks the contract GUI-001 will use: each `LLMError` kind string equals the GUI's `AskQuestionError` kind, and the view-model shows the right text for each. The `catch LLMError → AskQuestionError(error.kind)` wiring itself is GUI-001's job (ledger note). PASS.
- Both models fail → the answer model's error: `:213` (three cases: daily-quota primary + 503 fallback → `LLMQuotaError`; 503 primary + daily-quota fallback → `LLMUnavailableError`; 503 primary + 400 fallback → `LLMUnavailableError`), each with the fallback named in the message and `__cause__` the answer model's provider error. Documented: ADR-0004 amendment choice 3 and `generation-spec.md` "Resilience". PASS.
- A programming error is not swallowed: `:298` (`KeyError` propagates). PASS.

## Extra check 4. Mutations (scratch copy of `rag-003`; three of the executor's ten)

| Mutation | Edit | Suite run | Result |
|---|---|---|---|
| M1 retry count | `range(1, settings.max_attempts + 1)` → `range(1, settings.max_attempts)` in `gemini_llm.py` | resilience + retry tests | **9 failed**, 84 passed (e.g. `:104`, `:164`, `:175`, `:251[503]`, `:322`) |
| M2 daily-quota fast path | `retryable=code in RETRYABLE_STATUS and daily is None` → drop `and daily is None` in `gemini_retry.py` | same | **3 failed** (`test_daily_quota_skips_the_retries…`, `…on_both_models…`, `test_when_both_models_fail…`) |
| M3 `ALLOW_FALLBACK` guard | `settings.allow_fallback and settings.fallback_model` → `settings.fallback_model` in `gemini_llm.py` | same | **5 failed** (four `:251` params + `:262`) |

Each file was restored from `git show rag-003:<path>`. SHA-256 after restoration equals the repo blob's: `gemini_llm.py` `73798fdb…04e21e`, `gemini_retry.py` `8e2ebe15…c758d`, both identical before, after and in the repository. (My first M1 and M3 read was drowned by log lines in the grep; both were re-run with a stricter filter, the numbers above are from that re-run.) PASS.

## Extra check 5. Accounting

- Success path (`gemini_llm.py:187-218`): `model_used`, `retry_count`, `fallback_used`, `prompt/output/thoughts_tokens` (`getattr(..., None)`), `latency_ms` (the successful call's model time), `retry_wait_ms`, `throttle_wait_ms`. Failure path: the `LLMError` carries `model`, `retry_count`, `fallback_attempted`, `provider_body` (`_error`, `:240-245`). Gate path: `llm=None` and no LLM keys (`test_gate_refusal_has_no_llm_wait_keys`). Unreported tokens are `None`, not 0: `:398` (three params). Fallback answer carries the fallback call's tokens and latency: `:405`. Model latency excludes the backoff: `:413`. PASS.
- **`total ≥ generate + waits` is not the definition and does not need to be**: `generate` is the wall time of the whole `generate()` call, so it already contains `retry_wait` and `throttle_wait` (`answer_question.py:101` comment, `generation-spec.md` item 4). The invariant that holds is `total ≥ embed_query + retrieve + generate` and `generate ≥ model latency + retry_wait + throttle_wait`. `:435` and `:444` show the two waits are reported apart from model time. In the smoke file, all waits are 0 and the stage sums match the totals: a1 `0+314+4179 = 4493` vs total 4494; a2 `0+9+1902 = 1911` vs 1912; c `6+1312 = 1318` vs 1319 (1 ms is rounding). The gate refusal (b) has `embed_query 0, retrieve 12, total 12`. PASS. The waits > 0 case was never seen live (no 429/503 occurred); it is covered offline only.
- `AnswerResult.llm` copies the fields (`test_result_carries_the_llm_accounting_fields`). PASS.

## Extra check 6. Throttle

- 13 and 4 come from config: `config.py` `_model_limits("ANSWER", …, throttle_rpm=13)` / `("FALLBACK", …, throttle_rpm=4)`, overridable by `ANSWER_THROTTLE_RPM` / `FALLBACK_THROTTLE_RPM`, validated `1 ≤ throttle ≤ rpm`. `test_default_throttles_come_from_config_13_rpm…` (`:425`) shows 13 (and 4) calls fit the window and the next waits 60 s. PASS.
- Ledger 09a note (`docs/plans/task-ledger.md` row 09a): "The throttle is per `GeminiLLM` instance: the runner and the judge (09b) must share one instance or the same `throttles=` mapping, otherwise two 13-RPM windows can exceed the model's 15 RPM." PASS.
- **Is a shared throttle already possible?** Yes. `GeminiLLM.__init__` takes `throttles: Mapping[str, SlidingWindowThrottle] | None` (`gemini_llm.py:105,112`) and `build_throttles(settings)` is a public module function (`:60`). 09a builds the mapping once, passes the same object to the runner's and the judge's `GeminiLLM`, and no code change is needed. The mapping is keyed by model, so both instances share the flash-lite window. What 09a does **not** get for free: `requests` / `requests_by_model` are per instance, so a run-wide request count needs the sum over both instances. `composition.py` does not expose the sharing (it builds one `GeminiLLM` for `ask.py`), which is fine for the CLI.

## Extra check 7. Smoke file

- Requests: setup line "planned LLM requests: 4 … 0 embed"; totals "LLM requests: 4 of 5; embedding requests: 0"; per step `used 1, 2, 2 (b makes 0), 3 of 5`, and step d is the fourth (3 × flash-lite, 1 × flash). Ledger row and report say the same. PASS. This is the script's own count; I cannot check the provider's dashboard, so "no request beyond these" is trust in the script's counter (`llm.requests`), which the offline tests cover.
- Dev questions only: Q-DEV-001, Q-DEV-002, Q-DEV-005 (`dev-v1.jsonl`); firewall script (below) finds 0 of 36 eval texts and 0 eval ids in the file and in the added lines. PASS.
- Step c (gate off): `Insufficient information: yes (llm)`, `Missing information: The provided context does not contain information about …` (non-empty), answer text is the localized message. PASS.
- Step d: JSON valid (the file records "parsed and checked against the answer schema"; the raw text pasted parses and matches: `insufficient false`, `cited_passages [1]`), **`finish_reason STOP`, thoughts tokens 370** (prompt 1197, output 102), latency 23898 ms, `fallback_used=False` explained (direct call). PASS.

## Extra check 8. Fallback output budget (installed google-genai 1.75.0, read, not guessed)

- `types.py:5867`: `GenerateContentConfig.max_output_tokens` "Maximum number of tokens that can be generated in the response." The SDK says nothing about thinking tokens here.
- `types.py:7811` `thoughts_token_count`: "The number of tokens that were part of the model's generated 'thoughts' output"; `types.py:7825` `total_token_count` = `prompt_token_count + candidates_token_count + tool_use_prompt_token_count + thoughts_token_count`. So the SDK reports thoughts **separately from** `candidates_token_count` (our `output_tokens` excludes them: smoke d `output 102`, `thoughts 370`).
- **Whether thoughts are charged against `max_output_tokens` is decided by the API server, not by the SDK, so it is UNVERIFIED here.** Only field docs exist locally, and no live call is allowed. The smoke run does not decide it either: 102 + 370 = 472 < 1024.
- Adapter: `gemini_llm.py:136` builds `GenerateContentConfig(temperature, max_output_tokens[, response_mime_type, response_json_schema])` and nothing else. **It sets no `thinking_config`** (`grep -rn thinking src` finds only a comment). `max_output_tokens` is the `LLMRequest` default **1024** (`core/interfaces/llm.py:10`), and `answer_question.py:100` does not override it.
- Risk: the fallback thinks (370 tokens on a 102-token answer). If the server counts thoughts inside the 1024, a long Vietnamese answer (flash-lite used 301 output tokens for Q-DEV-002; the fallback would add its own thinking) could hit `MAX_TOKENS`; the adapter then raises `GenerationError` (`UNUSABLE_FINISH`), which is neither retried nor sent to a further model, so the one rare fallback call would be lost. The answer model is not affected in practice (flash-lite reported no thoughts). It is a low-frequency path (the fallback is only reached after failures, and eval runs turn it off), so it is not a blocker. Suggested handling is in the fix prompt (item 4): decide and record it, do not change the code speculatively.

## Extra check 9. CLI

- `ask.py --help` works: `usage: ask.py [-h] [--arm {A,B}] [--json] [--gate-off] question`; `--gate-off  DIAGNOSTIC ONLY: disable the retrieval gate`. PASS.
- `--gate-off` labelled diagnostic: in `--help`, in the module docstring (`ask.py:12-13`), in the output (`*** GATE OFF: diagnostic run … Never used for evaluation. ***`, smoke step c) and in the JSON (`"gate_off": true`). Ledger 09a note forbids it in the runner. PASS.
- **`--json` schema documented: FAIL (F2).** The only field list is `result_to_dict` (`ask.py:55`) and the test at `tests/unit/test_ask_cli.py:88`; `generation-spec.md` says "prints one JSON document (a failure is a JSON `error` object)" and nothing more; `--help` and the docstring do not list the fields. `grep -rn llm_called docs` finds nothing. Anyone who wants to parse it (09a might, GUI-001 will not) reads the source. The smoke file contains two real examples, which helps but is not documentation.
- Key never printed: `grep -nE "GEMINI_API_KEY|get_gemini_api_key|api_key|redact"` on `ask.py`, `smoke_check.py`, `composition.py`: only `redact_key(...)` around the provider body and the error message, and a docstring sentence. The key is read in exactly one place (`gemini_llm.py:125`, into the `genai.Client`); errors, provider bodies and logs go through `redact_key`; tests `:345`, `:360` prove redaction, including a key echoed inside a quota id. PASS.

## B. Tests

- `.venv/Scripts/python.exe -m pytest -q` on the branch: **`546 passed, 1 deselected in 8.59s`**.
- `dev` (scratch archive): `383 passed, 1 skipped, 1 deselected`; the branch in the same scratch archive: `545 passed, 1 skipped, 1 deselected`. The one skip is `tests/unit/test_config.py` "git history not available" (an archive has no `.git`); it runs in the real tree. **Dev 383 → branch 546 (+163).**
- Structure test (`tests/unit/test_project_structure.py`) is in those totals; it passes.
- Read the new tests: they assert calls made (`models.calls == [...]`), sleeps (`clock.sleeps == [...]`), exact error type, `__cause__`, tokens and latency values, not just that code runs. The mutations above show they can fail. Weak spots: no test of a `504` on its own, none for a persistent `500` error type (F3), and no live evidence of a real 429/503 on the LLM path (the report says so).

## C. Claims vs reality

Traced to files or my own runs: 546 tests; 4 LLM + 0 embed requests (smoke file); token and latency numbers (smoke file, arithmetic above); 13/4 RPM (config, tests); the mutation claims (I re-applied three of them); "the embedder's accepted behaviour unchanged" (dev's embedder tests pass unchanged against the branch source); "no eval text in added lines" (my own script: 0 of 36 eval texts, 0 eval ids). The report's statement "1 eval-style pattern in added lines, in the prompt log" is a different measure (id/name patterns) that I did not reproduce; my check found 0 eval ids in the added lines, so nothing contradicts it. The 09a "~144 requests per full 2-arm run" figure is the owner's, copied from the addendum, not measured here. No untraceable number found.

## D. Project rules

- Layers: structure test passes; no `chromadb|google|httpx|PySide6` in `core/` or `application/`.
- Model names in config only: `gemini-3.5-flash-lite` / `gemini-3.5-flash` appear as defaults in `config.py`; adapter and CLI read them from settings; no `-latest`.
- Secrets: `git grep -E "AIza[0-9A-Za-z_-]{35}" rag-003` → no hit in tracked files (also none in `validation/`, `data/`, `docs/`); only `.env.example` is tracked (placeholders); `.env` was never opened.
- Corpus and eval: no `corpus/` or `data/` file in the diff; `eval-v1.jsonl` sha256 starts `3436870e…`, `dev-v1.jsonl` `37d349e5…`, both equal to the values recorded at `eval-freeze-v1` (`739676fb`); excluded docs are not referenced by any change.
- Eval firewall: my script read `eval-v1.jsonl` in memory only and compared it with every added line of `git diff dev...rag-003` and with the smoke file: 0 of 36 question texts, 0 eval ids (nothing printed).
- Git: work is on `rag-003` from `dev`, PR #14 into `dev`; nothing merged.

## E. Scope

- Beyond the prompt: `throttle_wait` (declared in the ledger note and ADR), the `ALLOW_FALLBACK` setting and strict bool parsing (from the owner's addendum), `ask.py --gate-off` (addendum), the `smoke_check.py` script with quota guards (needed for item 4), `presentation` import test. All were declared in the report or the addendum.
- Decisions the executor took inside the owner's rules and listed for the owner to confirm (ADR note "Choices", ledger row): 500/504 retried; 400/401/403/404 raise at once without fallback; both-fail raises the answer model's error; `throttle_wait` key. I found nothing undeclared. **The owner's decision on 502 is open (F1).**

## F. Quality spot-read (`generate`, `_attempt`, `classify_failure`)

- `generate` (`gemini_llm.py:134-170`): the attempt loop is right (`attempt == max_attempts` breaks; the wait is computed after the failure and before the next call; nothing sleeps before the fallback). The fallback runs only for `kind != "other"`, so a 400 never reaches it. `failed.failure` is always set when the loop ends without a return (the loop runs at least once because config requires `max_attempts ≥ 1`).
- `_attempt` catches only `PROVIDER_ERRORS`, so a `KeyError` from a bug propagates (tested). The raw error is kept in `error` and becomes `__cause__`.
- `classify_failure` (`gemini_retry.py:125`): `code >= 500` → `unavailable`, so a 502 is classified `unavailable` (the fallback is tried) but is not retryable (F1). A daily-quota 429 is `quota`, not retryable, and skips to the fallback. No silent swallowing: `GenerationError` for unusable output is separate and never becomes "insufficient" (`test_an_llm_error_reaches_the_caller_and_is_never_turned_into_insufficient`).
- Minor: `_error` puts `failure.daily_quota_id` (from the provider body) in the message and redacts the whole message. Good.

## G. Explain-it-back

The bullets in the report's "Explain it back" are correct against the code (retry then fallback numbers and reasons; wrapping at the infrastructure edge with `kind` = the GUI kind; one shared retry module; accounting fields and why `None` not 0; the smoke design). One statement needs a qualifier: "3 attempts … on transient errors" does not include a 502, which the owner's status list does (F1). Nothing else to correct.

## Fix prompt (run in a new session on branch `rag-003`; keep the offline suite green; 0 Gemini requests)

1. **502 retried (F1).** File: `src/knowledge_assistant/infrastructure/gemini_retry.py:16` (and `docs/architecture/decisions/0004-…` amendment choice 1, `docs/specs/generation-spec.md` "Attempts"). Expected: a 502 is retried like a 503 on the answer model (3 attempts, then one fallback). **Decision for the owner (ask, do not choose silently):** (a) add 502 to `RETRYABLE_STATUS`, which also makes the embedder retry a 502 (change to accepted RAG-001a behaviour: record it in the ADR-0005 amendment) or (b) give the LLM adapter its own set, so the embedder stays as accepted. Proof: a parametrized test over `(500, 502, 503, 504)` asserting `calls == [P, P, P, F]` and `sleeps == [1.0, 2.0]`; run the RAG-001a embedder tests unchanged.
2. **Document the `--json` schema (F2).** File: `docs/specs/generation-spec.md` "CLI" (and the `scripts/ask.py` module docstring): list every key of `result_to_dict` with type and when it is `null`, the `error` object shape (`{"error": {"kind", "message"}}`) and the exit codes. Proof: a test that compares the documented key set with `result_to_dict(...)` keys (so the doc cannot drift), plus a grep that the doc names `llm_called`, `latency_ms`, `tokens`, `retrieval`.
3. **Complete the error-boundary list (F3).** File: `tests/unit/infrastructure/test_gemini_llm_resilience.py:307`. Add `api_error(500)` → `LLMUnavailableError` and a 400 `errors.ClientError` → `LLMRequestError` to the parametrized cases, and a 504 case to `:130`. Proof: pytest shows the new ids passing; mutate `code >= 500` → `code > 500` in a scratch copy and see the 500/504 cases fail.
4. **Record the thinking-token question (UNVERIFIED).** File: `docs/specs/generation-spec.md` "Resilience" / ledger row 08 note. Expected: state that whether `max_output_tokens` includes thinking tokens is not settled by the installed SDK, that the adapter sets no `thinking_config`, and that `max_output_tokens` is 1024 by default. Do not change the code speculatively. If the owner wants it settled, one owner-approved live call on `gemini-3.5-flash` with a small `max_output_tokens` can decide it; add it to the smoke plan of a later task or to 09a's first live run.

# EVAL-003a execution report: resumable evaluation runner (generation only, no scoring)

Task: `agents/prompts/09a-EVAL-003a-runner.md` with the owner's addendum of 2026-09-27 (verbatim in
[the prompt log](../../prompt-log/claude-code/EVAL-003a.md)). Branch `eval-003a` from `dev` (`dcdea66`), in a separate git
worktree; PR into `dev`, not merged. Status: done, awaiting `99-VERIFY`. Date: 2026-09-27. Tool: Claude Code, Claude Sonnet 5.

## Summary

- **What exists:** `scripts/evaluation/run_eval.py` (wiring and CLI guards) over the application use case `RunEvaluation`
  (`application/evaluation/run_evaluation.py`), the record schema (`records.py`), the frozen-hash check (`integrity.py`), a
  `RecordStore` port and its JSONL implementation (crash-safe append, redaction on every line).
- **Tests:** `569 passed, 1 deselected` on `dev` before, `653 passed, 1 deselected` after (84 new; per-file counts in "Tests"). 20 mutations of the new code (M1-M19, with M3 also run as M3b), all killed, files restored byte for byte.
- **Live dry run (dev split, arm A, 3 cases per mode):** retrieval mode 3 ok, 0 LLM requests, 0 embedding requests; full mode
  3 ok, **2 LLM requests** (the third case was answered by the retrieval gate), **0 embedding requests**, 0 provider errors;
  re-running the finished run spent nothing. **No eval-split run of any kind** (not even `--estimate-only`).
- **Addendum items:** the addendum has items 0-6. Items 1-6 are done; item 0 (branch from `dev`, standard git block, PR into `dev`, do not
  merge, stop for `99-VERIFY`) is done with the PR named in the header. The places where I chose between readings are listed in
  "Design decisions" (10 items).
- **Not seen live:** a real 429 or 5xx. The capture of their raw bodies is proven offline only (see Unverified).
- Frozen question files unchanged: `sha256sum` equals `docs/snapshots/evaluation/eval-v1.md`, and `git diff dcdea66 --` on both
  files and the snapshot is empty.

## Scope, entry condition and environment

- **Entry:** ledger row 08 (RAG-003) is `verified`; row 09a was `not started`. Branch `eval-003a` from `dev` at `dcdea66`.
- **Separate worktree, and a slip.** The main checkout was on `dev` with another session's uncommitted GUI work in it (files
  under `presentation/desktop/`, `tests/presentation/`, `tests/unit/test_project_structure.py`, `docs/screenshots/`, plus the
  GitNexus statistics in `AGENTS.md` and `CLAUDE.md`). My first `git switch -c eval-003a dev` ran in that checkout and moved its
  HEAD for a few seconds; I saw the other files in the `git switch` output, switched back (`git switch dev`, status unchanged),
  deleted the empty branch (`dcdea66`, no commits) and created a worktree instead
  (`.claude/worktrees/eval-003a`). I touched none of the other session's files and staged only paths of this task.
- Worktree runs use the main checkout's `.venv` by absolute path; live runs read the main checkout's git-ignored data through
  `CHROMA_PATH` and `EMBEDDING_CACHE_PATH`, and the key is found by `find_dotenv()` walking up to the main `.env` (never printed
  or copied). `OPENBLAS_NUM_THREADS=1` was set for every command; one heavy process at a time.
- Import check: `knowledge_assistant.__file__` resolved inside the worktree.

## Files

New:

| File | What |
|---|---|
| `src/knowledge_assistant/core/interfaces/record_store.py` | `RecordStore` port: manifest, records, error log |
| `src/knowledge_assistant/application/evaluation/records.py` | the record schema, `assemble`, `chunk_entry`, `citation_entry`, `latest_records` |
| `src/knowledge_assistant/application/evaluation/run_evaluation.py` | `RunEvaluation`, `RunConfig`, `RunEnvironment`, `RunSummary`, `RunEstimate` |
| `src/knowledge_assistant/application/evaluation/integrity.py` | frozen-file hashes vs `eval-v1.md` |
| `src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py` | `run.json`, `records.jsonl`, `errors.jsonl` |
| `src/knowledge_assistant/infrastructure/llm/gemini/provider_error_log.py` | `FirstProviderErrors`: first 429 and first 5xx body |
| `scripts/evaluation/run_eval.py` | CLI: integrity, config, estimate, run, resume command |
| `tests/eval_fakes.py` | shared doubles (made-up cases, scripted retriever/LLM, in-memory store) |
| 8 test files | see "Tests" |
| `data/evaluation/results/20260927-dev-A-{retrieval,full}-05680f9/` | the two dry-run outputs (dev split; **not evaluation results**) |

Modified (existing code). GitNexus impact analysis ran for `GeminiLLM` and `required_point_quotes` (both LOW); the new classes
appended to `core/exceptions/__init__.py` and the docstring in `latency.py` edit no existing symbol:

| File | Change |
|---|---|
| `core/exceptions/__init__.py` | 4 new classes: `EvaluationError`, `IntegrityError`, `RunConfigMismatch`, `ModelPurityError` |
| `infrastructure/llm/gemini/gemini_llm.py` | +6 lines: optional constructor argument `on_provider_error(model, failure)`, called for every failed attempt; unset by default, no behaviour change (the RAG-003 resilience suite runs unchanged: 487 lines, all pass) |
| `application/evaluation/metrics/retrieval.py` | `_case_label(case)`: `required_point_quotes` error messages accept a run record (`case_id`) as well as a dataset case (`id`) |
| `application/evaluation/metrics/latency.py` | module docstring only: the record shape is now fixed by this task |

Docs: prompt log, this report, `AI_WORKLOG.md`, `docs/plans/task-ledger.md` (rows 09a and 09b), `docs/plans/master-plan.md` and
`docs/plans/epics/EPIC-05-evaluation.md` (one status line each).

## Record schema

One JSON line per case x arm x mode; every field is always present (`tuple(record) == RECORD_FIELDS`); what was not generated is
null or an empty list. Ground truth is a deep copy of the dataset fields, never modified (`evidence[].supports` included: the
metrics read it).

| Group | Fields |
|---|---|
| identity | `run_id`, `case_id`, `arm`, `mode`, `status` (`ok` / `error`) |
| failure | `error`, `error_kind` (`quota` / `unavailable` / `other`), `error_model`, `error_type` (class name) |
| ground truth (13) | `question`, `language`, `parallel_group_id`, `answerable`, `expected_answer`, `answer_points`, `expected_sources`, `acceptable_alternate_sources`, `evidence`, `acceptable_variations`, `must_not_claim`, `citation_criteria`, `tags` |
| retrieval | `llm_called`, `retrieved[]` = `rank`, `chunk_id`, `source_id`, `heading_path` (string), `char_start`, `char_end`, `score`, **`display_text`**, **`passage_hash`**, **`duplicate_chunk_ids`**; **`top1_score`**, **`gate_fired`**, **`duplicates_dropped`** |
| answer | `answer`, `insufficient`, `insufficient_reason`, `missing_information`, `citations[]` = `marker`, `chunk_id`, `source_id`, `heading_path`; `dropped_markers`, `uncited_sentences` |
| accounting | `latency_ms` = `embed_query`, `retrieve`, `generate`, **`retry_wait`**, **`throttle_wait`**, `total`; `model_used`, `retry_count`, `fallback_used`, `prompt_tokens`, `output_tokens`, **`thoughts_tokens`**, `prompt_version` |
| time | `started_at`, `finished_at` |

Bold = added by the addendum or by a decision below. The brief's five columns are `question`, `expected_answer`,
`expected_sources`, `answer` and (later, EVAL-003b) `result`.

## Design decisions and deviations

1. **`display_text` in every retrieved chunk** (the prompt's schema lists no text). Without it `evidence_hit` cannot run on a
   record, and the addendum forbids adapter hacks. Cost: about 10 KB per record (3 records = 30 KB), so a 72-record eval run is
   about 0.7 MB. The judge (09b) also gets the passages the model saw without re-joining files.
2. **`llm_called` is an extra field, and no-LLM records have `retry_count` 0 and `fallback_used` false.** `latency.is_clean` reads
   `retry_count == 0 and not fallback_used`; a `None` (what `ask.py` prints for a gated answer) would file every gated record
   under "retried or fallback". `latency_ms` is always a full dict with null stages.
3. **`run_id` default also has the split:** `<YYYYMMDD>-<split>-<arm>-<mode>-<sha7>` (the prompt: without the split). A dev dry run
   and the eval run of EVAL-004 on the same day and commit would otherwise share an id and the second would stop on a settings
   mismatch. **Only an explicit `--run-id` resumes.** If the default id already exists the script refuses and prints the id to
   pass; nothing is resumed silently. This is my reading of "passing an existing `--run-id` resumes it".
4. **The LLM budget counts requests, not cases:** `retry_count + 1` per answered case, `retry_count + 1` (+1 if a fallback was
   attempted) per `LLMError`, 1 per `GenerationError` (retries inside that call are not visible, so this is a lower bound), 0 for
   a gate answer. `--max-llm-calls` (default 200) is per invocation and is checked before each case, so a case can exceed it by
   its own retries. In the dry run `run.json` records both the runner's count (2) and the adapter's HTTP counter (2).
5. **Quota stop.** An `LLMError` of kind `quota` and an embedding `QuotaExhaustedError` both stop the run after recording that one
   case as `error`; the other cases get no record, so a resume runs them. `unavailable` / `other` (also `GenerationError`,
   `RetrievalError`, other `EmbeddingError`) are recorded and the run goes on. Any other exception is a bug and aborts. A
   per-minute 429 that persisted through the adapter's three attempts is also kind `quota` and also stops the run.
6. **First 429/5xx body: a hook on `GeminiLLM`, not log scraping.** The adapter logs only the first 429 (never a 5xx) and a
   failed attempt that a retry fixes never reaches the caller as an error, so `LLMError.provider_body` alone would miss the case
   the owner asked about. `FirstProviderErrors` keeps the first 429 and the first 5xx of a process in `errors.jsonl` (status, model,
   reason, retry-after, daily quota id, body with the key redacted). A resumed invocation keeps its own first. Transport errors have
   no body and are not kept. Every failed case also stores its own `provider_body` in `errors.jsonl`.
7. **Estimate.** The LLM is called for every case the gate does not stop, answerable or not, so the estimate counts non-gated
   cases: a minimum (cached questions that pass the gate) and a maximum (every case not known to be gated), because the gate is
   known only for cached questions (retrieved for real at no API cost). It prints uncached query embeddings (one request each,
   once; the other arm reuses them), LLM requests, minutes at the throttle rate, and the share of RPD (500). `--estimate-only`
   prints it and stops. The estimate also refuses a run whose recorded settings differ: a finished run has nothing to run, so
   `run()` is never reached (a defect found by a CLI test, see below).
8. **Model purity.** `RunConfig` refuses `allow_fallback=True`; the script forces `replace(get_answer_settings(),
   allow_fallback=False)` whatever `ALLOW_FALLBACK` says and records that same settings object in `run.json`. After each answer the
   runner checks `fallback_used` and `model_used == answer_model`; a violation is written to `errors.jsonl` (with the answer text),
   is **not** written to `records.jsonl`, and raises `ModelPurityError` (exit 3). The check is skipped when the gate answered
   (`llm is None`). Because `AnswerQuestion` parses the JSON before returning, an unusable answer from another model would be a
   `GenerationError` (recorded as an error), not a purity abort.
9. **Resume compares settings, not git state.** Compared: arm, mode, split, answer and fallback model, `allow_fallback`, embedding
   model and dimension, throttle RPM, threshold, prompt version **and prompt file SHA-256**, top-k, over-fetch, freeze tag and its
   commit, and both question-file hashes. Not compared: git commit, dirty flag, timestamps (each invocation records its own). `git_dirty`
   means tracked files differ from HEAD.
10. **`required_point_quotes` was edited** (EVAL-003b-pre code, verified): its three error messages read `case['id']`, a run
    record has `case_id`. GitNexus impact: LOW, 0 callers besides tests. A test failed with `KeyError: 'id'` first, then the fix.

Smaller points: `records.jsonl` is append-only, so a retried case leaves its error line; `latest_records()` returns the last line
per `(case_id, arm, mode)` and is the one loader (resume and tests use it, 09b must too). Only newline-terminated lines are records:
a torn tail from a killed process is ignored on read and cut off on the next append. A complete line that is not JSON raises. The
script sets `OPENBLAS_NUM_THREADS=1` if unset (a Windows memory failure at numpy import was seen in RAG-003). The script loads the
`.env` with `find_dotenv()`, so a worktree inside the repo finds the repo's file.

## Tests (offline, fakes; all case ids and questions are made up)

| File | Tests | What it proves |
|---|---|---|
| `tests/unit/application/test_run_evaluation.py` | 32 | 5-case full run, every field; ground truth copied; extra fields; gate answer; retrieval mode never calls the LLM; **crash after case 3 then resume (cases 1-3 not regenerated, LLM calls counted)**; error retried, ok line wins; **`max_llm_calls` 2 stops after 2**; budget counts requests; gate answers cost nothing; quota (LLM and embedding) stops without marking the rest; other errors continue; purity (fallback and other model); gate/LLM disagreement aborts; **config mismatch on resume aborts** (also in `estimate`); new commit allowed; config validation; progress lines; estimate |
| `tests/unit/application/test_eval_runner_feeds_metrics.py` | 6 | records written by the runner and read back from disk go into `summarize_latency`, `RankedChunk.from_record`, `required_point_quotes`, `evidence_hit_at_k`, `section_hit_at_k`, `source_hit_at_k`, `slot_fraction_at_k`, `reciprocal_rank` and `map_result` **without an adapter**; a gate-answered record lands in the main latency table |
| `tests/unit/test_run_eval_cli.py` | 16 | **hash mismatch aborts** (either file, before any service opens); missing tag; another split's case refused; default run id; existing default run not resumed; `--cases`; `--estimate-only`; resume command printed and usable; quota stop + resume command; settings mismatch; exit codes; Ctrl-C; **fallback forced off even with `ALLOW_FALLBACK=true`**; the real `open_services` builds the throttles once and shares the mapping |
| `tests/unit/infrastructure/test_jsonl_record_store.py` | 9 | flush per line, UTF-8 and `\n`, torn tail, corrupt line, redaction, atomic manifest, non-finite refused |
| `tests/unit/application/test_eval_records.py` | 8 | schema fields and order, verbatim ground truth, defaults not shared, `chunk_entry`, `latest_records` |
| `tests/unit/application/test_eval_integrity.py` | 7 | mismatch names the file and both hashes; the repository snapshot holds the owner's hashes (`3436870e…2937`, `37d349e5…21d6`); the repository files match it |
| `tests/unit/infrastructure/test_provider_error_log.py` | 5 | hook sees every failed attempt; first 429 and first 5xx only; a retried 429 is still saved through the real adapter; key redacted |
| `tests/unit/test_eval_arm_b_reuses_query_embeddings.py` | 1 | real `CachingEmbedder` + `Retriever` + `RunEvaluation`: arm A sends 4 questions to the provider, arm B sends 0 (4 cache hits) |

**What was seen failing first and what was not** (no red run was staged afterwards):
- Seen failing before the code existed (collection error: module or class missing): `test_jsonl_record_store.py`,
  `test_eval_integrity.py`, `test_eval_records.py`, `test_run_evaluation.py`, `test_provider_error_log.py`, `test_run_eval_cli.py`. Then
  all 29 tests of `test_run_evaluation.py` passed on the first run of the implementation. Because a first-run pass proves little, I ran
  the mutations below.
- **Written after the code they test:** `test_eval_runner_feeds_metrics.py` (first run: 5 passed, 1 failed with `KeyError: 'id'`, then
  the `required_point_quotes` fix; covered by mutations M5 and M12) and `test_eval_arm_b_reuses_query_embeddings.py` (first run failed on
  my own wrong expectation of the hit counter, the core assertion passed; no mutation applies, it tests the existing `CachingEmbedder`
  through the runner). So "test first" holds for six of the eight files, not for these two.
- Seen failing for a behavioural reason: `required_point_quotes` on a record (`KeyError: 'id'`); the estimate on a finished run with
  other settings (`DID NOT RAISE`, found through a failing CLI test).
- Added after the code and seen only passing, then covered by a mutation: the threshold-boundary test (M15), the gate/LLM
  disagreement test (M18), the Ctrl-C test (M19).

### Mutation proofs

Twenty mutations (M1-M19; M3 is also run in a second variant, M3b). Each edits one committed file, runs the named test files (`-x`),
and restores the file; `sha256` before and after are equal in every case. Harness kept in the session scratchpad, not committed.

| # | Mutation | Result |
|---|---|---|
| M1 | resume no longer skips ok cases | killed: crash-resume test |
| M2 | quota error no longer stops the run | killed: quota test |
| M3 / M3b | purity ignores `fallback_used` / ignores the model name | killed: both purity parameters |
| M4 | budget counts cases, not requests | killed: budget test |
| M5 | no-LLM records get `retry_count` None | killed: latency feed test |
| M6 | store stops redacting | killed: redaction test |
| M7 | torn tail kept on append | killed: torn-tail test |
| M8 | resume ignores different settings | killed: settings-mismatch test |
| M9 | integrity never compares | killed: integrity test |
| M10 | adapter never calls the hook | killed: hook test |
| M11 | script does not force the fallback off | killed: CLI dev-run test (`ALLOW_FALLBACK` default is true) |
| M12 | retrieved chunks lose `display_text` | killed: metrics feed test |
| M13 | existing default run resumed silently | killed: CLI test |
| M14 | embedding quota is a plain error | killed: embedding-quota test |
| M15 | gate uses `<=` instead of `<` | killed: boundary test |
| M16 | LLM budget not checked | killed: `max_llm_calls` test |
| M17 | error case not retried | killed: retry test |
| M18 | runner/answerer gate cross-check removed | killed: disagreement test |
| M19 | Ctrl-C not handled by the script | killed (pytest exit 2: the escaped `KeyboardInterrupt` interrupted the session) |

## Commands run (real output)

Environment: `D:\Code\Python\Knowledge assistant\.venv\Scripts\python.exe` by absolute path, from the worktree root.

| Step | Command | Result |
|---|---|---|
| Baseline | `pytest -q` (worktree at `dcdea66`) | `569 passed, 1 deselected` |
| After milestone 1-2 (`fe91d95`) | `pytest -q` | `628 passed, 1 deselected` |
| After milestone 3-4 (`c4e4ccc`) | `pytest -q` | `650 passed, 1 deselected` |
| Final | `pytest -q` | `653 passed, 1 deselected` (= 569 + 84; `--collect-only` counts 653 selected, 1 deselected) |
| Structure and config tests | `pytest tests/unit/test_project_structure.py tests/unit/test_config.py` | pass (no `knowledge_assistant.infrastructure` text in `application/`, no model name outside `config.py`) |
| Frozen hashes | `sha256sum` on both question files | `3436870e…2937`, `37d349e5…21d6` = snapshot; `git diff dcdea66 --` empty |

**A slip with a live test.** To "confirm the gemini test stays deselected" I ran `pytest -m gemini`, which *selects* it. It failed at
once: the worktree has no `.env` and the shell had no `GEMINI_API_KEY`, so `GeminiEmbedder` raised `ConfigurationError("GEMINI_API_KEY
is not set")` before any client or network call (`gemini_embedder.py:110-112`). **0 requests were sent.** It left an empty git-ignored
`data/cache/live-tests.sqlite` in the worktree, which I deleted. The deselection is shown by `1 deselected` in every default run.

## Live dry run (dev split, arm A, cases Q-DEV-001, Q-DEV-002, Q-DEV-005)

Worktree clean at `05680f9` (`git_dirty: false`). Environment for the live commands only:
`CHROMA_PATH` and `EMBEDDING_CACHE_PATH` pointing at the main checkout's data; `OPENBLAS_NUM_THREADS=1`.

1. `run_eval.py --arm A --mode full --split dev --cases Q-DEV-001,Q-DEV-002,Q-DEV-005 --estimate-only`: 0 uncached embeddings, LLM
   requests 2 to 2 (the gate stops 1 known case), at least 0.2 min at 13 RPM, up to 2 of 500 requests per day (0.4 %). Spent nothing.
2. **Retrieval mode** (`--mode retrieval`): `[1/3] Q-DEV-001 en ok 0.1s`, `[2/3] Q-DEV-002 vi ok 0.0s`, `[3/3] Q-DEV-005 en ok 0.0s`; 3 ok;
   **LLM requests 0; embedding requests 0** (cache hits 3, misses 0); `gate_fired` true only for Q-DEV-005 (top-1 0.6741 < 0.686).
3. **Full mode** (`--mode full --max-llm-calls 3`): `[1/3] Q-DEV-001 en ok 2.6s`, `[2/3] Q-DEV-002 vi ok 1.7s`, `[3/3] Q-DEV-005 en ok 0.0s`;
   3 ok; **LLM requests 2** (`llm_http_requests` 2, all `gemini-3.5-flash-lite`); **embedding requests 0** (cache hits 6 = 3 for the
   estimate's retrieval and 3 for the run, misses 0); 0 provider errors, so `errors.jsonl` was not created.
4. **Resume:** the same command with `--run-id 20260927-dev-A-full-05680f9`: "3 already ok, 0 to run", "nothing to run", exit 0,
   `records.jsonl` still 3 lines, 0 requests.

Inspected by hand (`run.json` config: `answer_model` `gemini-3.5-flash-lite`, `allow_fallback` false, `throttle_rpm` 13, `threshold` 0.686,
`prompt_version` `answer_v2`, `top_k` 5, `overfetch` 10, `freeze_tag` `eval-freeze-v1` -> commit `739676f…`, both question-file
hashes, `git_dirty` false; invocation entry with counts and the embedding and HTTP request counters):
- Q-DEV-001: answered `[1]` with one citation (`07:header-1600:0006`, "C# classes > Static classes"), 1197 prompt / 72 output tokens,
  `thoughts_tokens` null (the answer model reports none, as RAG-003 saw), `retry_count` 0, `fallback_used` false, `generate` 2566 ms.
- Q-DEV-002 (Vietnamese): answered with two citations (`16:…:0002`, `04:…:0003`), 2038 / 255 tokens, `generate` 1716 ms.
- Q-DEV-005: `gate_fired` true, `insufficient_reason` `retrieval_gate`, `llm_called` false, `model_used` null, `retry_count` 0,
  `fallback_used` false, `generate`, `retry_wait` and `throttle_wait` null, `total` 2.9 ms; the five retrieved chunks are kept.
- Real records fed to the 09b-pre functions: `summarize_latency` main table 3 records, retried 0, `generate` n = 2 (the gate answer is
  clean, its missing stage skipped); retrieval-mode records: main 3, `generate` n = 0; `evidence_hit_at_k` = 1 for both answered
  cases; `map_result` for the gate case = `correct_refusal`, and the two answered cases raise `JudgeVerdictMissing` as designed.

### One record, pasted

Real record 1 of `data/evaluation/results/20260927-dev-A-full-05680f9/records.jsonl` (Q-DEV-001, a dev question). **Only the
`display_text` values are shortened here** (marked with the length in the file) and `passage_hash` is cut to 16 characters; every
other value is as written.

```json
{
  "run_id": "20260927-dev-A-full-05680f9",
  "case_id": "Q-DEV-001",
  "arm": "A",
  "mode": "full",
  "status": "ok",
  "error": null,
  "error_kind": null,
  "error_model": null,
  "error_type": null,
  "question": "What is a static class in C#, and can another class inherit from it?",
  "language": "en",
  "parallel_group_id": null,
  "answerable": true,
  "expected_answer": "A static class can't be instantiated and contains only static members. A static class is implicitly sealed, so you can't derive from it.",
  "answer_points": [
    {"id": "P1", "text": "A static class can't be instantiated and contains only static members.", "required": true},
    {"id": "P2", "text": "A static class is implicitly sealed, so you can't derive from it.", "required": true}
  ],
  "expected_sources": [{"source_id": "07", "heading_path": "C# classes > Static classes", "slot": "S1"}],
  "acceptable_alternate_sources": [],
  "evidence": [
    {"source_id": "07", "heading_path": "C# classes > Static classes", "quote": "A `static` class can't be instantiated and contains only static members.", "supports": ["P1"]},
    {"source_id": "07", "heading_path": "C# classes > Static classes", "quote": "A static class is implicitly sealed. You can't derive from it or instantiate it.", "supports": ["P2"]}
  ],
  "acceptable_variations": [],
  "must_not_claim": ["Static classes can be inherited."],
  "citation_criteria": ["The cited chunk is from #07 'Static classes'."],
  "tags": {"difficulty": "easy", "cognitive_level": "recall", "size_class": "medium", "failure_mode": "none", "scope": "single-source"},
  "llm_called": true,
  "retrieved": [
    {"rank": 1, "chunk_id": "07:header-1600:0006", "source_id": "07", "heading_path": "C# classes > Static classes", "char_start": 5209, "char_end": 5896, "score": 0.7359527945518494, "display_text": "## Static classes  A `static` class can't be instantiated an... [687 chars in the file]", "passage_hash": "deb0e8b7d83f55d4...", "duplicate_chunk_ids": []},
    {"rank": 2, "chunk_id": "07:header-1600:0008", "source_id": "07", "heading_path": "C# classes > Inheritance", "char_start": 6984, "char_end": 7625, "score": 0.6867058873176575, "display_text": "## Inheritance  Classes support *inheritance*. You can defin... [641 chars in the file]", "passage_hash": "398b46121f24152a...", "duplicate_chunk_ids": []},
    {"rank": 3, "chunk_id": "07:header-1600:0001", "source_id": "07", "heading_path": "C# classes > When to use classes", "char_start": 944, "char_end": 1485, "score": 0.6655963063240051, "display_text": "## When to use classes  Use a class when:  - The type has co... [541 chars in the file]", "passage_hash": "52dd4aeab1c14f36...", "duplicate_chunk_ids": []},
    {"rank": 4, "chunk_id": "07:header-1600:0000", "source_id": "07", "heading_path": "C# classes", "char_start": 0, "char_end": 942, "score": 0.6616770625114441, "display_text": "# C# classes  Tip  **New to developing software?** Start wit... [942 chars in the file]", "passage_hash": "a2d91498acdf8313...", "duplicate_chunk_ids": []},
    {"rank": 5, "chunk_id": "20:header-1600:0007", "source_id": "20", "heading_path": "A tour of the C# language > Familiar C# features", "char_start": 7925, "char_end": 9446, "score": 0.6482065916061401, "display_text": "that interface must provide. You can also define generic typ... [1521 chars in the file]", "passage_hash": "897c550f2c807058...", "duplicate_chunk_ids": []}
  ],
  "top1_score": 0.7359527945518494,
  "gate_fired": false,
  "duplicates_dropped": 0,
  "answer": "A `static` class cannot be instantiated and contains only static members [1]. It is implicitly sealed, which means you cannot derive from it [1].",
  "insufficient": false,
  "insufficient_reason": null,
  "missing_information": null,
  "citations": [{"marker": 1, "chunk_id": "07:header-1600:0006", "source_id": "07", "heading_path": "C# classes > Static classes"}],
  "dropped_markers": [],
  "uncited_sentences": 0,
  "latency_ms": {"embed_query": 0.08470000011584489, "retrieve": 1.9949999996242695, "generate": 2566.2959999999657, "retry_wait": 0.0, "throttle_wait": 0.0, "total": 2568.5049000003346},
  "model_used": "gemini-3.5-flash-lite",
  "retry_count": 0,
  "fallback_used": false,
  "prompt_tokens": 1197,
  "output_tokens": 72,
  "thoughts_tokens": null,
  "prompt_version": "answer_v2",
  "started_at": "2026-09-27T00:49:15.827+00:00",
  "finished_at": "2026-09-27T00:49:18.396+00:00"
}
```

(The pasted block was reflowed to one line per short object for readability; the file holds one JSON object per line.)

## Quota accounting for this task

- LLM requests: **2** (full-mode dry run, `gemini-3.5-flash-lite`); 0 in retrieval mode, 0 in the estimate and the resume. Fallback model: 0.
- Embedding requests: **0** (every dev query was cached from RAG-003's smoke run).
- HTTP 429: 0; 5xx: 0. Other use of the same key today by other sessions is not counted here.

## Eval firewall

Script kept in the scratchpad (not committed); it reads the frozen eval question file in memory only and prints counts and locations,
never a question text. Scope: every file this branch changed or added since `dcdea66` (tracked diff plus untracked files, including
the two result folders, the prompt log and this report).

- **0 of the 36 eval question texts** in any of those files (whole-file scan, whitespace collapsed on both sides).
- **0** `Q-EVAL-n` and **0** `BP-EVAL-n` ids in added lines.
- The eval file name (`eval-v1`) appears in added lines, and only as a file name or a hash label: the runner's own paths
  (`run_eval.py`: the split-to-file map, the snapshot path), `integrity.py` (its docstring and the snapshot table it parses), the
  tests' made-up mini project and `run.json` (which lists both file hashes by name), plus the prompt log, this report and the ledger
  and worklog lines. No eval case id and no eval question text. Final scan (after all docs but this paragraph, 30 files = 23
  tracked changed or added + 7 untracked): **35 lines** with `eval-v1`, in `run.json` x2 (1 each: the hash list), `EPIC-05-evaluation.md`
  (1: the status line I extended), the prompt log (3), this report (3), `run_eval.py` (3), `integrity.py` (4), `tests/eval_fakes.py` (1),
  `test_eval_integrity.py` (13), `test_run_evaluation.py` (1), `test_run_eval_cli.py` (4).
- The dry run used dev cases only (`Q-DEV-*`); the script refuses a case whose `split` differs from `--split`, and no eval-split
  command was run, `--estimate-only` included.
- Secret scan over the same 30 files: **0** matches for the `AIza` + 35-character shape, **0** for the configured key and **0** for its 12-character prefix (the key was read in memory from the main `.env` and never printed).

## GitNexus

- Impact analysis before editing existing symbols (upstream): `GeminiLLM` **LOW** (1 importer, its package `__init__`, 0 processes),
  `required_point_quotes` **LOW** (0 callers besides tests). No HIGH or CRITICAL. The other changes are new files.
- `detect_changes` was run **once**, before the first commit (`fe91d95`), with `scope: compare`, `base_ref: dev`. The index
  `Tech-docs-RAG` is registered for the main checkout, not this worktree, so it returned 30 changed symbols in 20 files, **all from the
  other session's uncommitted work in the main checkout** (GUI files, `AGENTS.md`, `CLAUDE.md`, docs) and none of mine. It was **not
  re-run** before `c4e4ccc` (which edited `GeminiLLM`) or any later commit, for the same reason. The scope check of every commit was
  `git diff --name-status`, as in EVAL-003b-pre: it lists only the files of the "Files" section (added files, and the four modified
  files named there), and no file of the other session appears. The index is stale (`dcdea66`); I did not run `npx gitnexus analyze`,
  which would rewrite `AGENTS.md` and `CLAUDE.md` in the main checkout.

## Unverified / open

- **No real 429 or 5xx was seen** (0 provider errors in the dry run), so RAG-003's open question ("no real 429/503 seen on the LLM
  path; is the daily-quota detection right?") is **still open**. The capture path is proven offline with the real adapter against a fake
  client that raises SDK errors, not against a real response body. The first real one will land in `errors.jsonl`.
- The eval-scale estimate (36 uncached embeddings, at most 36 LLM requests per arm) is the formula's result on paper; `--estimate-only`
  on the eval split was deliberately not run.
- Retry, backoff and throttle waits were never exercised live (`retry_wait` and `throttle_wait` are 0.0 in the dry run); `thoughts_tokens`
  is null for the answer model, so the RAG-003 question about thinking tokens and `max_output_tokens` is unchanged.
- Arm B reusing arm A's query vectors is proven offline only (`test_eval_arm_b_reuses_query_embeddings.py`); the live dry run was arm A
  only, as instructed.
- `GenerationError` costs are counted as 1 request; retries inside that call are not visible to the runner.
- Two runs of the same command at different commits get different default ids (the sha is part of the id); resuming after a commit
  needs the explicit `--run-id`, which the printed resume command contains.
- Windows console: the script reconfigures stdout and stderr to UTF-8 when run as a script; the tests do not cover a real console.
- **Throttle sharing is in-process only.** `Services.throttles` is one mapping per process. A judge (09b) that runs as a separate process
  while a runner process is still live has its own 13-RPM window, and together they can exceed the model's 15 RPM. Run them one after the
  other, or drive the judge in the same process with `Services.throttles`.
- **Committed dev dry-run results.** I committed the two folders under `data/evaluation/results/` as evidence for the verifier; they are
  dev cases, not evaluation results. Keep or delete is the owner's choice (also asked in the PR). Records carry no `split` field, so
  EVAL-003c must read `run.json` (`config.split`) and must not glob every run directory blindly.
- Commit `4e7912d` (the Ctrl-C test) has no Co-Authored-By line; it is pushed, so history was not rewritten.

## Deviations from the prompt

- Default `run_id` has the split (decision 3); records carry `display_text`, `llm_called`, `error_type`, `retry_wait`, `throttle_wait`
  (decisions 1, 2); the budget counts requests (decision 4); `--estimate-only` and Ctrl-C handling were added; `run.json` holds one entry
  per invocation. `agents/prompts/09a-*.md` itself was not edited.

## Explain it back

- **Why generation and judging are separate, and the file is append-only.** A paid answer is written and fsynced before the next case
  starts, and a rerun skips every case whose latest line is `ok`. So a crash, a quota stop or a judge fix never costs a second answer.
  The alternative, one script that answers and judges, would re-spend quota every time the judge changes.
- **Why the budget counts requests and stops before each case, and why a quota error stops instead of marking the rest as errors.** The
  daily quota is counted in HTTP requests, retries included, so counting cases would under-count exactly when the API is unhealthy. A
  daily 429 fails every later case the same way; recording them as errors would only add noise and bogus retries, so the runner records
  the one case that hit it, stops, and prints the resume command.
- **Why a record holds ground truth verbatim plus the retrieved text.** The metric functions already exist and read `evidence[].supports`,
  `answer_points[].required` and `display_text`; the record has the same shape, so a test can hand a record from disk straight to them.
  No adapter means no second place where the two shapes can drift apart.
- **Why the adapter got a hook instead of the runner parsing logs.** The 429 that a retry fixes never reaches the caller, and the
  adapter never logs a 5xx body, so only an observer inside the retry loop sees every failed attempt. It is optional, unset by default,
  and the evidence matters because the daily-quota detection was written from the documented error shape and never checked on a real body.
- **Why a run refuses to mix models or settings.** If the fallback model answers even a few cases, arm A and arm B are no longer measured
  with the same model, and a changed threshold, prompt or model inside one run makes its numbers meaningless. So the fallback is off by
  construction (config validation, the script forces it, `run.json` records it), a record that still came from another model stops the
  run and is kept out of `records.jsonl`, and a resume must match the recorded settings, the prompt file's hash and both question-file
  hashes included. The git commit is not compared, because it changes with every fix; each invocation records its own.

## Lines for the owner (not applied; `agents/prompts/` and the specs are yours)

`agents/prompts/CHANGELOG.md`, new row:

```
| 2026-09-27 | `09a-EVAL-003a-runner.md` (owner addendum, run in the session) | Extra record fields (top1_score, gate_fired, duplicates_dropped, passage_hash + duplicate_chunk_ids, thoughts_tokens, retry/throttle wait, error_kind, error_model); integrity check of both frozen files + tag in run.json; full mode forces allow_fallback=false and a model-purity abort; build_throttles once; estimate before a run, --max-llm-calls 200, quota stop with resume command, first 429/5xx body saved; runner records feed the EVAL-003b-pre functions as they are; no eval-split run. | Owner decisions after RAG-003 and EVAL-003b-pre | Owner (2026-09-27) | see EVAL-003a report |
```

Ledger row 09b: the "latency record shape" and "`RankedChunk` adapter" items are resolved here (applied in the ledger by this task);
09b proper only has the refusal-check JSON key left. For EVAL-004: pass `--run-id` explicitly when resuming across commits.

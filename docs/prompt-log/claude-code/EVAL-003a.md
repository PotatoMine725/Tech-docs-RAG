# EVAL-003a prompt log

Date: 2026-09-27 · Tool: Claude Code (CLI), Claude Sonnet 5 · Effort: xhigh

## Owner invocation (chat, verbatim)

```text
Run agents/prompts/09a-EVAL-003a-runner.md (EVAL-003a) with this addendum; it overrides the prompt where they differ.
Also read ledger row 09a (owner notes + notes from RAG-003) and the EVAL-003b-pre report.

0. Branch eval-003a from dev (dcdea66). Standard git block, PR into dev, do not merge, stop for 99-VERIFY.
   OPENBLAS_NUM_THREADS=1. One heavy process at a time.
1. Extra record fields:
   - top1_score, gate_fired (bool), duplicates_dropped, and per retrieved chunk: passage_hash + duplicate_chunk_ids.
   - thoughts_tokens; latency_ms retry_wait and throttle_wait.
   - error_kind (quota|unavailable|other) + error_model on failures.
   - The latency record shape must match what the EVAL-003b-pre latency functions expect. Resolve 09b's open item
     "latency record shape" here and add a test that feeds a runner record into those functions.
     Do the same for the retrieval metric functions (a runner record → metrics, no adapter hacks).
2. Integrity:
   - Check both question files against the hashes in eval-v1.md (eval 3436870e…2937, dev 37d349e5…21d6) and record the tag eval-freeze-v1 in run.json.
   - Record in run.json: answer model, allow_fallback=false, throttle RPM, threshold, prompt version (answer_v2), top_k, over-fetch.
3. Model purity:
   - Full mode forces allow_fallback=False.
   - A record with fallback_used=True or model_used ≠ the answer model is a bug: assert and abort the run.
   - Build the throttles ONCE (build_throttles()) and pass them in, so the judge (09b) can share them.
4. Quota:
   - Before a run, print an estimate: uncached query embeddings (eval questions are not cached yet → up to 36 once;
     arm B reuses them), LLM requests (answerable, non-gated cases), and the time at 13 RPM. Compare it with RPD 500.
   - Default --max-llm-calls 200.
   - LLMError kind=quota → stop the run cleanly (don't mark the remaining cases as errors) and print the resume command.
   - kind=unavailable/other → record the error and continue.
   - Save the FIRST 429/5xx raw body (key redacted) to errors.jsonl. This is evidence for RAG-003's open question.
5. No eval-split runs at all in this task (neither mode). The live dry run uses ≤ 3 dev cases per mode, arm A only:
   ≤ 3 LLM requests, and 0 embed requests expected (dev queries are cached; if not, report it).
6. Report docs/reports/execution/EVAL-003a.md with one pasted record and "Explain it back". Ledger row 09a, AI_WORKLOG.
   Eval firewall grep.
```

## Task prompt (`agents/prompts/09a-EVAL-003a-runner.md`, verbatim at the time of the run)

````text
# EVAL-003a — Resumable evaluation runner (generation only, no scoring)

Read `agents/prompts/_common.md` first and follow it.
Read: `evaluation-spec.md`, `docs/specs/evaluation-dataset-design.md`, `docs/snapshots/evaluation/eval-v1.md`, RAG-003 report.
Entry: RAG-003 done (G3). Design principle: **generating answers and judging them are separate steps**, so a judge fix never forces paid answers to be regenerated.

## Record schema (one JSON line per case × arm × mode) — `application/evaluation/records.py`
```
run_id, case_id, arm ("A"|"B"), mode ("retrieval"|"full"), status ("ok"|"error"), error (str|null),
# copied from the frozen dataset (ground truth — never modified)
question, language, parallel_group_id, answerable (bool), expected_answer, answer_points [{id, text, required}], expected_sources [{source_id, heading_path, slot}], acceptable_alternate_sources [{source_id, heading_path, slot}], evidence [{source_id, heading_path, quote}], acceptable_variations, must_not_claim, citation_criteria, tags {difficulty, cognitive_level, size_class, failure_mode, scope}
# (schema = evaluation-dataset-design.md §18; the evidence slots are needed for the D1 hit rule — owner 2026-09-24, REORIENT-001 C3)
# generated
retrieved: [{rank, chunk_id, source_id, heading_path, char_start, char_end, score}],
answer, insufficient, insufficient_reason, missing_information (owner decision D2, 2026-09-24), citations: [{marker, chunk_id, source_id, heading_path}], dropped_markers, uncited_sentences,
latency_ms {embed_query, retrieve, generate, total}, model_used, retry_count, fallback_used, prompt_tokens, output_tokens,
prompt_version, started_at, finished_at
```
`retrieval` mode fills only the retrieval fields (no LLM call). Field names for the brief's 5 columns must be obvious: `question`, `expected_answer`, `expected_sources`, `answer`, and `result` (added later by EVAL-003b).

## Do
1. `scripts/evaluation/run_eval.py --arm A|B --mode retrieval|full --split eval|dev [--run-id ID] [--max-llm-calls N] [--cases ID,ID]`
   - **Integrity check first:** SHA-256 of the question file must equal the value in `docs/snapshots/evaluation/eval-v1.md`; mismatch → abort with a clear message.
   - Output `data/evaluation/results/<run_id>/`: `run.json` (git commit, dirty flag, tag, question-file hash, arm, mode, all model names, embedding dim, top-k, threshold, prompt version, start/end), `records.jsonl` (append-only, flushed per record), `errors.jsonl`.
   - `run_id` default: `{YYYYMMDD}-{arm}-{mode}-{git short sha}`; passing an existing `--run-id` **resumes** it: skip (case, arm, mode) already `ok`; retry `error` ones.
   - Refuses to resume if `run.json` config differs from the current config (prevents mixing settings in one run).
   - Quota guard: `--max-llm-calls` stops cleanly after N LLM calls and prints how to resume.
   - Query embeddings come from the shared cache, so arm B re-uses arm A's query vectors (verify: second arm reports 0 embedding API requests).
   - Progress line per case: `[12/36] EV-012 vi ok 2.1s`.
2. Application use case `RunEvaluation` (depends on `AnswerQuestion`, `Retriever` and a `RecordStore` interface); the script only wires infrastructure.
3. Tests (offline, fakes):
   - full run over 5 fake cases writes 5 `ok` records with every schema field present;
   - crash after case 3 (fake raises) → resume → exactly 5 records, cases 1–3 not re-generated (count fake LLM calls);
   - hash mismatch aborts; config mismatch on resume aborts;
   - `--max-llm-calls 2` stops after 2;
   - retrieval mode never calls the LLM.
4. Live dry run (≤ 3 dev cases, `--split dev`) for each mode; inspect the JSON by hand; paste one record into the execution report.

## Do not
Score, judge or summarize anything (EVAL-003b/c). Run the eval split in full mode (EVAL-004).
````

## Shared rules (`agents/prompts/_common.md`)

Followed as written; the "When done" steps are the checklist of the execution report.

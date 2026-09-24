# EVAL-003a — Resumable evaluation runner (generation only, no scoring)

Read `agents/prompts/_common.md` first and follow it.
Read: `evaluation-spec.md`, `docs/specs/evaluation-dataset-design.md`, `docs/snapshots/evaluation/eval-v1.md`, RAG-003 report.
Entry: RAG-003 done (G3). Design principle: **generating answers and judging them are separate steps**, so a judge fix never forces paid answers to be regenerated.

## Record schema (one JSON line per case × arm × mode) — `application/evaluation/records.py`
```
run_id, case_id, arm ("A"|"B"), mode ("retrieval"|"full"), status ("ok"|"error"), error (str|null),
# copied from the frozen dataset (ground truth — never modified)
question, language, parallel_group_id, answerable (bool), expected_answer, expected_source_ids, expected_heading_paths, evidence_quotes, tags {difficulty, cognitive_level, size_class, failure_mode, scope}
# generated
retrieved: [{rank, chunk_id, source_id, heading_path, char_start, char_end, score}],
answer, insufficient, insufficient_reason, citations: [{marker, chunk_id, source_id, heading_path}], dropped_markers, uncited_sentences,
latency_ms {embed_query, retrieve, generate, total}, model_used, retry_count, fallback_used, prompt_tokens, output_tokens,
prompt_version, started_at, finished_at
```
`retrieval` mode fills only the retrieval fields (no LLM call). Field names for the brief's 5 columns must be obvious: `question`, `expected_answer`, `expected_source_ids`, `answer`, and `result` (added later by EVAL-003b).

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

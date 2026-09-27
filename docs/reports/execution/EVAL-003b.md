# EVAL-003b execution report: metrics audit, duplicate rule, LLM judge, scoring

Task: `agents/prompts/09b-EVAL-003b-metrics-and-judge.md` with the owner's addendum of 2026-09-27 (verbatim in
[the prompt log](../../prompt-log/claude-code/EVAL-003b.md)); the addendum overrides the prompt where they differ. Branch
`eval-003b` from `dev` (`7db105b`) in a separate git worktree; PR into `dev`, not merged. Status: done, awaiting
`99-VERIFY`. Date: 2026-09-27. Tool: Claude Code, Claude Opus 5.5.

## Summary

- **Audit, not redo.** The EVAL-003b-pre code (§1 retrieval metrics, expected spans, §3 mapping, §4 latency) was audited
  against the prompt and the owner decisions. One change, test first: the owner's new **duplicate overlap rule**. Every
  other audited item is unchanged (table below).
- **Duplicate rule, scope decided by the owner during the task: section level only.** Source metrics use the kept
  chunk's own document; the addendum's "span/source" wording was a mistake (owner, 2026-09-27). Count of changed values:
  - Real records: **0** values changed. The committed dev dry-run records hold no duplicates, and no eval-split records exist.
  - Simulated on the chunk files (not a retrieval result): only the **2** doc-12/13 cases (Q-EVAL-003, 004) on Arm A, as the
    owner expected. Arm B has no duplicate groups.
  - My first implementation also applied the rule at source level. That gave a bound of 6 (+ Q-EVAL-022, 023, 027, 032),
    and I asked the owner (§ Duplicate rule). EVAL-004 reports the actual count.
- **Judge.** `application/evaluation/judge.py`, `config/prompts/judge_v1.md` (two sections: answer check and refusal
  check) and `scripts/evaluation/judge_run.py`.
  - Settings: `JUDGE_MODEL` = `gemini-3.5-flash-lite` in config, temperature 0, fallback off, 13 RPM.
  - Parsing is strict. Any failure becomes `judge_error` and is never guessed.
  - A judgement from another model is rejected.
  - Cache key: (case, arm, sha256(answer), prompt version).
- **Scoring.** `application/evaluation/scoring.py` holds the pure per-record scores and summaries: answer, refusal and
  citation (OD-12: span check and judge support check, separately), the breakdowns, judge latency and cost.
  `config/pricing.json` cites the Gemini pricing page (flash-lite $0.30 / $2.50 per 1M tokens; the other two models are null).
- **Tests.** 90 new offline tests. Full suite: **775 passed, 1 deselected** (dev `7db105b` measured: 685). All **13 mutations
  killed**: the refusal-check row, the duplicate rule (off, and wrongly applied at source level), the two `from_record`
  guards, the per-point evidence rule, each of the 4 cache-key components, the cost per-question formula, and the
  runner-error listing.
- **Live** (dev dry-run records): **2 judge requests** (Q-DEV-001 EN, Q-DEV-002 VI; both ok, `gemini-3.5-flash-lite`,
  0 retries). A re-run spent **0**. **0 embedding requests.** The committed runs contain **no refusal-check record**
  (Q-DEV-005 is a bare retrieval-gate refusal, labelled `correct_refusal` without a call), so no refusal check ran live.
  No eval-split record was created.

## Scope, entry condition, environment

- Entry: ledger row 09a (EVAL-003a) is `verified` (re-verify of `792b691` ACCEPT). Row 09b was `not started`, with the
  EVAL-003b-pre pre-work `verified`.
- Worktree `.claude/worktrees/eval-003b`, created with `git worktree add -b eval-003b ... 7db105b`. The main checkout was on
  `gui-001` with uncommitted `AGENTS.md` and `CLAUDE.md` edits from another session, which I did not touch.
- The worktree's commands used the main checkout's `.venv` python by absolute path with `PYTHONPATH=src` and
  `OPENBLAS_NUM_THREADS=1`, one heavy process at a time.
- For the live calls, `find_dotenv()` found the main `.env`. The key was never printed. `judge_run.py` opens no embedder and
  no vector store, so no `CHROMA_PATH` was needed.

## Audit of the EVAL-003b-pre work (addendum item 1)

| Item | Checked against | Verdict | Change |
|---|---|---|---|
| Expected spans (`expected-spans-v1.json`, 36 cases, all variants, per slot, role tags) | §1, D1, ADR-0003 D8 | OK. `test_every_answerable_case_has_a_non_empty_span_in_every_slot` still passes; frozen hashes unchanged | none |
| source/section hit@1/3/5, lenient and strict, slot fraction, MRR lenient/strict/source | §1, "headline = lenient, strict next to it" | OK | **duplicate rule added** (see below; failing test first) |
| evidence_hit@k per required point (all-of points, any-of quotes, optional ignored), content-level; any-quote and `evidence_hit_via_alternate_only` diagnostics | owner 2026-09-26 (supersedes §1 "any chunk contains the evidence quote") | OK; mutation M3 still killed | none (the duplicate rule does not touch it: it is a text check) |
| §3 mapping incl. D2 rows | §3 table, D2 | OK. The refusal check reads `JudgeVerdict.presents_related_as_answer`; that name is now also the judge's JSON key (addendum 3) | none (mutation M1 killed) |
| Latency summary (nearest rank, clean vs retried/fallback) | §4, EVAL-003a record shape | OK | none; reused for the judge's latency (`summarize_judge_latency`) |
| `RankedChunk.from_record` | EVAL-003a record | needs the duplicate locations | new optional `chunk_index` argument; raises when a chunk has `duplicate_chunk_ids` and no index is given (never skipped silently) |

**Every change to audited code** (`metrics/retrieval.py`; GitNexus impact below):
1. `RankedChunk` gains `duplicates: tuple[(source_id, start, end), ...] = ()`, and `from_record(record, chunk_index=None)` resolves
   `duplicate_chunk_ids` (unknown id → `ValueError`).
2. `_hits`: at **section** level the chunk **or any duplicate** overlaps the span; at source level only the kept chunk's own
   document counts (owner). The new helper `_location_hits` holds the old body unchanged.
3. New functions: `duplicate_rule_changes`, `chunk_index`, `hits_any`, constant `HIT_KS = (1, 3, 5)`; module docstring.

Failing test first. `tests/unit/application/test_eval_duplicate_rule.py` was written before the rule:
- First run: collection error, since `duplicate_rule_changes` did not exist.
- With only the data field and a stub in place: **`7 failed, 6 passed`**. The 6 that passed are the `from_record` tests and the "no change" cases.
- After the rule: `13 passed`. All 241 application tests passed, including the 30 retrieval tests unchanged.
- **Scope change (owner, during the task): section level only.** The tests were changed first. The source-level test
  became "source metrics use the kept chunk's own document", the changed-values count went from 18 to 9, and source
  precision on a duplicate was pinned to 0.0. Against the old code they gave **`4 failed, 32 passed`**. After the
  one-line change in `_hits`: `36 passed`.

## Files

New:

| File | What |
|---|---|
| `src/knowledge_assistant/application/evaluation/judge.py` | `judge_check` (which records, which check), `build_judge_prompt`, `ANSWER_SCHEMA` / `REFUSAL_SCHEMA`, strict `parse_verdict`, `to_judge_verdict`, cache key, `JudgeRecords` use case (plan, run, budget, quota stop) |
| `src/knowledge_assistant/application/evaluation/scoring.py` | `score_record`, `retrieval_scores`, `answer_scores`, `citation_scores`, `summarize*`, `breakdown`, `summarize_judge_latency`, `cost_summary`, `estimate_usd` |
| `config/prompts/judge_v1.md` | judge prompt, sections `answerable` and `refusal` (made-up example; no eval content) |
| `config/pricing.json` | cited prices (URL, page date, retrieval date), nulls where not available |
| `scripts/evaluation/judge_run.py` | CLI: `--run-id`, `--max-llm-calls`, `--cases`, `--estimate-only`, `--allow-unfinished` |
| `tests/judge_fakes.py` | made-up records, verdict JSON, in-memory judgement store |
| `tests/unit/application/test_eval_duplicate_rule.py` (13), `test_eval_judge.py` (42), `test_eval_scoring.py` (24), `tests/unit/test_judge_run_cli.py` (11) | 90 tests (`pytest --collect-only`: `90 tests collected`) |
| `data/evaluation/results/20260927-dev-A-full-05680f9/judgements.jsonl` | the 2 live judgements (dev split; **not evaluation results**) |

Modified:

| File | Change |
|---|---|
| `application/evaluation/metrics/retrieval.py` | duplicate rule (above) |
| `config.py` | `JudgeSettings` / `get_judge_settings` (`JUDGE_MODEL` default `gemini-3.5-flash-lite`, prompt `judge_v1`, 3 attempts, 60 s, 2048 output tokens, limits 15 RPM / 250K TPM / 500 RPD, throttle 13); `get_pricing_path` |
| `core/interfaces/record_store.py` | new `JudgementStore` port (the `RecordStore` port is unchanged) |
| `infrastructure/persistence/jsonl_record_store.py` | `read_judgements` / `append_judgement` (`judgements.jsonl`, same fsync/torn-tail/redaction rules); `read_records` now calls a shared `_read(name)` with an identical body |
| `docs/specs/evaluation-spec.md` | duplicate rule, evidence_hit rule, "Answer and citation scoring" (judge, related note, OD-12, limitation), amendments log |
| docs | this report, prompt log, ledger rows 09b and 11, `AI_WORKLOG.md`, master plan (OD-12 row, stage B status), EPIC-05 status |

## Design decisions (for the verifier and owner)

1. **Which records get a call.**
   - An answered answerable record gets the answer check.
   - A corpus-insufficient record gets the refusal check when it was answered, or when it was refused with a related
     note or related citations.
   - Nothing else gets a call. An answerable refusal is `false_refusal` and a bare refusal is `correct_refusal`.
   - **Related note = non-empty `missing_information`**, the same rule as the EVAL-003a feed test. Answer-prompt rule 2
     makes the model fill it on almost every refusal it writes, so nearly every LLM refusal of a corpus-insufficient
     case will get a refusal check. Only gate refusals are bare. This is also stated in the spec.
2. **Strict parsing.**
   - The answer schema is §2's schema plus an `id` on each required point. Points are matched by id, never by position.
   - The ids must be exactly the record's required-point ids: no optional point, no duplicate, none missing.
   - The citation markers must be exactly the record's markers.
   - Booleans must be JSON booleans.
   - Anything else → `judge_error` with `raw_text` kept. The record then stays **unlabelled** (`result` None) and is listed
     in `answer.unlabelled`; it is never guessed.
3. **Refusal check key** `presents_related_as_answer`. The prompt sets it to true in four cases, which cover both D2 rows
   (insufficient + note, and answered):
   - the response presents related content as the answer;
   - it presents an inferred technique as the documents' answer;
   - it makes a substantive answering claim;
   - it never says the topic isn't covered.

   The example in the prompt is made up. I checked that the spec's MapGroup example appears in no eval case before
   deciding: it doesn't, but I still did not copy it.
4. **Cache key as specified**: (case_id, arm, sha256(answer), judge prompt version).
   - For an insufficient record, `answer` is the fixed localized message. That is safe only because a run never
     regenerates an ok record (EVAL-003a), so one run folder holds one answer per case × arm.
   - The prompt-file SHA-256 and the judge model are **validity checks**: an ok line with the same key but another hash
     or model refuses the run (`JudgeCacheMismatch`), instead of being reused or overwritten.
   - A `judge_error` line is retried on the next invocation.
5. **Model purity.** A judgement whose `model_used` is not `JUDGE_MODEL`, or which has `fallback_used`, is written as
   `judge_error` / `JudgeModelMismatch` with no verdict. The adapter is built with `allow_fallback=False`, so this should never happen.
6. **Never concurrent with the runner.** `judge_run.py` refuses a run whose last `run_eval.py` invocation has no
   `finished_at`. `--allow-unfinished` is the override for an invocation that was killed.
7. **Budget and quota** as in the runner. The budget counts requests (retries included) and is checked before each call.
   A quota `LLMError` records a `judge_error` and stops the run; other provider errors are recorded and the run goes on.
8. **Judge input.**
   - The question, the expected answer, every answer point with its `required` flag (optional marked "context only"),
     `acceptable_variations`, `must_not_claim` and `citation_criteria`.
   - The answer and its `missing_information`.
   - The full `display_text` of each cited chunk, found by `chunk_id` in the record's `retrieved` list. A citation not in
     that list raises; it would be a runner bug.
   - Uncited chunks are not shown.
9. **Groundedness.** An unsupported claim is "a substantive claim that neither the ground truth nor the cited passages support".
10. **Citation scoring (OD-12).** Answered answerable records only.
    - Automatic: source precision (the cited chunk's own document), section precision (the duplicate rule applies), and `auto_class`.
    - Judge: support rate = citations judged `yes` (`partial` does not count), and `judge_class`.
    - Both classes are `correct_evidence` > `correct_source_wrong_evidence` > `unsupported_citation`, or `citation_missing`
      when there are no citations. "Any cited chunk" is enough for `correct_evidence`; precision shows the rest.
    - Insufficient records only add to `related_citation_count`.
    - An answered unanswerable record gets no class: there is no evidence to check its citations against, and the
      refusal check judges it. Such records are counted in `answered_unanswerable_with_citations`.
11. **Accuracy denominators** are the labelled answerable records. Two kinds of record are listed and never counted as
    right or wrong: unlabelled records (judge missing or error), in `answer.unlabelled`, and runner-error records (no
    answer), in `answer.runner_errors`. The second list was added after the advisor review; without it, error records
    would have shrunk the denominator with no trace. EVAL-003c must print both lists in the table caption.
12. **Cost.**
    - Formula: prompt tokens × input price + (output + thinking tokens) × output price. The source prices output
      "including thinking tokens".
    - flash-lite reports no thinking count, so the estimate says how many calls "reported no thinking-token count (counted as 0)".
    - The price is null if the model has no price, or if the calls span several models.
    - Every estimate carries "the runs used the free tier and were not billed".
13. **Dev runs have no spans.** `expected-spans-v1.json` covers the eval split only (EVAL-003b-pre decision 10), so
    `score_record` raises a clear error for an answerable case without spans. The end-to-end check below built dev spans
    in memory with the same pure function; nothing was committed.

## Duplicate rule: how many case × arm values it changes (addendum item 2)

**Owner decision (2026-09-27, during this task): section level only.** "Record in the spec/report that the owner's
addendum said 'span/source' by mistake; the intended scope was section level (owner prediction 'at most 2 cases').
Source metrics and citation source precision use the kept chunk's own document, i.e. what the user sees. Report the
actual number of changed case×arm values after EVAL-004."

- **Real records:** both committed dev folders (arm A, 3 records each) have **0** retrieved chunks with
  `duplicate_chunk_ids`, so the rule changed **0** values. No eval-split records exist, and I created none.
  `summarize_retrieval` reports the real count (`duplicate_rule_changed`), so EVAL-004 will produce it from real runs.
- **Simulated bound** (scratch script, not committed; like the EVAL-003b-pre alternate-only count, this is **not a
  retrieval result**). Method:
  - Group each arm's chunks by the retriever's `passage_hash` (link-stripped body).
  - Try each member of a duplicate group as the kept chunk, alone, with the other members as its duplicates.
  - Ask `duplicate_rule_changes` whether any span value of an answerable eval case differs.

Final code (section level only):
```
(b) arm A: 733 chunks, 13 duplicate groups (26 extra copies); eval cases whose values the rule CAN change (some group member kept alone): 2 ['Q-EVAL-003', 'Q-EVAL-004']
      Q-EVAL-003: kept->dropped docs ['section:12->13']
      Q-EVAL-004: kept->dropped docs ['section:12->13']
(b) arm B: 859 chunks, 0 duplicate groups (0 extra copies); eval cases whose values the rule CAN change (some group member kept alone): 0 []
```
(The 13 groups / 26 extra copies match RAG-002's "Arm A 26 extra copies by passage". RAG-002's report lists the same two
cases, Q-EVAL-003 and 004, at `RAG-002.md` lines 142–145.)

**History: the first implementation, which applied the rule at source level too.** I read the addendum's "span/source
metrics" literally. The same script then gave:
```
(b) arm A: ... 6 ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-022', 'Q-EVAL-023', 'Q-EVAL-027', 'Q-EVAL-032']
      Q-EVAL-003: kept->dropped docs ['section:12->13', 'source-only:12->13']
      Q-EVAL-004: kept->dropped docs ['section:12->13', 'source-only:12->13']
      Q-EVAL-022: kept->dropped docs ['source-only:12->13']
      Q-EVAL-023: kept->dropped docs ['source-only:12->13']
      Q-EVAL-027: kept->dropped docs ['source-only:13->12']
      Q-EVAL-032: kept->dropped docs ['source-only:12->13']
```
At source level, a kept #12 chunk whose dropped copy is in #13 counted as "from #13" for every case that names #13 in
*any* section. That was above the owner's "at most 2", so I asked the owner (AskUserQuestion) instead of explaining it
away. The answer is quoted above. The tests were changed first, then the code (§ Audit).

**Alternate-only diagnostic under the rule** (advisor check). The rule makes a chunk whose copy overlaps an expected span
count as "inside". So I re-ran EVAL-003b-pre's simulated alternate-only count: every chunk that overlaps no expected
span, now judged with the rule, `k` = all of them. The result is unchanged, so the spec's figure stands:
```
arm A without duplicate rule: 4 / 32 ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
arm A with duplicate rule: 4 / 32 ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
arm B without duplicate rule: 4 / 32 ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
arm B with duplicate rule: 4 / 32 ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
```

## Tests

- `test_eval_duplicate_rule.py` (13) covers:
  - a kept #13 chunk whose #12 copy overlaps the span is a section hit, lenient and strict;
  - **source metrics use the kept chunk's own document**: hit, MRR and slot fraction are all 0 there;
  - a touching copy does not overlap;
  - strict-aware (a copy that overlaps only an alternate span);
  - MRR and slot fraction;
  - the alternate-only diagnostic treats a copy inside an expected span as "inside";
  - `from_record` resolves ids and refuses a missing index or an unknown id;
  - `duplicate_rule_changes` names the 9 section values (6 hits + 2 MRR + 1 slot fraction) and no source value, and is
    empty when nothing changes.
- `test_eval_judge.py` (42) covers:
  - `judge_check` for every §3 row (8 parametrized);
  - prompt contents (full cited text, braces not rescanned, uncited chunk absent, sections separate);
  - a template without a section is refused; both schemas require every field;
  - parsing: order by id and marker, **10 malformed answer verdicts and 3 malformed refusal verdicts all raise**;
  - one call per record at temperature 0 with the right schema;
  - **the cache prevents a second call**, and **each of the 4 key components forces a new call**;
  - a prompt-hash or model mismatch refuses the run;
  - **malformed JSON → `judge_error`, retried next time**;
  - another model's judgement is rejected, and so is a fallback judgement;
  - an unavailable error continues, a quota error stops;
  - the budget counts requests; tokens, latency and the key are recorded; `plan` counts;
  - verdict → label for both refusal outcomes, and `partially_correct` / `correct`.
- `test_eval_scoring.py` (24) covers, with hand-computed values:
  - citation precision, support and both classes; `correct_source_wrong_evidence`;
  - the span check and the judge check disagreeing; `citation_missing`;
  - a duplicate counting for section precision but not for source precision; related citations only counted;
  - runner-error records listed in `runner_errors` and kept out of the denominators;
  - unlabelled when the judgement is missing or an error; no-judge rows;
  - points-covered **0.5** for yes / partial / no + optional; the refusal-check label;
  - rates (accuracy 1/4, lenient 2/4, false refusal 1/4, correct refusal and hallucination 1/2, groundedness 2/3);
  - breakdowns by language, arm and parallel subset;
  - retrieval rows (strict alternate at rank 1: lenient 1.0 vs strict MRR 0.5; evidence@1 0 vs @3 1);
  - the duplicate-change count; missing spans and unresolved duplicates raise;
  - judge latency (retried call apart, p50 20.0);
  - cost `(2000×0.30 + 200×2.50)/1e6`, null price → None, mixed models → None, per-stage and per-question figures;
  - one case on both arms is 2 calls (100 output tokens per call, not 200 per case id);
  - the real `pricing.json` never has a price without a source.
- `test_judge_run_cli.py` (11) covers:
  - judging, then a re-run with 0 requests and "nothing to judge";
  - `--estimate-only` builds no LLM;
  - split taken from `run.json` when the records predate the field;
  - refusals: retrieval-mode run, unfinished invocation, unknown case, unknown run;
  - `--allow-unfinished`; budget stop prints the resume command; judge errors → exit 1;
  - the real adapter is `gemini-3.5-flash-lite`, fallback off, throttle 13.
- The 09b §5 items already covered by EVAL-003b-pre tests (span overlap, MRR, evidence whitespace, slots, points-covered,
  latency, every mapping row) still pass unchanged.

### Mutation proofs (harness in the session scratchpad; each file restored byte-for-byte)

```
== M1 refusal-check row: src/knowledge_assistant/application/evaluation/metrics/mapping.py
   - return HALLUCINATION if judge.presents_related_as_answer else CORRECT_REFUSAL
   + return CORRECT_REFUSAL
   pytest exit 1
   | FAILED tests/unit/application/test_eval_result_mapping.py::test_unanswerable_insufficient_with_related_material_uses_the_refusal_check[True-False]
   | FAILED tests/unit/application/test_eval_result_mapping.py::test_unanswerable_insufficient_with_related_material_uses_the_refusal_check[False-True]
   | FAILED tests/unit/application/test_eval_result_mapping.py::test_unanswerable_insufficient_with_related_material_uses_the_refusal_check[True-True]
   | FAILED tests/unit/application/test_eval_result_mapping.py::test_unanswerable_answered_is_decided_by_the_refusal_check_never_auto_hallucination
   | FAILED tests/unit/application/test_eval_judge.py::test_judged_records_map_to_labels
   | FAILED tests/unit/application/test_eval_scoring.py::test_refusal_check_labels_without_groundedness
   | 6 failed, 79 passed in 1.59s
   restored: sha256 before ef2cc3732a20414e after ef2cc3732a20414e equal=True git-diff-exit=0
== M2 duplicate rule off: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - duplicates = chunk.duplicates if level == SECTION else ()
   + duplicates = ()
   pytest exit 1
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_a_duplicate_that_overlaps_the_span_makes_the_kept_chunk_a_section_hit
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_rule_is_strict_aware
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_rule_in_mrr_and_slot_fraction
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_counts_as_inside_the_expected_spans_for_the_alternate_only_diagnostic
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_rule_changes_names_every_value_the_rule_changed
   | FAILED tests/unit/application/test_eval_scoring.py::test_a_duplicate_of_the_cited_chunk_counts_for_section_precision
   | FAILED tests/unit/application/test_eval_scoring.py::test_retrieval_summary_counts_duplicate_rule_changes
   | 7 failed, 60 passed in 1.40s
   restored: sha256 before 62dd99d622159cb2 after 62dd99d622159cb2 equal=True git-diff-exit=1
== M2b duplicate rule also at source level: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - duplicates = chunk.duplicates if level == SECTION else ()
   + duplicates = chunk.duplicates
   pytest exit 1
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_source_metrics_use_the_kept_chunks_own_document
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_rule_in_mrr_and_slot_fraction
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_duplicate_rule_changes_names_every_value_the_rule_changed
   | FAILED tests/unit/application/test_eval_scoring.py::test_a_duplicate_of_the_cited_chunk_counts_for_section_precision
   | 4 failed, 63 passed in 1.40s
   restored: sha256 before 62dd99d622159cb2 after 62dd99d622159cb2 equal=True git-diff-exit=1
== M6a from_record without the missing-index guard: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - if duplicate_ids and chunk_index is None:
   + if False:
   pytest exit 1
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_from_record_refuses_duplicates_without_a_chunk_index
   | FAILED tests/unit/application/test_eval_scoring.py::test_score_record_refuses_unresolved_duplicates
   | 2 failed, 35 passed in 1.43s
   restored: sha256 before 62dd99d622159cb2 after 62dd99d622159cb2 equal=True git-diff-exit=1
== M6b from_record without the unknown-id guard: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - if unknown:
   + if False:
   pytest exit 1
   | FAILED tests/unit/application/test_eval_duplicate_rule.py::test_from_record_refuses_an_unknown_duplicate_id
   | 1 failed, 36 passed in 1.36s
   restored: sha256 before 62dd99d622159cb2 after 62dd99d622159cb2 equal=True git-diff-exit=1
== M5 cost per question by case id: src/knowledge_assistant/application/evaluation/scoring.py
   - per_question = {name: tokens[name] / tokens["calls"] if tokens["calls"] else None
   + per_question = {name: tokens[name] / len({i["case_id"] for i in items}) if tokens["calls"] else None
   pytest exit 1
   | FAILED tests/unit/application/test_eval_scoring.py::test_per_question_tokens_count_each_arm_as_its_own_call
   | 1 failed, 23 passed in 1.37s
   restored: sha256 before 3550ded5c7b01922 after 3550ded5c7b01922 equal=True git-diff-exit=1
== M7 runner errors not listed: src/knowledge_assistant/application/evaluation/scoring.py
   - for row in rows if row["status"] != "ok"),
   + for row in rows if False),
   pytest exit 1
   | FAILED tests/unit/application/test_eval_scoring.py::test_runner_error_records_are_listed_not_silently_dropped
   | 1 failed, 66 passed in 1.42s
   restored: sha256 before 3550ded5c7b01922 after 3550ded5c7b01922 equal=True git-diff-exit=1
== M3 per-point evidence all->any: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - return int(all(any(_quotes_found(chunks, quotes, k)) for quotes in point_quotes.values()))
   + return int(any(any(_quotes_found(chunks, quotes, k)) for quotes in point_quotes.values()))
   pytest exit 1
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss
   | 1 failed, 50 passed in 1.38s
   restored: sha256 before b4ec82059dc2a941 after b4ec82059dc2a941 equal=True git-diff-exit=0
== M4a cache key without the answer hash: src/knowledge_assistant/application/evaluation/judge.py
   - return case_id, arm, answer_hash, prompt_version
   + return case_id, arm, '', prompt_version
   pytest exit 1
   | FAILED tests/unit/application/test_eval_judge.py::test_every_cache_key_component_forces_a_new_call[answer]
   | FAILED tests/unit/application/test_eval_judge.py::test_judgement_line_records_tokens_latency_and_the_key
   | 2 failed, 72 passed in 1.68s
   restored: sha256 before 25f6c4c5494a1a49 after 25f6c4c5494a1a49 equal=True git-diff-exit=0
== M4b cache key without the arm: src/knowledge_assistant/application/evaluation/judge.py
   - return case_id, arm, answer_hash, prompt_version
   + return case_id, '', answer_hash, prompt_version
   pytest exit 1
   | FAILED tests/unit/application/test_eval_judge.py::test_every_cache_key_component_forces_a_new_call[arm]
   | 1 failed, 73 passed in 1.72s
   restored: sha256 before 25f6c4c5494a1a49 after 25f6c4c5494a1a49 equal=True git-diff-exit=0
== M4c cache key without the prompt version: src/knowledge_assistant/application/evaluation/judge.py
   - return case_id, arm, answer_hash, prompt_version
   + return case_id, arm, answer_hash, ''
   pytest exit 1
   | FAILED tests/unit/application/test_eval_judge.py::test_every_cache_key_component_forces_a_new_call[prompt_version]
   | FAILED tests/unit/application/test_eval_judge.py::test_same_key_with_another_prompt_hash_or_model_refuses_to_run
   | FAILED tests/unit/application/test_eval_judge.py::test_judgement_line_records_tokens_latency_and_the_key
   | 3 failed, 71 passed in 1.72s
   restored: sha256 before 25f6c4c5494a1a49 after 25f6c4c5494a1a49 equal=True git-diff-exit=0
== M4d cache key without the case id: src/knowledge_assistant/application/evaluation/judge.py
   - return case_id, arm, answer_hash, prompt_version
   + return '', arm, answer_hash, prompt_version
   pytest exit 1
   | FAILED tests/unit/application/test_eval_judge.py::test_one_call_per_record_temperature_0_and_the_check_schema
   | FAILED tests/unit/application/test_eval_judge.py::test_every_cache_key_component_forces_a_new_call[case_id]
   | FAILED tests/unit/application/test_eval_judge.py::test_budget_counts_requests_and_stops_before_the_next_call
   | FAILED tests/unit/test_judge_run_cli.py::test_judges_every_answered_record_then_spends_nothing_on_a_rerun
   | FAILED tests/unit/test_judge_run_cli.py::test_budget_stop_prints_the_resume_command
   | 5 failed, 69 passed in 1.65s
   restored: sha256 before 25f6c4c5494a1a49 after 25f6c4c5494a1a49 equal=True git-diff-exit=0
```
The harness ran twice. The first run was M1–M4d with the source-level M2, against commit `088124e`; `git status` was clean
afterwards. The second run, whose M2 to M7 blocks are pasted here, covers all 13 mutations against the working tree after
the owner's scope change. It restores each file from its working-tree bytes. Its `git-diff-exit=1` only means the file had
uncommitted edits; the sha256 check and `sha256sum -c` over the 4 files afterwards were the proof (all OK). In the second
run, M1 and M3/M4 killed the same tests as shown (only the passed counts grew, by the tests added since).

M5 (added after the report draft) was first run by hand, as below, and is now in the harness run above: back up `scoring.py`,
apply the edit, run the test file, restore from the backup. The mutation puts back my first draft's per-question divisor (distinct case ids instead of calls):
```
- per_question = {name: tokens[name] / tokens["calls"] if tokens["calls"] else None
+ per_question = {name: tokens[name] / len({i["case_id"] for i in items}) if tokens["calls"] else None
FAILED tests/unit/application/test_eval_scoring.py::test_per_question_tokens_count_each_arm_as_its_own_call
1 failed, 22 passed in 1.42s
```
After the restore: `23 passed`, and `grep` shows the `tokens["calls"]` line back.

**Tests-first honesty:**
- The duplicate-rule file was seen failing first, for a behavioural reason (above).
- The judge, scoring and CLI test files were written right after their modules. Their first runs were all green:
  42, 21 and 11 passed. A first-run pass proves little, so I rely on the mutations above for those files.
- Two scoring tests were added later. The missing-spans test was written after the error it checks. The two-arm cost test
  was added because I noticed the first cost test used two different cases. It would have passed under my first,
  wrong formula too; it now fails under that formula (M5).

## Commands run (real output)

| Step | Command | Result |
|---|---|---|
| Dev baseline | `pytest -q` in the detached worktree at `7db105b` | `685 passed, 1 deselected` |
| Duplicate rule, red | `pytest tests/unit/application/test_eval_duplicate_rule.py` (data field + stub only) | `7 failed, 6 passed` |
| After the rule | `pytest tests/unit/application/` | `241 passed` |
| Code milestone | full `pytest -q` | `772 passed, 1 deselected` (commit `088124e`) |
| After the report draft | full `pytest -q` | `773 passed, 1 deselected` |
| After the cost test | full `pytest -q` | `774 passed, 1 deselected` |
| Scope change, red | duplicate + scoring test files, old `_hits` | `4 failed, 32 passed` |
| Final (after the scope change and the runner-error listing) | full `pytest -q`; `--collect-only` on the 4 new test files | `775 passed, 1 deselected` = 685 + 90; `90 tests collected` |
| Frozen hashes | `sha256sum eval-v1.jsonl dev-v1.jsonl`; `git diff 7db105b --stat -- data/evaluation/questions corpus` | `3436870e…2937`, `37d349e5…21d6` (= snapshot); diff empty |

## Live judge (addendum item 5)

Run folder `data/evaluation/results/20260927-dev-A-full-05680f9` (dev split, arm A). `run.json` `config.split` = `dev`; the
records predate the `split` field. Q-DEV-001 and Q-DEV-002 were judged one at a time, each with `--max-llm-calls 1`,
checking the HTTP counter in between.

```
$ judge_run.py --run-id 20260927-dev-A-full-05680f9 --estimate-only
judge run 20260927-dev-A-full-05680f9 (split dev, arm A): model gemini-3.5-flash-lite (fallback off, temperature 0, throttle 13 RPM), prompt judge_v1 (74debd108034)
records needing a judgement: 2 (0 already judged ok, 2 to call); labelled without a judge: 1; not scored (error or retrieval records): 0
estimate: at least 2 judge request(s) (retries extra), about 0.2 min at 13 RPM, 2 of 500 requests per day

$ judge_run.py --run-id 20260927-dev-A-full-05680f9 --cases Q-DEV-001 --max-llm-calls 1
[1/1] Q-DEV-001 A answer: ok
judged 1 ok, 0 judge_error, 0 cached; judge requests this invocation: 1 (HTTP 1, by model {'gemini-3.5-flash-lite': 1}); embedding requests: 0

$ judge_run.py --run-id 20260927-dev-A-full-05680f9 --cases Q-DEV-002 --max-llm-calls 1
[1/1] Q-DEV-002 A answer: ok
judged 1 ok, 0 judge_error, 0 cached; judge requests this invocation: 1 (HTTP 1, by model {'gemini-3.5-flash-lite': 1}); embedding requests: 0

$ judge_run.py --run-id 20260927-dev-A-full-05680f9
records needing a judgement: 2 (2 already judged ok, 0 to call); labelled without a judge: 1; not scored (error or retrieval records): 0
nothing to judge: every record that needs a judgement is judged ok
```
(Only the first command's header lines are repeated here; the two single-case runs printed the same header with 1 to call.
All four exited 0.)

Judgement 1 of `judgements.jsonl`, pasted as written (reflowed onto one line per short object):
```json
{"run_id": "20260927-dev-A-full-05680f9", "case_id": "Q-DEV-001", "arm": "A", "mode": "full", "split": "dev", "check": "answer",
 "answer_sha256": "ad4ce89b67427029ffd57c3e0f16338d4100539ed29c8b687e4c4ec3a74b9c27", "judge_prompt_version": "judge_v1",
 "judge_prompt_sha256": "74debd1080342e0eeecfc326ab30c8dd16d15513472bb45f81ccdbb07b9d37c4", "judge_model": "gemini-3.5-flash-lite",
 "status": "ok",
 "verdict": {"required_points": [
     {"id": "P1", "point": "A static class can't be instantiated and contains only static members.", "covered": "yes"},
     {"id": "P2", "point": "A static class is implicitly sealed, so you can't derive from it.", "covered": "yes"}],
   "contradicts_ground_truth": false, "unsupported_claims": [],
   "citations": [{"marker": 1, "supports_attached_claim": "yes"}],
   "reason": "The answer correctly covers all required points and is fully supported by the ground truth and cited passages."},
 "error": null, "error_kind": null, "error_type": null, "raw_text": null,
 "model_used": "gemini-3.5-flash-lite", "retry_count": 0, "fallback_used": false,
 "prompt_tokens": 773, "output_tokens": 183, "thoughts_tokens": null,
 "latency_ms": {"generate": 22348.335600000155, "retry_wait": 0.0, "throttle_wait": 0.0, "total": 23469.75909999992},
 "started_at": "2026-09-27T07:24:34.218+00:00", "finished_at": "2026-09-27T07:24:57.688+00:00"}
```

Q-DEV-002 (the Vietnamese answer against the English ground truth): P1 `yes`, P2 `yes`, no contradiction, no unsupported
claims, markers 1 and 2 `yes`; 1407 prompt / 252 output tokens; `generate` 2051.7 ms. Reason: "The answer accurately covers
all required points regarding the definition and usage of nint and nuint. All claims are fully supported by the cited
passages."

**Anomaly (unexplained):** Q-DEV-001's judge call took **22.3 s** of model time. Q-DEV-002 took 2.1 s, and the answer calls
in EVAL-003a took 1.7–2.6 s. There was no retry and no throttle wait. The cause is unverified (free-tier latency noise is one
possibility); EVAL-004's latency table will show whether it recurs.

**Refusal check live: not run.** No committed record needs one. Q-DEV-005 is a bare gate refusal: `missing_information`
null, 0 citations. Its table label is `correct_refusal`, with no call. Creating such a record needs a new answer run, which
the addendum does not allow ("≤ 3 judge calls on the committed dev dry-run records"). The refusal path is proven offline only.

**End to end on real data** (scratch script; dev spans built in memory with `build_expected_spans`, not committed):
```
Q-DEV-001 result correct grounded True points 1.0 | cite {'citation_count': 1, 'source_precision': 1.0, 'section_precision': 1.0, 'support_rate': 1.0, 'auto_class': 'correct_evidence', 'judge_class': 'correct_evidence', 'related_citation_count': None} | section@5 1 strict 1 evidence@5 1 mrr 1.0 dup changed []
Q-DEV-002 result correct grounded True points 1.0 | cite {'citation_count': 2, 'source_precision': 1.0, 'section_precision': 1.0, 'support_rate': 1.0, 'auto_class': 'correct_evidence', 'judge_class': 'correct_evidence', 'related_citation_count': None} | section@5 1 strict 1 evidence@5 1 mrr 1.0 dup changed []
Q-DEV-005 result correct_refusal grounded None points None | cite {'citation_count': None, 'source_precision': None, 'section_precision': None, 'support_rate': None, 'auto_class': None, 'judge_class': None, 'related_citation_count': 0} | section@5 None strict None evidence@5 None mrr None dup changed None
cost answer {'calls': 2, 'models': ['gemini-3.5-flash-lite'], 'prompt_tokens': 3235, 'output_tokens': 327, 'thoughts_tokens': 0, 'calls_without_thoughts_tokens': 2} usd {'usd': 0.001788, 'reason': 'estimate: list price per 1M tokens; the runs used the free tier and were not billed; 2 call(s) reported no thinking-token count (counted as 0)'}
cost judge {'calls': 2, 'models': ['gemini-3.5-flash-lite'], 'prompt_tokens': 2180, 'output_tokens': 435, 'thoughts_tokens': 0, 'calls_without_thoughts_tokens': 2} usd {'usd': 0.0017415, 'reason': 'estimate: list price per 1M tokens; the runs used the free tier and were not billed; 2 call(s) reported no thinking-token count (counted as 0)'}
judge latency main n 2 generate {'n': 2, 'mean': 12200.030200000016, 'p50': 2051.7247999998744, 'p95': 22348.335600000155, 'max': 22348.335600000155}
```
Hand checks:
- Answer tokens 1197 + 2038 = 3235 and 72 + 255 = 327 (EVAL-003a records): 3235 × 0.30/1M + 327 × 2.50/1M = $0.001788.
- Judge: 2180 × 0.30/1M + 435 × 2.50/1M = $0.0017415.

These are dev dry-run numbers (3 records), **not evaluation results**.

## Quota accounting for this task

- Judge requests: **2** (`gemini-3.5-flash-lite`, both ok, 0 retries); HTTP counter 1 + 1. Answer requests: 0. Fallback: 0.
- Embedding requests: **0**. The judge opens no embedder.
- HTTP 429: 0; 5xx: 0. `errors.jsonl` was not created in the run folder.

## Pricing source (addendum item 4)

`config/pricing.json` comes from `https://ai.google.dev/gemini-api/docs/pricing?hl=en`: page "Last updated 2026-09-24 UTC",
retrieved 2026-09-27. The quoted rows are from the "Gemini 3.5 Flash-Lite > Standard" table, paid tier:
- "Input price … $0.30 (text / image / video / audio)";
- "Output price (including thinking tokens) … $2.50".

Two prices are **null / "not available"**:
- `gemini-embedding-001`: not on the page. The page lists "Gemini Embedding 2", a different model, whose $0.20 I did **not** borrow.
- `gemini-3.5-flash`: it has a section on the page, but my search tool did not return its price table, so I did not
  record a price. Evaluation runs never call it.

The free tier is "Free of charge" on the same page; every estimate says the runs used the free tier.

## Eval firewall

Scratch script over the 22 files this branch changed or added since `7db105b` (tracked diff + untracked, including the
judgements file and every doc of this task; final run after all docs were written). It reads `eval-v1.jsonl` in memory and prints counts only.

- **0** of the 36 eval question texts in any file (whitespace collapsed).
- `Q-EVAL`/`BP-EVAL` ids in added lines appear in only four places (final scan):
  - `docs/specs/evaluation-spec.md` (1 match): the simulated duplicate-rule cases;
  - `AI_WORKLOG.md` (1): the same two cases;
  - the prompt log (4): the verbatim 09b prompt's own examples;
  - this report (36): the analysis sections named below.
- The judge prompt, judge code, test fakes and `judgements.jsonl` hold **0** ids and **0** question texts. The judge-prompt
  example is made up, and "MapGroup" is in no eval case.
- No eval-split command was run.
- This report names eval case ids in its analysis sections: the duplicate-rule bound and the evidence_hit diagnostic,
  as EVAL-003b-pre's report did. It holds no question texts.
- Secret scan: **0** matches for the `AIza` + 35-character shape, **0** for the configured key and for its 12-character
  prefix. The key was read in memory from the main `.env` and never printed.

## GitNexus

- Impact analysis before the edits (upstream):
  - `RankedChunk`: **LOW** (0 dependents in the index).
  - `from_record`: **LOW** (1 test).
  - `_hits`: **CRITICAL**. It feeds `slots_satisfied`, `reciprocal_rank` and `evidence_hit_via_alternate_only_at_k`, and
    through them source/section hit, slot fraction and MRR: 5 flows, all in the one metrics module. I told the owner in
    chat before editing. The change is additive: with no duplicates the result is identical, and the 30 retrieval tests
    are unchanged and pass.
- `JsonlRecordStore` and `read_records` are **not in the index**, which is stale at `dcdea66` and predates EVAL-003a. I used
  grep instead: 46 references in 11 files. `read_records` keeps its behaviour, and its 9 store tests pass.
- `detect_changes` returned `Repository "…\worktrees\eval-003b" not found` (the index is registered for the main
  checkout). The scope check was `git status` / `git diff --stat` before each commit instead: only this task's files.
  I did not run `npx gitnexus analyze`, because it would rewrite `AGENTS.md`/`CLAUDE.md` in the shared main checkout.

## Unverified / open

- **Duplicate rule, actual count**: 0 on the dev records. The eval count comes from EVAL-004's real runs (owner); the
  simulated bound is 2 (Q-EVAL-003, 004, Arm A).
- **Refusal check never ran live.** No committed record needs one. Proven offline only; EVAL-004 will run it for real.
- **Judge quality is unmeasured.** 2 dev judgements agree with a reading of the records, but that is not a spot-check. The
  owner spot-check of ~10 judgments after EVAL-004 is now a task in ledger row 11. OD-13 (sample size) stays open.
- Q-DEV-001's 22.3 s judge latency (cause unknown).
- `gemini-3.5-flash` price not extracted.
- No real 429/5xx seen (RAG-003's open question stays open).

## Deviations from the prompt

- §2 schema: I added an `id` to each `required_points` entry, so points are matched by id, not position (addendum: "the
  answerable schema is as in §2", plus strict parsing).
- §2 "one live judge call": the addendum's ≤ 3 applies. I made 2, because only 2 committed records need a judgement.
- §1 `evidence_hit` wording: superseded by the owner's per-point rule (addendum 2). The prompt file itself is unchanged;
  owner lines below.
- `judge_run.py --allow-unfinished` and the unfinished-invocation guard were not asked for. They enforce "never
  concurrently with the runner".
- Addendum item 2 said "span/source metrics". The owner corrected this during the task to section level only
  (§ Duplicate rule).

## Explain it back

- **Why the judge never picks the label.** The judge answers narrow questions: is each required point covered, is anything
  contradicted, does each cited passage support its claim, and is related content presented as the answer. A fixed table in
  code turns those answers into `correct` / `partially_correct` / … . The same judge output therefore always gives the same
  label, and the table is tested row by row. A malformed or missing verdict becomes `judge_error` and the record stays
  unlabelled and listed, because a guessed label would be a fabricated result. The alternative, asking the judge for the
  label directly, hides the rule inside a prompt and cannot be unit-tested.
- **Why strict parsing by id.** The judge must return exactly the required point ids and exactly the cited markers.
  Position-based matching would silently shift grades when the model skips or reorders a point. Rejecting the reply costs
  one retry on the next invocation; a mis-assigned grade would never be noticed.
- **Why two citation checks (OD-12).** The span check is automatic and cheap: did the cited chunk come from the expected
  section? But it cannot see whether the text supports the sentence. The judge check reads the text but shares the answer
  model's biases. Reporting both separately shows where they disagree, for example a chunk from the wrong section that
  still supports the claim (`unsupported_citation` by span, `correct_evidence` by judge). A single blended number would hide that.
- **Why the duplicate rule.** The retriever keeps one chunk per identical passage (RAG-002). When #12 and #13 contain the
  same paragraph, it may keep the #12 copy while the ground truth names #13. Without the rule, a retrieval that found
  exactly the right text would score as a miss because of which copy survived dedup. With it, a chunk also counts through
  the copies it replaced. The count of changed values is reported, so a reader can see how much the rule moves the numbers.
  It applies only to section-level (span) metrics. Source metrics keep the document the user actually sees cited, so a
  #12 chunk never becomes a #13 "source" (owner decision; applied at source level too, the rule could change 6 cases
  instead of the 2 intended).
- **Why cache by (case, arm, answer hash, prompt version) and refuse on a hash/model mismatch.** Judge calls come out of the
  same 500-per-day quota as answers, so a re-run must cost 0. Any change to what the judge sees (a new answer, another arm,
  a new prompt version) must cost a new call. An edited prompt file under the same version name, or another judge model,
  would silently mix two judges in one table, so the run stops instead.

## Lines for the owner (not applied; `agents/prompts/` is yours)

`agents/prompts/CHANGELOG.md`, new row:
```
| 2026-09-27 | `09b-EVAL-003b-…` (+ `evaluation-spec.md`) | §1 `evidence_hit@k` per required point, content-level (supersedes "any chunk contains the evidence quote"); duplicate overlap rule for span/source metrics; §2 refusal-check key `presents_related_as_answer` + reason in a separate prompt section/schema; `required_points[].id` added to the judge schema; OD-12 = span check + judge support check, reported separately; judge limitation (same model; ~10-judgment owner spot-check after EVAL-004). | Owner addendum 2026-09-27 to EVAL-003b | Owner | EVAL-003b commits |
```
`agents/prompts/09b-EVAL-003b-metrics-and-judge.md` §1, `evidence_hit@k` bullet, replace with:
```
- `evidence_hit@k` = 1 if every required answer point has at least one of its supporting quotes (`evidence[].supports`) contained whole in some top-k chunk (owner 2026-09-26; content-level, aligns with lenient section hit); "any quote" and `evidence_hit_via_alternate_only` are diagnostics. Same whitespace normalization as `validate_questions.py` …
```

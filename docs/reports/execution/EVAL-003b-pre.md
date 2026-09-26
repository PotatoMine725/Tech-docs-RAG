# EVAL-003b-pre — pure metric + statistics functions (execution report)

Date: 2026-09-26. Branch `eval-003b-pre` from `origin/dev` (`f81faa5`), separate git worktree. Agent: Claude Code, Opus 5.5. Before re-verify, `origin/dev` (`8cb2010`: RAG-001b, GUI-001-pre) was merged in with merge commit `bebf486` (owner, 2026-09-26).

## Summary

- Pure retrieval metrics, expected spans (`expected-spans-v1.json`: 36 cases, 120 spans), the 09b §3 mapping table, the latency summary and exact paired statistics; 87 new offline tests; full suite `273 passed, 1 deselected` before the merge, and `313 passed, 1 deselected` on the merged branch = dev's `226` (measured on `8cb2010`) + 87; 5 mutation proofs; frozen question files unchanged.
- **evidence_hit** (owner, 2026-09-26): per required point. evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside.
- **evidence_hit_via_alternate_only count** (diagnostic, owner follow-up 2026-09-26): **4 of 32** answerable cases on both arms: Q-EVAL-003, Q-EVAL-004, Q-EVAL-007, Q-EVAL-008. This is simulated alternate-only retrieval (every chunk that overlaps no expected span of the case, `k` = all of them), **not a retrieval result**; there is no runner yet. Output: § evidence_hit_via_alternate_only below.
- Verify: [EVAL-003b-pre-verify](../../reviews/evaluation/EVAL-003b-pre-verify.md) → ACCEPT WITH FIXES; the fixes the owner chose (option (a): keep the rule, fix the wording, add the diagnostic) are applied, and verifier fix 4 (Windows memory note, § Anomaly) was added at the owner's later request; pending a limited re-verify.

## Scope and entry condition

- **Owner exception to the ledger prerequisite rule (2026-09-26):** 09b formally needs 09a (EVAL-003a runner, `not started`). This part uses only frozen data (`eval-v1.jsonl`, `normalized.jsonl`) and no pipeline, so the owner allowed it to run in parallel. **When 09b proper runs, it audits this work instead of redoing it** (`_common.md` "Before you start" 4).
- In scope: 09b §1 retrieval metrics + expected spans, 09b §3 mapping table (judge verdict passed in as data), 09b §4 latency summary, 12-EXP-001 §1 paired statistics, and the matching 09b §5 tests.
- Out of scope (left for 09b proper / EXP-001): judge prompt and judge code (`judge.py`, `judge_v1.md`, `judge_run.py`), OD-12, citation metrics, answer/refusal rate aggregation, cost, breakdowns, the live judge call, `compare_arms.py`.
- Not touched by the task's own commits (through `8adeb71`): embeddings/, vector_store/, llm/, generation/, retrieval/, core/interfaces/, presentation/, scripts/, the frozen question files, shared docs (ledger, AI_WORKLOG, CHANGELOG, master plan). No Gemini calls, no ChromaDB access, no new dependency, no venv/pip.
- `data/processed/documents/normalized.jsonl` is tracked in git, so the worktree had its own copy: nothing was read from the main checkout.
- **After verify (owner-authorized):** the branch now also modifies two shared docs: `AI_WORKLOG.md` and `docs/plans/task-ledger.md`. The verifier's commit `fd59109` did that first; this follow-up then added the merged 09b ledger note and the worklog entry the owner asked for. For re-verify scope, check the task's own files with `git diff --name-status origin/dev...8adeb71` and review the later commits separately.
- **Merge of `origin/dev` (`bebf486`, owner, before re-verify):** a merge commit, no rebase, no force. `AI_WORKLOG.md` conflicted only where both sides appended a new 2026-09-26 entry; both entries are kept unchanged in time order (RAG-001b first committed 14:30:54, EVAL-003b-pre verifier findings 14:34:04), and a line-count check shows no line of either parent missing. `task-ledger.md` merged cleanly: it equals dev's file except the 09b row, which carries this branch's note. After the merge, `git diff --name-status origin/dev...HEAD` lists only this branch's work: the 14 task files, the verify report, and the two shared docs.

## Files (all new)

| File | What |
|---|---|
| `src/knowledge_assistant/application/evaluation/metrics/__init__.py` | package docstring |
| `.../metrics/spans.py` | `ExpectedSpan`; `build_expected_spans()` — expected + alternate sections → all variant spans, grouped by slot, tagged `expected` / `alternate`; pure |
| `.../application/evaluation/build_expected_spans.py` | I/O wrapper: reads the two inputs, writes the JSON with both input SHA-256s in the header (`newline="\n"`) |
| `.../metrics/retrieval.py` | `RankedChunk`; `overlaps`; `source_hit_at_k` / `section_hit_at_k` (lenient + `strict=True`); `slot_fraction_at_k`; `reciprocal_rank` (section/source, lenient/strict); `required_point_quotes`; `evidence_hit_at_k` (headline, per required point); `any_evidence_hit_at_k` and `evidence_hit_via_alternate_only_at_k` (diagnostics); `mean` |
| `.../metrics/mapping.py` | `map_result()` = the 09b §3 table; `JudgeVerdict` (data only); `JudgeVerdictMissing`; `is_grounded`; `points_covered` |
| `.../metrics/latency.py` | `nearest_rank`, `summarize_values`, `summarize_latency` (clean vs retried/fallback) |
| `.../application/evaluation/stats.py` | `mcnemar_exact`, `paired_bootstrap_ci`, `percentile_interval`, `wilcoxon_signed_rank` |
| `data/evaluation/questions/expected-spans-v1.json` | 36 cases, 120 spans (72 expected, 48 alternate), 0 empty spans |
| `tests/unit/application/test_eval_expected_spans.py` | 8 tests |
| `tests/unit/application/test_eval_retrieval_metrics.py` | 30 tests |
| `tests/unit/application/test_eval_result_mapping.py` | 22 tests |
| `tests/unit/application/test_eval_latency.py` | 9 tests |
| `tests/unit/application/test_eval_stats.py` | 18 tests |

(Collected items incl. parametrized cases, from `pytest --collect-only`: 8 + 30 + 22 + 9 + 18 = 87 new. The first PR version had 24 retrieval tests, 81 in total; the evidence_hit follow-up removed the any-vs-all test and added 6 (86); the post-verify follow-up added 1 for the alternate-only diagnostic (87).)

## Design decisions (and what 09b proper must confirm)

1. **Hits on offsets only.** A chunk hits a span when `source_id` matches and the half-open ranges overlap (`max(starts) < min(ends)`). The chunk's heading path is never compared: Arm A labels a merged section with its first heading (ADR-0003 D3), Arm B uses the nearest heading (D5). Verified for the real data: `display_text == normalized_text[char_start:char_end]` for all 733 Arm A and 859 Arm B chunks.
2. **Section spans are "own text" spans.** `normalized.jsonl` sections do not nest: a parent's span ends where its first child heading starts (e.g. #01 H1 `[0, 7556)`, first H2 `[7556, 10849)`). Checked over the whole corpus: 636 sections in 24 documents, all sorted, 0 with `char_start` < the previous section's `char_end`. So an expected H1 section is hit only by a chunk overlapping the H1 intro, not by a chunk in one of its subsections. This matches the slot design (BP-EVAL-017: S1 = the #11 intro, S2 = `IMiddleware`) but 09b proper should state it in the metric definitions.
3. **All variants, `evidence_variant` ignored for spans.** Every variant of a heading path becomes a span (ADR-0003 D8: any variant counts); `evidence_variant` only restricts where the evidence *quote* was checked by `validate_questions.py`. Measured: the corpus maximum is 8 variants of one (source_id, heading path) (#13 `Handle errors in ASP.NET Core > Additional resources`); in `expected-spans-v1.json` one section contributes at most 6 spans (Q-EVAL-022, #13) and one slot holds at most 10 spans (Q-EVAL-013 S1, several sections).
4. **Strict = role `expected` only.** Every slot of every answerable case has at least one expected span (tested), so strict hit is always computable.
5. **evidence_hit with several quotes — decided by the owner (2026-09-26), implemented in `240f948`.** Cases have several evidence quotes (multi-slot cases have quotes in different slots), and 09b says "contains the evidence quote" (singular). The first PR version used "any quote" as the headline with a `require_all` option, and flagged this as DECISION REQUIRED. **Owner decision:** the headline is per required point. Every required answer point must have at least one of its supporting quotes (`evidence[].supports`) contained whole in some top-k chunk: all-of across required points, any-of across the quotes of one point. Optional-point quotes are ignored. "Any quote" stays as a secondary diagnostic (`any_evidence_hit_at_k`). `require_all` was dropped.
   - `required_point_quotes(case)` builds `{required point: [quotes]}`. A quote that supports several points counts for each of them. It raises for an insufficient case, a case with no required point, or a required point with no quote. Measured on `eval-v1.jsonl`: 32 answerable cases, 77 required and 35 optional points, 100 quotes, 0 required points without a quote. 17 required points have more than one quote (e.g. Q-EVAL-023 P1–P3, two each).
   - **Correction to the owner's note "evidence_hit uses expected-source quotes only, so it behaves like strict".** Measured: 97 of 100 quotes lie in expected sections, but 3 lie in approved **alternate** sections: Q-EVAL-003 P3, Q-EVAL-004 P3 (#13 `… > Developer Exception Page`), and Q-EVAL-023 P2+P3 (#13 `… > IExceptionHandler > SuppressDiagnosticsCallback`). The owner's rule says "its supporting quotes (evidence[].supports)", so these 3 count; no expected-only filter was added.
   - **Corrected after verify (C1; owner chose option (a), 2026-09-26: keep the rule, no change to the matching code).** The previous version of this item said that no case can be evidence-hit from alternate-section quotes alone and called the metric strict. That was false: my check covered only the 3 quotes whose sole location is an alternate section, not every place where the same quote text occurs. evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside. Measured on the real chunk files (§ evidence_hit_via_alternate_only): in 4 of 32 cases (Q-EVAL-003 and 004, whose quotes also occur in `#12 … > Developer Exception Page`; Q-EVAL-007 and 008, whose quotes also occur in `#23 … > Route constraint reference`, all of them approved alternates), chunks that overlap no expected span give evidence_hit = 1, lenient section hit = 1 and strict section hit = 0, on both arms. The diagnostic `evidence_hit_via_alternate_only_at_k` reports such hits per case (below).
6. **Whitespace normalization is imported, not copied.** `retrieval.py` does `from scripts.evaluation.validate_questions import collapse_whitespace` (owner instruction). Works because pytest's `pythonpath = ["src", "."]` and `scripts/` is a namespace package; importing the module does no I/O. A test pins the provenance (`co_filename` ends with `scripts/evaluation/validate_questions.py`). **Coupling:** application code now depends on a CLI script module, and running it needs the repo root on `sys.path`. Follow-up (needs a `scripts/` edit, out of scope here): move `collapse_whitespace` into `application/evaluation/` and let `validate_questions.py` import it.
7. **Mapping takes the judge verdict as data.** The 09b judge JSON schema has no field for the D2 refusal check; here it is the named boolean `JudgeVerdict.presents_related_as_answer`. 09b proper owns the JSON key. A verdict the table needs but did not get raises `JudgeVerdictMissing` (caller records `judge_error`, never a guessed label). Zero required points or an unknown coverage value raise. Contradiction wins over full coverage (`yes, yes` + contradiction → `incorrect`). Unsupported claims change only groundedness, not the label.
8. **Latency record shape is assumed** (EVAL-003a does not exist yet): `{"latency_ms": {stage: float|None}, "retry_count": int, "fallback_used": bool}`. Main table = `retry_count == 0 and not fallback_used`; missing/None stage values are skipped per stage. Nearest-rank percentiles use an exact rational rank (`Fraction`): in floats `14/100*50 = 7.000000000000001` would give rank 8 instead of 7 (tested).
9. **Statistics conventions.** Δ = B − A everywhere. McNemar `b` = A-only successes (A=1, B=0), `c` = B-only (A=0, B=1); p exact two-sided binomial, capped at 1. Bootstrap resamples case *indices* (pairs together) with `random.Random(42)`, 10 000 resamples, bounds = nearest-rank 2.5th/97.5th percentiles (tail computed exactly: `(1-0.95)/2*100` is `2.500000000000002` in floats (as Python prints it) and would move the bound from rank 250 to 251; tested). Wilcoxon: zeros dropped, average ranks for ties (|d| rounded to 12 decimals so float noise ties), exact permutation distribution over doubled ranks. **Difference from scipy:** with ties scipy switches to a normal approximation; this implementation stays exact, so tied cases can differ slightly from scipy.
10. **Spans file covers the eval set only** (as instructed: `eval-v1.jsonl`). Dev cases (`dev-v1.jsonl`) are not included; add them in 09b if dev runs need retrieval metrics.
11. **`RankedChunk` is local to metrics.** RAG-001b's core `RetrievedChunk` is not on `dev` yet (and core/interfaces/ was off limits). `RankedChunk.from_record()` reads a chunk record (`display_text`); 09b adapts it to the retriever's type.

## Commands run (real output)

Environment: `D:\Code\Python\Knowledge assistant\.venv\Scripts\python.exe` by absolute path, `$env:PYTHONPATH="src"`, from the worktree root. Import check: `knowledge_assistant.__file__` and `scripts.evaluation.validate_questions.__file__` both resolve inside the worktree.

| Step | Command | Result |
|---|---|---|
| Frozen hashes before any edit | `Get-FileHash eval-v1.jsonl, dev-v1.jsonl` | `3436870e…2937`, `37d349e5…21d6` = snapshot |
| Baseline | `python -m pytest -q` | `186 passed, 1 deselected` |
| Build spans | `python -m knowledge_assistant.application.evaluation.build_expected_spans` | `36 cases, 120 spans` |
| Milestone 1 (`7e70180`) | full pytest | `218 passed, 1 deselected` |
| Milestone 2 (`0125683`) | full pytest | `249 passed, 1 deselected` |
| Milestone 3 (`afd7007`) | full pytest (×3) | `267 passed, 1 deselected` each |
| evidence_hit follow-up (`240f948`) | `pytest tests/unit/application/test_eval_retrieval_metrics.py`; full pytest | `29 passed`; `272 passed, 1 deselected` |
| Post-verify follow-up (`943f063`) | `pytest` retrieval + stats files; full pytest (×3) | `48 passed`; run 1 cut off (see Anomaly), runs 2 and 3: `273 passed, 1 deselected` each, exit 0 |
| Alternate-only count | `PYTHONPATH="src;." python alt_only.py` (job tmp, not committed) | 4 / 32 on each arm (below) |
| Dev baseline before the merge | full pytest in a detached worktree of `origin/dev` (`8cb2010`), job tmp | `226 passed, 1 deselected`, exit 0 |
| Merge (`bebf486`) | `git merge --no-ff --no-commit origin/dev`; resolve `AI_WORKLOG.md`; commit | 1 conflict (`AI_WORKLOG.md`), ledger auto-merged; 0 lines of either parent missing |
| Merged branch | full pytest; `pytest --collect-only` on the 5 task test files | `313 passed, 1 deselected`, exit 0 (= 226 + 87, not truncated); `87 tests collected` |
| Frozen hashes at the end | `Get-FileHash` + `git diff origin/dev -- <both files>` | unchanged (see below), diff empty; re-checked after the merge |

Anomaly (unexplained, reported honestly): one full run with `-rfE`, piped to a file, stopped at about 60 % with exit code 1 and no failure or summary line. The next verbose run and two quiet runs all exited 0 with `267 passed`. No test failure was ever shown; the likely cause is the environment (another session's job on this machine was killed for low memory earlier the same day), but this is **unverified**. It happened once more in the post-verify follow-up: the first full run (`pytest -q … 2>&1 | Select-Object -Last 3`) printed progress to about 70 % and then exited 1 with no summary. The two re-runs straight after, with output redirected to a file, both gave `273 passed, 1 deselected`, exit 0, and about 1.5 GB of virtual memory was free right after them. Cause still unverified.

Verifier observation (verifier fix 4, added at the owner's request): while running the mutation harness, the verifier saw one pytest subprocess die with Windows exit code `3221225773` (0xC000012D, "commit limit reached"; no pytest output), with only about 875 MB of virtual memory free system-wide. The same subprocess passed on every re-run ([verify report](../../reviews/evaluation/EVAL-003b-pre-verify.md)). This is consistent with today's truncated run at about 70 % (post-verify follow-up, above) and the earlier one at about 60 % both being environmental: machine-wide memory pressure from parallel sessions. It is not proof. My two truncated runs exited with 1, not `3221225773`, and I did not record free memory at the moment they stopped. The cause therefore stays **unverified (environmental, likely)**; no test failure was ever shown. The full run on the merged branch was not truncated.

Tests fixed while writing (my own mistakes, caught by running them): (1) a latency test comment claimed `0.1*30` is not exactly 3 in floats; it is `3.0`, so the test proved nothing. It was replaced with a searched real counterexample (`14/100*50`). (2) The bootstrap pairing test compared floats exactly (`0.9999999999999964` vs `1.0`, summation noise); it now uses `approx(abs=1e-9)`.

### Mutation proofs (run against the committed files, restored byte-for-byte)

```
== M1: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - return max(a_start, b_start) < min(a_end, b_end)
   + return max(a_start, b_start) <= min(a_end, b_end)
   pytest exit 1
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_touching_half_open_spans_do_not_overlap
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_section_hit_touching_chunk_is_a_miss
   | 2 failed in 0.04s
   restored: sha256 before 7ee7647185b4fed3 after 7ee7647185b4fed3 equal=True git-diff-exit=0
== M2: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - return [span for span in spans if span.role == EXPECTED] if strict else list(spans)
   + return list(spans)
   pytest exit 1
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_slot_rule_strict_and_lenient[sources0-1-0-1.0]
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_strict_mrr_alternate_at_rank_1_expected_at_rank_3
   | 2 failed, 2 passed in 0.05s
   restored: sha256 before 7ee7647185b4fed3 after 7ee7647185b4fed3 equal=True git-diff-exit=0
== M3: src/knowledge_assistant/application/evaluation/stats.py
   - deltas.append(statistic([b[i] for i in indices]) - statistic([a[i] for i in indices]))
   + deltas.append(statistic([b[i] for i in indices]) - statistic([a[rng.randrange(n)] for _ in indices]))
   pytest exit 1
   | assert (1.0, -18.999...9999996, 21.0) == approx((1.0 ±....0 ± 1.0e-09))
   | FAILED tests/unit/application/test_eval_stats.py::test_bootstrap_resamples_pairs_together
   | 1 failed in 0.07s
   restored: sha256 before c515fcb4ce756a84 after c515fcb4ce756a84 equal=True git-diff-exit=0
```
M2 fails only the `{04, 20}` parameter of the slot test, as expected: `{04, 26}` and `{20, 26}` give the same value under both rules. `git status` was clean after the three restores.

Per-point evidence rule (after the owner decision, run against `240f948`, same harness):
```
== M4: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - return int(all(any(_quotes_found(chunks, quotes, k)) for quotes in point_quotes.values()))
   + return int(any(any(_quotes_found(chunks, quotes, k)) for quotes in point_quotes.values()))
   pytest exit 1
   | ...test_eval_retrieval_metrics.py:206: AssertionError: assert 1 == 0
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss
   | 1 failed in 0.04s
   restored: sha256 before 5ff5a6cee9a91aa9 after 5ff5a6cee9a91aa9 equal=True git-diff-exit=0
```
M4 (all-of → any-of across points) turns the two-slot miss into a hit.

M5 (optional points no longer filtered), re-run after verify against `943f063` on the **whole** `test_eval_retrieval_metrics.py`. The first transcript ran only the optional-point test and showed "1 failed". Harness output below, with ANSI colour codes stripped and the worktree path shortened to `...`:
```
== M5: src/knowledge_assistant/application/evaluation/metrics/retrieval.py
   - points = {point["id"]: [] for point in case["answer_points"] if point["required"]}
   + points = {point["id"]: [] for point in case["answer_points"]}
   pytest exit 1
   | E   ValueError: Q-TEST: required points without an evidence quote: ['P3']
   | ...retrieval.py:118: ValueError: Q-TEST: required points without an evidence quote: ['P3']
   | E   AssertionError: assert {'P1': ['is a...turns true.']} == {'P1': ['is a...be injected']}
   | ...test_eval_retrieval_metrics.py:216: AssertionError: assert {'P1': ['is a...turns true.']} == {'P1': ['is a...be injected']}
   | E   AssertionError: assert {'P1': ['a', ..., 'P3': ['b']} == {'P1': ['a', ..., 'P2': ['b']}
   | ...test_eval_retrieval_metrics.py:222: AssertionError: assert {'P1': ['a', ..., 'P3': ['b']} == {'P1': ['a', ..., 'P2': ['b']}
   | E   Failed: DID NOT RAISE ValueError
   | ...test_eval_retrieval_metrics.py:228: Failed: DID NOT RAISE ValueError
   | E   ValueError: Q-EVAL-023: required points without an evidence quote: ['P4']
   | ...retrieval.py:118: ValueError: Q-EVAL-023: required points without an evidence quote: ['P4']
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_evidence_hit_ignores_a_missing_optional_point_quote
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_required_point_quotes_counts_a_quote_for_every_point_it_supports
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_required_point_quotes_raises_when_a_required_point_has_no_quote
   | FAILED tests/unit/application/test_eval_retrieval_metrics.py::test_required_point_quotes_real_case_q_eval_023
   | 5 failed, 25 passed in 0.08s
   restored: sha256 before d37ea874758776da after d37ea874758776da equal=True git-diff-exit=0
```
The whole file gives **5 failures**, not the 3 the verifier reported and the owner's follow-up repeated. Each failure is explained by the mutation making optional points required:
- the two-slot case's optional P3 has no quote, so the function raises;
- the optional-point test and the "quote for every point" test fail their dict equality;
- the "raises when a required point has no quote" case no longer raises, because its only point is optional;
- in the real Q-EVAL-023 record, the optional P4 has no quote, so the function raises.

The new alternate-only test is not affected (it builds its point dict by hand).

### 09b §5 test list → where it is covered

| 09b §5 item | Test |
|---|---|
| section hit via overlap, touching `[0,10)`/`[10,20)` = no overlap, multiple variants | `test_touching_half_open_spans_do_not_overlap`, `test_section_hit_touching_chunk_is_a_miss`, `test_section_hit_any_variant_counts` (+ other-document miss) |
| MRR rank 3 = 0.333…, no hit = 0, strict MRR alternate@1 / expected@3 → 1.0 / 0.333… | `test_reciprocal_rank_hit_at_rank_3`, `…_no_hit_is_zero`, `test_strict_mrr_alternate_at_rank_1_expected_at_rank_3` |
| evidence_hit false when split across two chunks | `test_evidence_hit_false_when_the_quote_is_split_across_two_chunks` |
| evidence_hit true across whitespace (spaces, newlines, U+00A0), Q-EVAL-028 / #18 | `test_evidence_hit_ignores_whitespace_differences`, `test_evidence_hit_real_case_q_eval_028_no_break_space_in_source_18` (real Arm A chunk) |
| (owner decision) two variant quotes for one point, one found → hit (Q-EVAL-023 style) | `test_evidence_hit_one_of_two_variant_quotes_for_a_point_is_enough`, `test_required_point_quotes_real_case_q_eval_023` (real record) |
| (owner decision) two-slot case, only one slot's quote found → miss | `test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss` (the any-quote diagnostic gives 1 on the same input) |
| (owner decision) optional-point quote missing → still hit | `test_evidence_hit_ignores_a_missing_optional_point_quote` |
| (owner follow-up) evidence_hit_via_alternate_only: alternate-only → 1; expected chunk without a quote → still 1; expected chunk with a quote → 0, unless below k; evidence miss → 0 | `test_evidence_hit_via_alternate_only_flags_hits_earned_outside_the_expected_spans` (diagnostic only, no mutation proof, as instructed) |
| every mapping row, both refusal-check outcomes | `test_eval_result_mapping.py` (all 7 rows) |
| slots S1={04}, S2={26, 20 alt}: {04,20} lenient hit/strict miss; {04,26} both; {20,26} miss, fraction 0.5 | `test_slot_rule_strict_and_lenient` (source and section level) |
| points-covered yes/partial/no + optional no → 0.5 | `test_points_covered_required_yes_partial_no_optional_ignored` |
| latency percentiles on a known list; retried excluded | `test_nearest_rank_textbook_example`, `test_retried_and_fallback_records_are_excluded_from_the_main_table` |
| judge fake LLM / cache / malformed JSON | **not in scope** (no judge code); 09b proper |
| (task) every answerable case ≥ 1 span per slot | `test_every_answerable_case_has_a_non_empty_span_in_every_slot` (also requires `char_end > char_start` and an expected span per slot) |

### evidence_hit_via_alternate_only (owner follow-up after verify, `943f063`)

`evidence_hit_via_alternate_only_at_k(chunks, point_quotes, spans, k)` is a per-case diagnostic; the headline is unchanged. It returns 1 when `evidence_hit_at_k` is 1 **and** every required point was satisfied only by top-k chunks outside the expected spans. Here "outside" means the chunk overlaps no span with role `expected` (same `source_id`, half-open offset overlap). A point also counts as "inside" when a top-k chunk that overlaps an expected span contains one of its quotes. The top k are cut first and split afterwards. Interpretation note: "every hit point" is read as "every required point, and evidence_hit is 1"; a case with no evidence hit scores 0.

Count on the current data. There is no runner and no retrieval output yet, so this is **simulated alternate-only retrieval**: for each arm and each answerable case, every chunk of `arm-{a,b}.jsonl` that overlaps no expected span of the case is passed to the real functions, with `k` = the number of those chunks. Script `alt_only.py` in the job's tmp directory, not committed; run from the worktree root with `PYTHONPATH="src;."`. Real output:
```
answerable cases: 32
  arm A Q-EVAL-003: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm A Q-EVAL-004: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm A Q-EVAL-007: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm A Q-EVAL-008: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
arm A: 733 chunks; evidence_hit_via_alternate_only count = 4 / 32: ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
  arm B Q-EVAL-003: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm B Q-EVAL-004: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm B Q-EVAL-007: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
  arm B Q-EVAL-008: evidence@all=1 via_alt_only=1 lenient section=1 strict section=0
arm B: 859 chunks; evidence_hit_via_alternate_only count = 4 / 32: ['Q-EVAL-003', 'Q-EVAL-004', 'Q-EVAL-007', 'Q-EVAL-008']
```
This equals the owner's expected set and the verifier's finding. The other 28 cases cannot be evidence-hit without a chunk that overlaps an expected span. When 09b reports real runs, it should report this count per arm next to evidence_hit and strict section hit.

## Frozen files at the end

```
3436870ef02dfc2c25bd9d403ec6c8dd44cb46dfacbf02d586161dedd1252937  eval-v1.jsonl
37d349e5a7fa43a179755d1c7993ef5a8438954f995bedcaee07bcfbf4da21d6  dev-v1.jsonl
```
Both equal `docs/snapshots/evaluation/eval-v1.md`. `git diff origin/dev --` on both files is empty. `expected-spans-v1.json` records `eval-v1.jsonl` = `3436870e…2937` and `normalized.jsonl` = `a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95`; a test rebuilds the file and compares parsed JSON, so a stale file fails.

## GitNexus

All changes are new files; no existing symbol was edited, so no impact analysis was needed (`_common.md`). `gitnexus_detect_changes` was run before the first commit but cannot see this worktree: the index `Tech-docs-RAG` is registered for the main checkout (currently on `rag-001b`). The compare against `origin/dev` returned risk "high" with 223 changed symbols in 20 files, **all from the other session's `rag-001b` work** (Chroma store, embedder, index_corpus, …) and none from this branch. `git diff --name-status origin/dev` on this branch lists only the 13 added files above. Because the index cannot see this worktree, `detect_changes` was not re-run before commits 2–4 (`0125683`, `afd7007`, the report commits) or the evidence_hit follow-up (`240f948`, which modified only this branch's own `retrieval.py` and its test file); `git diff --name-status` was the scope check instead (only added files, no modified ones). Post-verify follow-up: `detect_changes` was tried again before `943f063` and returned `Repository "…\worktrees\eval-003b-pre" not found`. The commit changes only this branch's own files: `retrieval.py` (new function + module docstring), its test file, and one trailing comment each in `stats.py` (inside `percentile_interval`'s tail line) and `test_eval_stats.py` (inside the bootstrap-rank test). `git diff fd59109 943f063` on those two files shows only the comment text changing (the float repr, now `2.500000000000002`), with no code token changed. No existing code was changed, so no impact analysis was run. The report commit also modifies `AI_WORKLOG.md` and `task-ledger.md` (owner-authorized, docs only). Merge `bebf486`: `detect_changes` (compare against `origin/dev`) was tried again and returned the same "not found". The merge adds dev's own reviewed code without changes, and its only hand-resolved file is `AI_WORKLOG.md`. The report commit after it changes docs only.

## Unverified / open

- evidence_hit headline: decided by the owner (item 5; kept after verify, option (a)). evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside. The alternate-only diagnostic is 4 / 32 on simulated alternate-only retrieval (003, 004, 007, 008). The evaluation spec and CHANGELOG do not record the rule yet; the owner lines are below.
- Verifier fix 4 (add the verifier's Windows exit `3221225773` observation to the anomaly note): not in the owner's first follow-up list. It was applied later, in the owner's pre-re-verify instruction, and now appears in § Anomaly, linked to today's truncated run at about 70 %.
- Refusal-check JSON key, latency record shape, `RankedChunk` adapter: to be fixed by 09b proper / EVAL-003a (items 7, 8, 11).
- No metric has been run on real retrieval output (no runner yet). Correctness rests on the hand-computed tests and the mutation proofs.
- The two truncated pytest runs (see Anomaly).

## Explain it back

- **Why offsets, not heading strings:** a hit is "same document and the chunk's `[start, end)` overlaps the expected section's span". Heading paths lie in both arms (Arm A names a merged section after its first heading, Arm B after the nearest one), so comparing strings would favour or penalise one arm for its labelling, not its retrieval. Half-open ranges make touching chunks (`[0,10)`, `[10,20)`) a miss, so a chunk that ends exactly where the section starts gets no credit.
- **Why slots plus strict/lenient:** a cross-document question needs evidence from every document, so "all slots, any source within a slot" stops one document from counting as a full hit. Lenient accepts owner-approved alternates (the headline); strict removes them, so a verifier can see whether a conclusion depends on the widened ground truth. If Arm A wins lenient but loses strict, EXP-001 must say so.
- **Why paired tests:** both arms answer the same 32 answerable cases, so the question difficulty cancels out. McNemar looks only at the cases where the arms disagree (b vs c); the bootstrap resamples whole cases, not each arm separately (the M3 mutation shows the interval blowing up to [-19, 21] when pairs are broken). Alternative: unpaired tests (chi-square, two-sample t) ignore the pairing and need far more cases to detect the same difference.
- **Why exact methods in plain Python:** scipy is not installed and n is small (≤ 36), so exact binomial and exact permutation distributions are cheap and avoid normal approximations that are poor at this n. Exact rational arithmetic in the percentile ranks avoids float off-by-one ranks (`14/100*50 = 7.000000000000001`).
- **Why evidence_hit is counted per required point:** a quote says *which* point it proves, so the question is "can every required point be proven from what was retrieved?". Any quote per point is enough (variants say the same thing). All required points must be covered, so a two-document case that retrieved only one document misses, while "any quote" would call it a hit. Optional points are ignored because a correct answer does not need them. The check is on content, not location: a quote found in an approved alternate section counts too. So evidence_hit sits with lenient section hit, and the alternate-only diagnostic plus strict section hit show when a hit came only from alternates (4 of 32 cases can).
- **Why the judge only supplies data:** the label comes from a fixed table in code, so the same judge output always gives the same label, a missing verdict is an error instead of a guess, and the table itself is unit-tested row by row. The judge's job is limited to judgments a table can't make (point coverage, contradiction, the D2 "presented as the answer" check).

## Lines for the owner to add at merge

The task itself did not touch shared docs. After verify, the owner asked for two shared-doc edits, and they are **applied on this branch**:
- `docs/plans/task-ledger.md`, row 09b, Notes: the proposed note that used to be here and the verifier's appended note are merged into one note. Status stays `not started`, and the note says "fixes applied, pending re-verify".
- `AI_WORKLOG.md`: the owner's entry about the repeated false assumption, placed under the verifier's 2026-09-26 EVAL-003b-pre section.

Still proposals only (not applied):

`docs/specs/evaluation-spec.md`, § Retrieval hit rule (after the strict/lenient bullet), evidence_hit rule and provenance note:
```
- **evidence_hit@k (owner, 2026-09-26).** Headline = per required point: every required answer point must have at least one of its supporting quotes (`evidence[].supports`) contained whole in some top-k chunk (all-of across required points, any-of across the quotes of one point; whitespace normalized as in `validate_questions.py`). Optional-point quotes are ignored. "Any quote of the case contained in a top-k chunk" is reported as a secondary diagnostic only. Corpus-insufficient cases are excluded.
  - evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside.
  - Diagnostic `evidence_hit_via_alternate_only` (per case, count per arm in the summary): 1 when evidence_hit is 1 and every required point was satisfied only by top-k chunks outside the expected spans. On eval-v1 with simulated alternate-only retrieval: 4 of 32 cases (Q-EVAL-003, 004, 007, 008).
```

`agents/prompts/CHANGELOG.md`, new row (and 09b §1 `evidence_hit@k` bullet reworded to match):
```
| 2026-09-26 | `09b-EVAL-003b-…` (+ `evaluation-spec.md` § Retrieval hit rule) | §1 `evidence_hit@k` defined per required point: every required answer point has ≥ 1 of its supporting quotes (`evidence[].supports`) whole in some top-k chunk; optional-point quotes ignored; "any quote" kept as a secondary diagnostic only. evidence_hit is content-level: a required point counts if a supporting quote appears whole in any top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient section hit, not strict. Strict section hit is reported alongside. New diagnostic `evidence_hit_via_alternate_only` (4 of 32 eval-v1 cases can score it: 003, 004, 007, 008). | "Contains the evidence quote" (singular) was ambiguous for cases with several quotes; "any quote" let a two-slot case score a hit with one slot missing (EVAL-003b-pre decision 5); verify showed alternate-only retrieval can score evidence_hit (EVAL-003b-pre-verify C1) | Owner (2026-09-26) | `240f948`, `943f063` |
```

`AI_WORKLOG.md`, Log section:
```
### 2026-09-26 EVAL-003b-pre (commits `7e70180`, `0125683`, `afd7007`, `240f948`, `943f063`, report commits)
- *AI did:* pure retrieval metrics (source/section hit@1/3/5 strict + lenient, slot fraction, MRR lenient/strict/source, evidence_hit@k per required point + any-quote and alternate-only diagnostics, reusing `validate_questions.collapse_whitespace`), `expected-spans-v1.json` (36 cases, 120 spans), the 09b §3 result-mapping table, points-covered, nearest-rank latency summary, and exact McNemar / paired bootstrap / exact Wilcoxon in plain Python; 87 offline tests, 5 mutation proofs ([report](docs/reports/execution/EVAL-003b-pre.md)).
- *AI got wrong:* (1) a latency test claimed `0.1*30` is not exactly 3.0 in floats (it is), so the test proved nothing; (2) the bootstrap pairing test compared floats exactly and failed on summation noise; (3) the first bootstrap draft computed the 2.5 % tail in floats (`2.500000000000002`), which moves the lower bound by one rank; (4) the report draft listed per-file test counts (9/23/20/11) without checking them; (5) the report draft named the first normalized record "#04" (it is #01) and called 10 the "max variants for one section" (10 is the max spans in one slot; the corpus max per section is 8); (6) the report claimed no case can be evidence-hit from alternate sections alone (checked only where each quote was first located, not every occurrence), wrote the float tail with one digit more than Python prints, and showed M5 as "1 failed" from a single-test run.
- *How found:* (1) checked the claim in Python before committing; (2) the test run; (3) code review before running; (4) `pytest --collect-only` (real: 8/24/22/9/18); (5) the advisor review asked for every report number to be measured; a corpus-wide check script; (6) verify (EVAL-003b-pre-verify C1 on real Arm A/B chunks, plus two cosmetic findings).
- *Fix:* (1) replaced with a searched real counterexample (`14/100*50`); (2) `approx(abs=1e-9)`; (3) exact `Fraction` tail + a test pinning ranks 250/9750; (4)–(5) report corrected with measured values (and the no-nesting claim checked on all 636 sections); (6) wording replaced by the owner's content-level text, `evidence_hit_via_alternate_only` diagnostic + test (4/32 on both arms), float printed as Python prints it, M5 re-run on the whole file (5 failed).
- *Human decision:* owner allowed the work before 09a (2026-09-26). Owner decided evidence_hit = per required point (all-of points, any-of quotes, optional ignored; any-quote as diagnostic), 2026-09-26. The AI measured that 3 of 100 quotes lie only in alternate sections, which corrects the owner's "expected-source quotes only" note. Verify then showed that evidence_hit is content-level and aligns with lenient section hit, not strict: 4 of 32 cases can be evidence-hit from alternate sections alone. The owner kept the rule (option (a)) and added the `evidence_hit_via_alternate_only` diagnostic (`943f063`).
```

## Appendix — task prompt (verbatim)

```
Parallel task EVAL-003b-pre — pure metric + statistics functions.
Owner exception to the ledger prerequisite rule (2026-09-26): 09b formally needs 09a, but this part depends only on frozen
data (eval-v1, normalized.jsonl), not on the pipeline. When 09b proper runs later, it audits this work instead of redoing it.
Other sessions are running (RAG-001b indexing, GUI-001-pre) — stay out of their files.

Read agents/prompts/_common.md, agents/prompts/09b-EVAL-003b-metrics-and-judge.md (§1 retrieval, §3 mapping table,
§4 latency/refusal), agents/prompts/12-EXP-001-experiment-and-failure-analysis.md (§1 paired statistics),
docs/specs/evaluation-spec.md, docs/snapshots/evaluation/eval-v1.md.

Scope (pure functions + offline tests only):
1. application/evaluation/metrics/: expected-section spans from normalized.jsonl + eval-v1.jsonl (all variants, per slot,
   incl. alternates) → data/evaluation/questions/expected-spans-v1.json (+ test: every answerable case has ≥ 1 span per slot);
   source/section hit@1/3/5 strict and lenient, slot fraction, MRR (lenient + strict), evidence_hit@k using the same
   whitespace normalization as validate_questions.py (incl. U+00A0) — import and reuse that function, don't copy it.
2. The result-mapping table from 09b §3 as a pure function (judge verdict passed in as data; no judge/LLM code).
3. Latency summary (nearest-rank p50/p95; retried/fallback records excluded and counted separately).
4. application/evaluation/stats.py: exact McNemar (report b, c, p), paired bootstrap CI (10 000 resamples, fixed seed),
   Wilcoxon signed-rank — scipy only if already installed, otherwise plain Python.
5. Tests on hand-made records with hand-computed expected values: the 09b §5 list, the slot example S1={04}, S2={26,20}
   (top-k {04,20}: lenient hit, strict miss; {20,26}: miss, slot fraction 0.5), touching spans [0,10)/[10,20) = no overlap.
   Prove two key tests fail under mutation, then restore byte-for-byte.

Boundaries:
- Touch only application/evaluation/ (new files), its tests, and data/evaluation/questions/expected-spans-v1.json.
  Do NOT touch embeddings/, vector_store/, llm/, generation/, retrieval/, core/interfaces/, presentation/, scripts/ingestion/,
  the frozen question files, or shared docs (ledger, AI_WORKLOG, CHANGELOG, master plan).
- Everything else goes in docs/reports/execution/EVAL-003b-pre.md (incl. "Explain it back" and the exact ledger/worklog
  lines the owner should add at merge).
- No Gemini calls, no ChromaDB access. At the end, the frozen file hashes must still match docs/snapshots/evaluation/eval-v1.md.

Environment:
- Separate git worktree. It has no .venv: use "D:\Code\Python\Knowledge assistant\.venv\Scripts\python.exe" by absolute
  path, run from the worktree root with $env:PYTHONPATH="src" so tests import the worktree's src/. Do not create a venv
  or pip install anything.
- data/processed/ files may be missing in the worktree if git-ignored — if so, read them from the main checkout path
  read-only and say so in the report.
- Write text files with explicit newline="\n".

Git (do it yourself with git + gh; never force-push, never touch main):
- git fetch origin; branch eval-003b-pre from origin/dev inside the worktree; clean tree.
- Commit per milestone; push after each; tests green at every push.
- gh pr create --base dev --head eval-003b-pre. Do not merge. STOP.
```

## Appendix — owner decision on evidence_hit (verbatim, 2026-09-26)

```
Owner decision on evidence_hit (2026-09-26): headline = per required point — every required answer point must have at
least one of its supporting quotes (evidence[].supports) contained whole in some top-k chunk (all-of across required
points, any-of across quotes of the same point); optional-point quotes are ignored. Keep "any quote" as a secondary
diagnostic; drop require_all (or keep it only as an internal option, not reported).
Tests: Q-EVAL-023-style case (two variant quotes for one point → one found = hit); a two-slot case with only one slot's
quote found = miss; an optional-point quote missing = still hit. Mutation proof on the per-point rule.
Note in the report: evidence_hit uses expected-source quotes only, so it behaves like strict even when retrieval found an
approved alternate.
Add both items to your report's "lines for the owner" as a CHANGELOG/evaluation-spec note (do not edit shared docs).
Commit, push eval-003b-pre. STOP.
```

## Appendix — owner follow-up after verify (verbatim, 2026-09-26)

Grep note for re-verify: after this follow-up, a search for "strict-like" / "behaves like strict" / "alternate-section quotes alone" in this report finds only these places:
- decision 5, first correction bullet: it quotes the owner's original note;
- decision 5, "Corrected after verify" bullet: it names the withdrawn claim;
- the owner's verbatim texts in the two appendices.

No such line is left as a claim. A search for the float repr with one extra digit finds no line in `src/`, `tests/` or this report.

```
EVAL-003b-pre follow-up after verify (ACCEPT WITH FIXES). Branch eval-003b-pre, now at fd59109.
Owner decision on issue 1: option (a). Keep the per-required-point rule. Do not change the matching code.

1. Wording: remove every "strict-like" claim from the report and from the proposed evaluation-spec.md line.
   Replace it with:
   "evidence_hit is content-level: a required point counts if a supporting quote appears whole in any
   top-k chunk, including chunks from owner-approved alternate sections. It therefore aligns with lenient
   section hit, not strict. Strict section hit is reported alongside."
2. Diagnostic (reporting only; the headline stays unchanged):
   - Add evidence_hit_via_alternate_only per case, true when every hit point was satisfied only by
     chunks outside the expected spans.
   - Add its count to the summary. Expected on the current data: Q-EVAL-003, 004, 007, 008.
   - Add 1 unit test for it. No mutation proof is needed, since it is diagnostic only.
3. Cosmetics:
   - M5 output: show the real result of the whole test file (3 failures).
   - Print the float as Python prints it (2.500000000000002).
4. Housekeeping:
   - Merge the report's proposed 09b note with the verifier's appended note into ONE note in the task ledger.
   - AI_WORKLOG entry: "Same false assumption appeared twice (owner-side assistant, then this report):
     that evidence quotes exist only in expected sections. Caught by verify on real Arm A/B chunks."
5. Run the full offline suite and commit/push using the standard git block (no force).
   Do not merge. STOP for a limited re-verify.
```

## Appendix — owner instruction before re-verify (verbatim, 2026-09-26)

```
Before the re-verify:
1. Merge origin/dev into eval-003b-pre with a merge commit (no rebase, no force).
   Resolve AI_WORKLOG.md by keeping every entry from both sides, in chronological order. Delete nothing.
   If task-ledger.md conflicts: keep dev's rows and re-apply the 09b note.
2. Also apply verifier fix 4: add their Windows memory-error note (exit 3221225773, commit limit) to the report's anomalies section,
   and link it to today's truncated run at ~70%.
3. Run the full offline suite on the merged branch. The count must be dev's count + this task's new tests; report both numbers.
4. Push. Do not merge. STOP.
```

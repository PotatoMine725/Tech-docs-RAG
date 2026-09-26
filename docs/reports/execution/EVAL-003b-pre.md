# EVAL-003b-pre — pure metric + statistics functions (execution report)

Date: 2026-09-26. Branch `eval-003b-pre` from `origin/dev` (`f81faa5`), separate git worktree. Agent: Claude Code, Opus 5.5.

## Scope and entry condition

- **Owner exception to the ledger prerequisite rule (2026-09-26):** 09b formally needs 09a (EVAL-003a runner, `not started`). This part uses only frozen data (`eval-v1.jsonl`, `normalized.jsonl`) and no pipeline, so the owner allowed it to run in parallel. **When 09b proper runs, it audits this work instead of redoing it** (`_common.md` "Before you start" 4).
- In scope: 09b §1 retrieval metrics + expected spans, 09b §3 mapping table (judge verdict passed in as data), 09b §4 latency summary, 12-EXP-001 §1 paired statistics, and the matching 09b §5 tests.
- Out of scope (left for 09b proper / EXP-001): judge prompt and judge code (`judge.py`, `judge_v1.md`, `judge_run.py`), OD-12, citation metrics, answer/refusal rate aggregation, cost, breakdowns, the live judge call, `compare_arms.py`.
- Not touched: embeddings/, vector_store/, llm/, generation/, retrieval/, core/interfaces/, presentation/, scripts/, the frozen question files, shared docs (ledger, AI_WORKLOG, CHANGELOG, master plan). No Gemini calls, no ChromaDB access, no new dependency, no venv/pip.
- `data/processed/documents/normalized.jsonl` is tracked in git, so the worktree had its own copy: nothing was read from the main checkout.

## Files (all new)

| File | What |
|---|---|
| `src/knowledge_assistant/application/evaluation/metrics/__init__.py` | package docstring |
| `.../metrics/spans.py` | `ExpectedSpan`; `build_expected_spans()` — expected + alternate sections → all variant spans, grouped by slot, tagged `expected` / `alternate`; pure |
| `.../application/evaluation/build_expected_spans.py` | I/O wrapper: reads the two inputs, writes the JSON with both input SHA-256s in the header (`newline="\n"`) |
| `.../metrics/retrieval.py` | `RankedChunk`; `overlaps`; `source_hit_at_k` / `section_hit_at_k` (lenient + `strict=True`); `slot_fraction_at_k`; `reciprocal_rank` (section/source, lenient/strict); `evidence_hit_at_k` (any quote / `require_all`); `mean` |
| `.../metrics/mapping.py` | `map_result()` = the 09b §3 table; `JudgeVerdict` (data only); `JudgeVerdictMissing`; `is_grounded`; `points_covered` |
| `.../metrics/latency.py` | `nearest_rank`, `summarize_values`, `summarize_latency` (clean vs retried/fallback) |
| `.../application/evaluation/stats.py` | `mcnemar_exact`, `paired_bootstrap_ci`, `percentile_interval`, `wilcoxon_signed_rank` |
| `data/evaluation/questions/expected-spans-v1.json` | 36 cases, 120 spans (72 expected, 48 alternate), 0 empty spans |
| `tests/unit/application/test_eval_expected_spans.py` | 8 tests |
| `tests/unit/application/test_eval_retrieval_metrics.py` | 24 tests |
| `tests/unit/application/test_eval_result_mapping.py` | 22 tests |
| `tests/unit/application/test_eval_latency.py` | 9 tests |
| `tests/unit/application/test_eval_stats.py` | 18 tests |

(Collected items incl. parametrized cases, from `pytest --collect-only`: 8 + 24 + 22 + 9 + 18 = 81 new.)

## Design decisions (and what 09b proper must confirm)

1. **Hits on offsets only.** A chunk hits a span when `source_id` matches and the half-open ranges overlap (`max(starts) < min(ends)`). The chunk's heading path is never compared: Arm A labels a merged section with its first heading (ADR-0003 D3), Arm B uses the nearest heading (D5). Verified for the real data: `display_text == normalized_text[char_start:char_end]` for all 733 Arm A and 859 Arm B chunks.
2. **Section spans are "own text" spans.** `normalized.jsonl` sections do not nest: a parent's span ends where its first child heading starts (e.g. #04 H1 `[0, 7556)`, first H2 `[7556, 10849)`). So an expected H1 section is hit only by a chunk overlapping the H1 intro, not by a chunk in one of its subsections. This matches the slot design (BP-EVAL-017: S1 = the #11 intro, S2 = `IMiddleware`) but 09b proper should state it in the metric definitions.
3. **All variants, `evidence_variant` ignored for spans.** Every variant of a heading path becomes a span (ADR-0003 D8: any variant counts); `evidence_variant` only restricts where the evidence *quote* was checked by `validate_questions.py`. Max 10 variants for one section (#13/#17/#23 style repeats).
4. **Strict = role `expected` only.** Every slot of every answerable case has at least one expected span (tested), so strict hit is always computable.
5. **evidence_hit with several quotes — DECISION REQUIRED (09b proper).** Cases have several evidence quotes (multi-slot cases have quotes in different slots). 09b says "contains the evidence quote" (singular). Implemented: headline = any quote contained whole in one top-k chunk (literal reading); `require_all=True` = every quote contained whole in some top-k chunk. Note: under the "any" reading `evidence_hit` can be 1 while `section_hit` is 0 for a multi-slot case, which conflicts with 09b calling it "the strictest check". Options: (a) keep "any" as headline, report "all" beside it; (b) make "all" the headline (strictest, matches EXP-001's "chunking" failure stage); (c) per slot. Recommendation: (b) all-quotes as headline, any-quote secondary — owner to decide.
6. **Whitespace normalization is imported, not copied.** `retrieval.py` does `from scripts.evaluation.validate_questions import collapse_whitespace` (owner instruction). Works because pytest's `pythonpath = ["src", "."]` and `scripts/` is a namespace package; importing the module does no I/O. A test pins the provenance (`co_filename` ends with `scripts/evaluation/validate_questions.py`). **Coupling:** application code now depends on a CLI script module, and running it needs the repo root on `sys.path`. Follow-up (needs a `scripts/` edit, out of scope here): move `collapse_whitespace` into `application/evaluation/` and let `validate_questions.py` import it.
7. **Mapping takes the judge verdict as data.** The 09b judge JSON schema has no field for the D2 refusal check; here it is the named boolean `JudgeVerdict.presents_related_as_answer`. 09b proper owns the JSON key. A verdict the table needs but did not get raises `JudgeVerdictMissing` (caller records `judge_error`, never a guessed label). Zero required points or an unknown coverage value raise. Contradiction wins over full coverage (`yes, yes` + contradiction → `incorrect`). Unsupported claims change only groundedness, not the label.
8. **Latency record shape is assumed** (EVAL-003a does not exist yet): `{"latency_ms": {stage: float|None}, "retry_count": int, "fallback_used": bool}`. Main table = `retry_count == 0 and not fallback_used`; missing/None stage values are skipped per stage. Nearest-rank percentiles use an exact rational rank (`Fraction`): in floats `14/100*50 = 7.000000000000001` would give rank 8 instead of 7 (tested).
9. **Statistics conventions.** Δ = B − A everywhere. McNemar `b` = A-only successes (A=1, B=0), `c` = B-only (A=0, B=1); p exact two-sided binomial, capped at 1. Bootstrap resamples case *indices* (pairs together) with `random.Random(42)`, 10 000 resamples, bounds = nearest-rank 2.5th/97.5th percentiles (tail computed exactly: `(1-0.95)/2*100` is `2.5000000000000022` in floats and would move the bound from rank 250 to 251; tested). Wilcoxon: zeros dropped, average ranks for ties (|d| rounded to 12 decimals so float noise ties), exact permutation distribution over doubled ranks. **Difference from scipy:** with ties scipy switches to a normal approximation; this implementation stays exact, so tied cases can differ slightly from scipy.
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
| Frozen hashes at the end | `Get-FileHash` + `git diff origin/dev -- <both files>` | unchanged (see below), diff empty |

Anomaly (unexplained, reported honestly): one full run with `-rfE`, piped to a file, stopped at about 60 % with exit code 1 and no failure or summary line. The next verbose run and two quiet runs all exited 0 with `267 passed`. No test failure was ever shown; the likely cause is the environment (another session's job on this machine was killed for low memory earlier the same day), but this is **unverified**.

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

### 09b §5 test list → where it is covered

| 09b §5 item | Test |
|---|---|
| section hit via overlap, touching `[0,10)`/`[10,20)` = no overlap, multiple variants | `test_touching_half_open_spans_do_not_overlap`, `test_section_hit_touching_chunk_is_a_miss`, `test_section_hit_any_variant_counts` (+ other-document miss) |
| MRR rank 3 = 0.333…, no hit = 0, strict MRR alternate@1 / expected@3 → 1.0 / 0.333… | `test_reciprocal_rank_hit_at_rank_3`, `…_no_hit_is_zero`, `test_strict_mrr_alternate_at_rank_1_expected_at_rank_3` |
| evidence_hit false when split across two chunks | `test_evidence_hit_false_when_the_quote_is_split_across_two_chunks` |
| evidence_hit true across whitespace (spaces, newlines, U+00A0), Q-EVAL-028 / #18 | `test_evidence_hit_ignores_whitespace_differences`, `test_evidence_hit_real_case_q_eval_028_no_break_space_in_source_18` (real Arm A chunk) |
| every mapping row, both refusal-check outcomes | `test_eval_result_mapping.py` (all 7 rows) |
| slots S1={04}, S2={26, 20 alt}: {04,20} lenient hit/strict miss; {04,26} both; {20,26} miss, fraction 0.5 | `test_slot_rule_strict_and_lenient` (source and section level) |
| points-covered yes/partial/no + optional no → 0.5 | `test_points_covered_required_yes_partial_no_optional_ignored` |
| latency percentiles on a known list; retried excluded | `test_nearest_rank_textbook_example`, `test_retried_and_fallback_records_are_excluded_from_the_main_table` |
| judge fake LLM / cache / malformed JSON | **not in scope** (no judge code); 09b proper |
| (task) every answerable case ≥ 1 span per slot | `test_every_answerable_case_has_a_non_empty_span_in_every_slot` (also requires `char_end > char_start` and an expected span per slot) |

## Frozen files at the end

```
3436870ef02dfc2c25bd9d403ec6c8dd44cb46dfacbf02d586161dedd1252937  eval-v1.jsonl
37d349e5a7fa43a179755d1c7993ef5a8438954f995bedcaee07bcfbf4da21d6  dev-v1.jsonl
```
Both equal `docs/snapshots/evaluation/eval-v1.md`. `git diff origin/dev --` on both files is empty. `expected-spans-v1.json` records `eval-v1.jsonl` = `3436870e…2937` and `normalized.jsonl` = `a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95`; a test rebuilds the file and compares parsed JSON, so a stale file fails.

## GitNexus

All changes are new files; no existing symbol was edited, so no impact analysis was needed (`_common.md`). `gitnexus_detect_changes` was run before the first commit but cannot see this worktree: the index `Tech-docs-RAG` is registered for the main checkout (currently on `rag-001b`). The compare against `origin/dev` returned risk "high" with 223 changed symbols in 20 files, **all from the other session's `rag-001b` work** (Chroma store, embedder, index_corpus, …) and none from this branch. `git diff --name-status origin/dev` on this branch lists only the 13 added files above.

## Unverified / open

- evidence_hit headline (any vs all quotes): **DECISION REQUIRED** (item 5).
- Refusal-check JSON key, latency record shape, `RankedChunk` adapter: to be fixed by 09b proper / EVAL-003a (items 7, 8, 11).
- No metric has been run on real retrieval output (no runner yet). Correctness rests on the hand-computed tests and the mutation proofs.
- The one truncated pytest run (see Anomaly).

## Explain it back

- **Why offsets, not heading strings:** a hit is "same document and the chunk's `[start, end)` overlaps the expected section's span". Heading paths lie in both arms (Arm A names a merged section after its first heading, Arm B after the nearest one), so comparing strings would favour or penalise one arm for its labelling, not its retrieval. Half-open ranges make touching chunks (`[0,10)`, `[10,20)`) a miss, so a chunk that ends exactly where the section starts gets no credit.
- **Why slots plus strict/lenient:** a cross-document question needs evidence from every document, so "all slots, any source within a slot" stops one document from counting as a full hit. Lenient accepts owner-approved alternates (the headline); strict removes them, so a verifier can see whether a conclusion depends on the widened ground truth. If Arm A wins lenient but loses strict, EXP-001 must say so.
- **Why paired tests:** both arms answer the same 32 answerable cases, so the question difficulty cancels out. McNemar looks only at the cases where the arms disagree (b vs c); the bootstrap resamples whole cases, not each arm separately (the M3 mutation shows the interval blowing up to [-19, 21] when pairs are broken). Alternative: unpaired tests (chi-square, two-sample t) ignore the pairing and need far more cases to detect the same difference.
- **Why exact methods in plain Python:** scipy is not installed and n is small (≤ 36), so exact binomial and exact permutation distributions are cheap and avoid normal approximations that are poor at this n. Exact rational arithmetic in the percentile ranks avoids float off-by-one ranks (`14/100*50 = 7.000000000000001`).
- **Why the judge only supplies data:** the label comes from a fixed table in code, so the same judge output always gives the same label, a missing verdict is an error instead of a guess, and the table itself is unit-tested row by row. The judge's job is limited to judgments a table can't make (point coverage, contradiction, the D2 "presented as the answer" check).

## Lines for the owner to add at merge (shared docs were not touched)

`docs/plans/task-ledger.md`, row 09b, Notes column (status stays `not started` until 09b proper runs):
```
Pre-work EVAL-003b-pre (owner exception 2026-09-26, parallel to 09a): pure retrieval metrics + expected-spans-v1.json, §3 mapping, §4 latency, EXP-001 §1 stats; `7e70180`, `0125683`, `afd7007` + report; [EVAL-003b-pre](../reports/execution/EVAL-003b-pre.md). 09b proper audits it instead of redoing it. Open: evidence_hit any-vs-all headline (DECISION REQUIRED), refusal-check JSON key, latency record shape.
```

`AI_WORKLOG.md`, Log section:
```
### 2026-09-26 EVAL-003b-pre (commits `7e70180`, `0125683`, `afd7007`, report commit)
- *AI did:* pure retrieval metrics (source/section hit@1/3/5 strict + lenient, slot fraction, MRR lenient/strict/source, evidence_hit@k reusing `validate_questions.collapse_whitespace`), `expected-spans-v1.json` (36 cases, 120 spans), the 09b §3 result-mapping table, points-covered, nearest-rank latency summary, and exact McNemar / paired bootstrap / exact Wilcoxon in plain Python; 81 offline tests, 3 mutation proofs ([report](docs/reports/execution/EVAL-003b-pre.md)).
- *AI got wrong:* (1) a latency test claimed `0.1*30` is not exactly 3.0 in floats (it is), so the test proved nothing; (2) the bootstrap pairing test compared floats exactly and failed on summation noise; (3) the first bootstrap draft computed the 2.5 % tail in floats (`2.5000000000000022`), which moves the lower bound by one rank.
- *How found:* (1) checked the claim in Python before committing; (2) the test run; (3) code review before running.
- *Fix:* (1) replaced with a searched real counterexample (`14/100*50`); (2) `approx(abs=1e-9)`; (3) exact `Fraction` tail + a test pinning ranks 250/9750.
- *Human decision:* owner allowed the work before 09a (2026-09-26). Pending: evidence_hit any-vs-all headline.
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

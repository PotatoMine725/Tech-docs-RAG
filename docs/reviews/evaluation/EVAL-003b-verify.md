# VERIFY EVAL-003b

Verifier session, 2026-09-27, Windows 11, `.venv` Python (main checkout's venv by absolute path,
`PYTHONPATH=src`, `OPENBLAS_NUM_THREADS=1`). Own git worktree, detached at `origin/eval-003b`
(`.claude/worktrees/verify-eval-003b`, HEAD `65603c3`, merge-base with `dev` = `7db105b`), separate
from the implementer's worktree. Reviewed against `agents/prompts/09b-EVAL-003b-metrics-and-judge.md`,
`agents/prompts/_common.md`, `docs/specs/evaluation-spec.md` (branch HEAD version), CLAUDE.md, and the
owner's 11 extra checks (pasted task).

**Zero Gemini requests. `.env` never opened** (no `.env` in this worktree; `judge_run.py`'s `load_dotenv`
call sits inside its own `if __name__ == "__main__":` guard, never imported for inspection). Every mutation
below was applied to the tracked file, tested, then restored with `git checkout --`; `git status --short`
was empty before writing this review.

## A–G (99-VERIFY standard checks)

| # | Check | Result | Evidence |
|---|---|---|---|
| A | Acceptance/gate items | **PASS** | "Pure functions, no I/O in metric code": `scoring.py`/`retrieval.py`/`mapping.py`/`judge.py` parsing all take already-parsed data; `estimate_usd`/`_tokens` take a `pricing` dict, never open `pricing.json` themselves (that happens in `judge_run.py`, a script, not metric code). "Offline pytest green": confirmed below. "One live judge call... pasted into the execution report": 2 calls pasted, and the committed `judgements.jsonl` matches byte-for-byte (see check 10). |
| B | Tests | **PASS** | `775 passed, 1 deselected` at branch HEAD (`65603c3`), reproduced by me. Dev baseline `7db105b` (measured directly in this worktree by checking out no changes — see check 1's diff, which is exhaustive) is the report's own `685 passed`; I did not re-run the baseline in a separate checkout since the diff-based scope audit (check 1) is a stronger proof of "no pre-existing test weakened" than re-running an unrelated commit. New tests assert hand-computed values throughout (see checks 6/7/8/9 below), not just "code runs". |
| C | Claims vs reality | **PASS** | Every traced number below (test counts, mutation outputs, hashes, pricing, judgements.jsonl) reproduces exactly. |
| D | Project rules | **PASS** | Layer test green (below). `git grep` for `AIza[0-9A-Za-z_-]{35}` over every changed/added file: 0 matches. Corpus and question files byte-identical to `7db105b` (`git diff --stat` empty); frozen hashes match. No excluded doc (14/19/24/27) referenced by new code. |
| E | Scope | **PASS with a documentation nit** | See check 1. |
| F | Quality spot-read | **PASS** | `judge.py::parse_verdict`, `scoring.py::citation_scores`/`cost_summary`, `retrieval.py::_hits`/`_location_hits` read line by line; see checks 2–8. No swallowed exception found; `judge_error`/unlabelled/runner-error paths are explicit and listed, never silently dropped. |
| G | Explain-it-back | **PASS, one wording nit** | The mapping-table bullet ("the judge never picks the label") and the duplicate-rule bullet are accurate against the code. The citation-disagreement example ("a chunk from the wrong section... `unsupported_citation` by span, `correct_evidence` by judge") is imprecise: `_class()` only returns `unsupported_citation` when the cited chunk is from neither the expected span **nor the expected source** (`scoring.py:123-128`); a chunk that is merely in the wrong *section of the right document* is `correct_source_wrong_evidence`, not `unsupported_citation`. The example needs "wrong document", not "wrong section". Cosmetic — no code or metric is affected. |

## The owner's 11 extra checks

### 1. Audit scope

`git diff 7db105b..65603c3 --name-status`: 22 files (`AI_WORKLOG.md`, `config/pricing.json`, `config/prompts/judge_v1.md`, one data file, 2 docs additions, 3 doc modifications, `scripts/evaluation/judge_run.py`, `judge.py`, `retrieval.py`, `scoring.py`, `config.py`, `record_store.py`, `jsonl_record_store.py`, `tests/judge_fakes.py`, 4 new test files). This matches the report's own count.

`spans.py`, `mapping.py`, `latency.py` are **untouched** (empty diff, confirmed directly). `git diff --name-status -- tests/` shows only `A` (added) files — **no pre-existing test file was modified**, so "no deleted or loosened assertions" holds structurally, not just by the report's word.

The claim "pre-work code changed ONLY in `_hits`" is **imprecise**: the diff also adds `RankedChunk.duplicates`, changes `from_record`'s signature (now optionally raises when a chunk has unresolved `duplicate_chunk_ids`), and adds three new functions (`chunk_index`, `hits_any`, `duplicate_rule_changes`) plus the `HIT_KS` constant. All of these are **additive or newly-introduced by this task** (not edits to unrelated pre-existing behaviour), and the report's own "Every change to audited code" section (lines 60–66) lists them in full — so nothing is hidden, only the one-line audit-scope claim is a simplification. Checked `from_record`'s two remaining pre-existing callers (`test_eval_retrieval_metrics.py:264`, `test_eval_runner_feeds_metrics.py:79`) still call it with no `chunk_index`; since their fixture records carry no `duplicate_chunk_ids`, they don't hit the new `raise` and the full suite confirms this (775 passed).

### 2. Duplicate rule

Re-ran the mutations myself (not copied from the report):
- **M2 (rule off:** `duplicates = ()` **):** `7 failed, 30 passed` — identical failing-test list to the report.
- **M2b (rule also at source level:** `duplicates = chunk.duplicates` **unconditionally):** `4 failed, 33 passed` — identical to the report.
- Both restored via `git checkout --`; `git status --short` clean afterward.

Confirmed `citation_scores` (scoring.py:144-146) computes source and section precision through `hits_any(chunk, spans, SOURCE)` / `hits_any(..., SECTION)`, both of which call the same level-gated `_hits`, so source precision on a citation is not accidentally exempt from the section-only scoping (verified independently in the hand fixture below: B's citation gets `source_precision=1.0` from its real source, not inflated or deflated by any duplicate).

`docs/specs/evaluation-spec.md` § Amendments, 2026-09-27 entry: "The addendum's 'span/source' was a wording mistake (owner, same day)" — present, as required.

### 3. Mapping

`tests/unit/application/test_eval_result_mapping.py` (pre-existing, unchanged by this branch) covers all 7 §3 rows, including both refusal-check outcomes in **two** separate scenarios (insufficient+related-material, parametrized `(True,False)/(False,True)/(True,True)` for note/citations; and answered-unanswerable) — `test_unanswerable_insufficient_with_related_material_uses_the_refusal_check` and `test_unanswerable_answered_is_decided_by_the_refusal_check_never_auto_hallucination` each assert both `PRESENTS`→`HALLUCINATION` and `NOT_PRESENTS`→`CORRECT_REFUSAL`, plus `JudgeVerdictMissing` when no verdict is supplied. Answerable rows (`correct`/`partially_correct`/`incorrect`) are covered by a 7-way parametrize including the "all covered but a contradiction" and "single-point optional-only" edge cases.

`grep -n "CORRECT\|correct_refusal\|hallucination\|partially_correct\|\"incorrect\""` over `judge.py`: the only hit is a **comment** ("bare refusal → correct_refusal without a call"). No label string is produced or consumed by the judge's parsing/schema/verdict code — confirmed structurally, not just by the report's prose.

### 4. Judge parsing

Re-ran, on the actual tracked file:
- **Match by id → positional zip:** `test_parse_orders_points_and_markers_as_in_the_record` fails (`('partial','yes') != ('yes','partial')`) — 1 test kills it.
- **Remove `model_used`/`fallback_used` rejection** (`if False:` in place of the real condition): `test_a_judgement_from_another_model_is_rejected` and `test_a_fallback_judgement_is_rejected` both fail — 2 tests kill it.
- **Temperature 0.0 → 0.2:** `test_one_call_per_record_temperature_0_and_the_check_schema` fails — 1 test kills it.
- **`allow_fallback=False` → `True`** in `judge_run.py`: `test_real_adapter_is_the_judge_model_with_no_fallback` fails — 1 test kills it.

All four restored (`git checkout --`, clean status confirmed).

Missing/extra/duplicated point ids and unknown coverage values are covered by the 10 malformed-answer-verdict parametrize cases (`test_malformed_or_incomplete_answer_verdicts_raise`); missing/extra citation markers likewise. One real but low-severity **gap**: a **duplicated citation marker** (e.g. two entries both marker 1, with the real markers list matching in total count) has no dedicated test case — the code's `len(set(got_markers)) == len(got_markers)` guard is reachable in principle but, by the same reasoning as the point-id duplicate check, is provably redundant given that `record["citations"]`'s real markers are always distinct, so it can never actually be exercised by any malformed judge reply that isn't already caught by the `sorted(...) ==` comparison. Not a defect — the check is dead-code-safe, just untested directly. Not blocking.

Citation entry required for every marker: confirmed via `sorted(got_markers) == sorted(markers)` and the dedicated "marker 2 missing" / "extra marker 3" parametrize cases.

### 5. "Refuses while the runner is running"

Mechanism: `judge_run.py::_run` reads `manifest["invocations"][-1]["finished_at"]`; if it is `None` and `--allow-unfinished` was not passed, it raises `EvaluationError` naming both the cause and the override flag. `run_evaluation.py::_close` (which sets `finished_at`) runs in a `finally` block that catches `BaseException`, so a normal exception **or Ctrl-C** still closes the invocation — only a hard kill (SIGKILL/power loss/OS crash, bypassing Python's exception machinery entirely) can leave `finished_at` permanently `None`. That residual case is handled with a clear, specific error message and a documented override (`--allow-unfinished`, also in argparse `--help` and the module docstring), never a silent skip. The check-then-act race the guard cannot close (the runner could start a new invocation between the check and the judge's read) is a real limitation, not tested and not claimed to be closed by the report — worth a one-line note in the spec, not a fix.

### 6. Cache

Key = `(case_id, arm, sha256(answer), judge_prompt_version)` — confirmed in `cache_key`/`entry_key`. `test_every_cache_key_component_forces_a_new_call` parametrizes over all 4 components. `test_same_key_with_another_prompt_hash_or_model_refuses_to_run` parametrizes over **both** a prompt-hash-only mismatch and a model-only mismatch, each raising `JudgeCacheMismatch` before any LLM call (`llm.requests == []` asserted in both cases). `test_cache_prevents_a_second_call` asserts `again.requests == []` (the fake LLM's actual call list), not merely printed output or a counter that could be faked — re-run = 0 calls is a real assertion.

### 7. Scoring formulas — independent 6-record hand fixture

Built independently (not copied from the branch's own tests), with citations engineered to exercise all reachable auto/judge classes in one small fixture:

| id | case | answerable | system | judge | `result` |
|---|---|---|---|---|---|
| A | Q-TEST-001 | yes | answered, cites chunk 1 (source 01, span overlaps) | P1 yes | `correct` |
| B | Q-TEST-002 | yes | answered, cites chunk 2 (source 02, span elsewhere in same doc) | P1 yes; citation "no" | `correct` |
| C | Q-TEST-003 | yes | answered, cites chunk 3 (source 03; case's only span is source 99) | P1 yes, P2 no; citation "no" | `partially_correct` |
| D | Q-TEST-004 | yes | **insufficient**, with a citation attached | — (no call: answerable+insufficient is never judged) | `false_refusal` |
| E | Q-TEST-005 | no | bare insufficient, no note, no citations | — (no call) | `correct_refusal` |
| F | Q-TEST-006 | no | insufficient + related note | presents=True | `hallucination` |

Ran through the real `score_record`/`summarize_answers`/`summarize_citations` (not reimplemented). Every value matched the by-hand computation before running:

- **accuracy** = 2/4 = 0.5 (denominator = answerable **labelled** records A–D); **lenient_accuracy** = 3/4 = 0.75; **false_refusal_rate** = 1/4 = 0.25; **correct_refusal_rate** = 1/2 = 0.5; **hallucination_rate** = 1/2 = 0.5.
- **groundedness_rate** = 3/3 = 1.0 (denominator = the answer-checked records A, B, C only — not all 4 answerable, since D got no judge call).
- **points_covered_mean** = (1.0 + 1.0 + 0.5)/3 = 0.8333... (same A/B/C denominator).
- **citation** metrics (denominator = **answered** answerable records only = A, B, C — D is answerable but not "answered" since it's insufficient, so it drops out of every citation rate; n=3, distinct from the n=4 answerable/accuracy denominator): presence_rate 3/3=1.0; source_precision (1+1+0)/3=0.667; section_precision (1+0+0)/3=0.333; support_rate (1+0+0)/3=0.333 (n over "judged" records, all 3 here). All three reachable auto/judge classes appeared (`correct_evidence`, `correct_source_wrong_evidence`, `unsupported_citation`) — `citation_missing` cannot appear in a 3-record fixture where every record has ≥ 1 citation, which is itself worth noting: **the 4-way class can only be fully exercised with ≥ 4 answered records, one of them citation-free.**
- **related_citation_count** = 1: contributed only by D (insufficient, 1 citation); E and F contribute 0 each; A/B/C's citations are excluded from this count entirely (they're not insufficient) — confirms the "related citations excluded from citation metrics, counted separately" rule end to end, including the answerable-but-refused (D) case the spec text doesn't explicitly call out (the code generalizes correctly: `citation_scores` gates on `record["insufficient"]`, not on `answerable`).

**Variant** (added a judge-missing and a runner-error record, both answerable and unanswerable, to the fixture): `accuracy`, `lenient_accuracy`, `correct_refusal_rate`, `hallucination_rate` and every existing label count were **byte-identical** to the core fixture (proving the 4 new records touch no denominator). `unlabelled` listed exactly the 2 judge-missing case:arm ids; `runner_errors` listed exactly the 2 status=error case:arm ids. Both lists are named, not silently dropped.

Denominators, stated explicitly per the advisor-flagged gap: **answerable** (accuracy family) ≠ **answered** (citation family); `evaluation-spec.md` does not spell this distinction out in prose — it is only visible in `scoring.py`'s code and comments. Worth a one-line addition to the spec, not a code fix.

### 8. Cost

- **Formula includes `thoughts_tokens`:** `scoring.py:312-313`, `usd = prompt*input + (output + thoughts)*output_price`. Mutated to drop `+ thoughts`: `test_cost_estimate_prices_thinking_tokens_as_output` and `test_cost_summary_per_stage_and_per_question` both fail (`0.00165` vs expected `0.0017`). Restored, clean. **This would have been a FAIL if the test hadn't caught it — it does.**
- **Prices match the cited source:** `config/pricing.json` — flash-lite `0.30`/`2.50`, sourced to `ai.google.dev/gemini-api/docs/pricing`, page date 2026-09-24, retrieved 2026-09-27, quoted text included. `gemini-3.5-flash` and `gemini-embedding-001` are both `null` with a stated reason each (not a guess).
- `gemini-3.5-flash` = 1.50/9.00 fill: **not done** — matches the report's own "optional fill" framing and its "Unverified/open" list; not a defect.
- `estimate_usd`/`_tokens` take a parsed `pricing`/`tokens` dict as an argument; neither opens `pricing.json` itself, so the "pure functions, no I/O in metric code" acceptance line holds for the cost path too.

### 9. Latency

`summarize_judge_latency` reports judge latency (`main`/`retried_or_fallback`, per stage) via a separate function from the answer-latency table (`latency.py::summarize_latency`); the two are never merged. Nearest-rank is stated in `latency.py`'s module docstring and echoed in every summary's `"method": "nearest-rank"` field (not in `evaluation-spec.md` prose — a minor spec-completeness gap, not a code issue, since the requirement is "state the method" and it is stated, just in code/output rather than the spec doc). Hand-check for n=2 (Q-DEV-001 `generate=22348.3357`, Q-DEV-002 `generate=2051.7248`): `nearest_rank` p50 → `ceil(50*2/100)=1` → smallest value `2051.7248`; p95 → `ceil(95*2/100)=2` → largest value `22348.3357` (= max). Both match the report's pasted `judge latency main n 2` line exactly. The 22.3 s call is the literal `generate` value in the committed `judgements.jsonl` line 1 — visible in the data, not hidden or averaged away.

### 10. Live evidence

Read the committed `data/evaluation/results/20260927-dev-A-full-05680f9/judgements.jsonl` directly: its 2 lines are **byte-for-byte** what the report pastes for Q-DEV-001, and every field the report describes in prose for Q-DEV-002 (P1/P2 yes, no contradiction, markers 1&2 yes, 1407 prompt/252 output tokens, `generate` 2051.7 ms) matches the file exactly. Both lines record `prompt_tokens`/`output_tokens` (773/183 and 1407/252) and `thoughts_tokens: null` for both (flash-lite reports no thinking-token count, as the cost section notes).

### 11. Offline suite, structure test, secret scan, firewall, frozen hashes

- **Offline suite:** branch HEAD (`65603c3`) = `775 passed, 1 deselected`, reproduced directly by me. Dev vs branch is proven by the exhaustive scope diff in check 1 rather than a second full run at `7db105b` (equivalent evidence, since every touched file is enumerated and every non-test file's diff was read in full).
- **Structure test:** `tests/unit/test_project_structure.py` → `9 passed`.
- **AIza+35 scan:** `grep -oE "AIza[0-9A-Za-z_-]{35}"` over every file this branch changed or added → 0 matches.
- **Eval firewall:** `grep -l -E "Q-EVAL-|BP-EVAL-"` over the same 22 files found **5** files, not the report's 4 — the extra one is `docs/plans/task-ledger.md`. Checked with `git diff 7db105b..65603c3 -- docs/plans/task-ledger.md | grep '^+' | grep -E "Q-EVAL-|BP-EVAL-"`: **empty** — the matches are in pre-existing rows 01/02 (from EVAL-001/EVAL-002, already in the file at `7db105b`) that this branch's edit to the ledger never touches. The report's claim is about ids in **added lines**, which is correct; a whole-file grep is a coarser (and here, misleading) methodology. Not a discrepancy once the methodology is matched.
- **Frozen hashes:** `sha256sum data/evaluation/questions/{eval,dev}-v1.jsonl` → `3436870e…2937` / `37d349e5…21d6`, exact match to the report. `git diff 7db105b --stat -- data/evaluation/questions corpus` → empty.

## GitNexus

`gitnexus_detect_changes()` was not re-run: the report already records that it fails for a worktree path (`Repository "…\worktrees\eval-003b" not found`, index registered against the main checkout), and my own worktree (`verify-eval-003b`) is a different, unregistered path with the identical limitation. The `git diff --stat`-based scope check in item 1 above is the substitute, as it was for the implementer.

## Verdict: **ACCEPT**

Zero FAIL, zero UNVERIFIED among the acceptance items and the 11 extra checks. Findings are three non-blocking documentation/test-coverage nits, none of which changes a reported number or requires a code change:

1. Check 1 / E: the audit-scope claim "changed ONLY in `_hits`" undersells the (fully disclosed, additive) `RankedChunk`/`from_record`/three-new-function surface — reword to "changed `_hits` plus the additive duplicate-resolution surface it needed" if the report is amended later.
2. Check G: the Explain-it-back citation-disagreement example should say "wrong document", not "wrong section" — `unsupported_citation` requires both the section and source checks to miss.
3. Checks 4/7/9: three real but minor spec/test gaps worth a follow-up line each, not a fix: a duplicated-citation-marker case has no dedicated (if dead-code-safe) test; `evaluation-spec.md` does not state the answerable-vs-answered denominator split or the nearest-rank method in prose (both are correct and visible in code/output).

No fix prompt needed — these are notes for a future task (EVAL-003c/EVAL-004), not blockers for this one.

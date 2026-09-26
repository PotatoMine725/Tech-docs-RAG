# VERIFY EVAL-003b-pre

Verifier session, 2026-09-26 (~14:20–14:50 UTC+7), Windows 11, `.venv` Python 3.13.3 (main checkout's venv by absolute path, `PYTHONPATH` = worktree `src` + worktree root). Reviewed branch `eval-003b-pre` at `8adeb71` (commits `7e70180`, `0125683`, `afd7007`, `22a439d`, `4c862a9`, `240f948`, `8adeb71`; PR #12 into `dev`, open, not draft) against the quoted task prompt (in `docs/reports/execution/EVAL-003b-pre.md`, no prompt-log file by design), `agents/prompts/09b-EVAL-003b-metrics-and-judge.md` §1/§3/§4/§5, `12-EXP-001` §1, `_common.md`, CLAUDE.md, and the owner's extra checks 1–6.

**Zero Gemini requests, no ChromaDB.** Only `data/processed/chunks/arm-{a,b}.jsonl` and `normalized.jsonl` (both tracked JSONL) were read.

Method: every number below comes from my own commands. My hand values for checks 2 and 4 were worked out from the printed offsets *before* running the code. Mutations were applied to a **scratch copy** (`$CLAUDE_JOB_DIR/tmp/mut`), never to the branch; `git status --short` on the worktree stayed empty. Scripts are in the job's `tmp/` and were not committed.

## A. Acceptance / gate items (task prompt + owner's extra checks)

| # | Item | Result | Evidence |
|---|---|---|---|
| Scope 1 | `git diff --name-status origin/dev...eval-003b-pre` lists only added files of this task | **PASS** | 14 lines, all `A`: `expected-spans-v1.json`, the report, `build_expected_spans.py`, `metrics/{__init__,latency,mapping,retrieval,spans}.py`, `stats.py`, and 5 test files. No `M`/`D`/`R`. Nothing under `embeddings/`, `vector_store/`, `llm/`, `generation/`, `retrieval/`, `core/`, `presentation/`, `scripts/`, the frozen question files, or shared docs. |
| Do 1 | Expected spans from `normalized.jsonl` + `eval-v1.jsonl`, all variants, per slot, incl. alternates → `expected-spans-v1.json`; test: ≥ 1 span per slot | **PASS** | My own rebuild (raw sections of `normalized.jsonl` matched by heading path, no code reuse) equals the file for all 36 cases, 120 spans (72 expected, 48 alternate), 0 empty slots, 0 insufficient cases with slots. Test `test_every_answerable_case_has_a_non_empty_span_in_every_slot`. |
| Do 1 | source/section hit@1/3/5 strict + lenient, slot fraction, MRR lenient + strict, `evidence_hit@k` with `validate_questions` whitespace normalization (imported, not copied) | **PASS** (see Extra 2, 3) | `retrieval.py:17` imports `collapse_whitespace`; `test_whitespace_normalization_is_reused_from_validate_questions` pins `co_filename`. Import coupling application → `scripts.` disclosed by the report (item 6); see E. |
| Do 2 | 09b §3 mapping as a pure function, judge verdict as data | **PASS** | `mapping.py:44-66` compared row by row with 09b lines 34–40: bare refusal → `correct_refusal`; related note/citations or answered-unanswerable → judge refusal check (`hallucination` / `correct_refusal`); answerable+insufficient → `false_refusal`; all `yes` → `correct`; ≥ 1 `yes`/`partial` → `partially_correct`; otherwise `incorrect`; contradiction wins. Missing verdict → `JudgeVerdictMissing`, never a guessed label. |
| Do 3 | Latency nearest-rank p50/p95, retried/fallback excluded and counted separately | **PASS** | `latency.py:50-55` (`is_clean` = `retry_count == 0 and not fallback_used`); `14/100*50 = 7.000000000000001` reproduced in Python, exact `Fraction` rank avoids it. |
| Do 4 | Exact McNemar (b, c, p), paired bootstrap CI (10 000, fixed seed), Wilcoxon; scipy only if installed | **PASS** (see Extra 4) | `scipy not installed` confirmed by `import scipy`; plain Python. |
| Do 5 | Tests on hand-made records: 09b §5 list, the S1={04}/S2={26,20} example, touching spans, 2 key mutations | **PASS** | Slot example parametrized at source **and** section level, touching-span tests, MRR 1/3 and strict 1.0 / 0.333. Mutations re-run by me: see B. The judge-cache/fake-LLM §5 items are out of scope (no judge code), as the report says. |
| Bound | Only `application/evaluation/` (new files), tests, spans file; no Gemini, no Chroma; frozen hashes unchanged | **PASS** | Scope 1; hashes see D. |
| Git | Branch from `origin/dev`, PR #12 base `dev`, not merged, pushed | **PASS** | `gh pr view 12` → `baseRefName: dev`, `state: OPEN`, `headRefOid` = local `HEAD` = `origin/eval-003b-pre` = `8adeb71`. |
| **Extra 2** | Hand-recompute 3 metrics on real data (Q-EVAL-017, 022, 031) | **PASS** | 51 values, 0 mismatches; see the section below. |
| **Extra 3** | `evidence_hit` per-point rule; the 3 alternate quotes counted; no case hits from alternate-only quotes | **PASS for the rule and the 3 quotes; FAIL for the "strict-like / no alternate-only hit" claim** | see the section below. |
| **Extra 4** | McNemar hand example; bootstrap pairs together; Wilcoxon vs hand exact p | **PASS** | see the section below. |
| **Extra 5** | `expected-spans-v1.json` reproducible, right input hashes | **PASS** | see the section below. |
| **Extra 6** | Frozen hashes; full pytest twice; earlier anomaly | **PASS**, anomaly not reproduced in pytest but a related Windows memory failure was | see B and D. |

### Extra 2 — three metrics hand-recomputed on real Arm A records

Top-5 lists were built from real `arm-a.jsonl` records (`source_id, char_start, char_end`) and real spans from `expected-spans-v1.json`. For each I derived the expected values by hand from the offsets (half-open overlap) before calling the functions; the functions were then called through `RankedChunk.from_record` and `spans_from_entry`.

- **Q-EVAL-017** (S1 `#11` intro `[0,1327)`; S2 `IMiddleware` `[1327,4388)`, `[6819,10586)`, `[12803,16578)`; alternates: `#11 Additional resources` for S1, `#10 Service lifetimes [16573,18087)` for S2). Top-5 = `#10 (0,1415)`, `#11 (1327,2417)`, `#11 (2310,3603)`, `#26 (0,1222)`, `#11 (0,1325)`. Hand: rank 1 is only a *source* hit for the S2 alternate; rank 2 `(1327,2417)` touches S1 at 1327 (no overlap) and overlaps S2 → S2 at rank 2; S1 only at rank 5. Section hit@1/3/5 = 0/0/1 (strict @5 = 1), slot fraction @1/@3 = 0.0/0.5, MRR lenient 0.5 and strict 0.5, **source MRR lenient 1.0 vs strict 0.5** (alternate #10 at rank 1), source hit@3 = 1. Evidence: P1's quote sits only in `(1327,2417)`; P2's in `(0,1325)` and others; P3's in `(0,1325)` → `evidence_hit` @2 = 0, @3 = 0, @5 = 1; any-quote diagnostic @1 = 0, @3 = 1. **All 18 values equal.**
- **Q-EVAL-022** (both slots in `#13`, up to 6 variants per section; alternates are the older H2 headings). Top-5 = `#13 (229417,230597)` (S1 alternate), `#13 (21473,22967)` (S2 expected v1), `#13 (19332,20181)`, `#04 (0,822)`, `#13 (20183,21471)` (S1 expected v1). Hand: `(21473,22967)` touches S1 `[20183,21473)` → no S1 credit; `(19332,20181)` is 2 chars before `20183` → miss. Section hit lenient @1/@2 = 0/1; **strict @2 = 0, @4 = 0, @5 = 1**; slot fraction @1/@2 = 0.5/1.0; MRR lenient 1.0, **strict 0.5**; source hit@1 = 1 for both rules. Evidence: P1 quote only in `(20183,21471)`; P3 has two quotes (redirect/re-execute variants); → evidence @1/@2/@4 = 0, @5 = 1; any-quote @1 = 1. **All 17 values equal.**
- **Q-EVAL-031** (alternate `#20`; S1 `#04 default expressions [6799,7632)`, S2 `#26 [3579,5427)`, alt `#20 [6195,9448)`). Top-5 = `#20 (6195,7093)`, `#26 (2337,3577)`, `#04 (5483,6797)`, `#04 (6799,7630)`, `#10 (0,1415)`. Hand: `#26 (2337,3577)` and `#04 (5483,6797)` both end 2 chars before their span (miss). Section hit lenient @3/@4 = 0/1, **strict @4 = @5 = 0**, slot fraction @3/@4 = 0.5/1.0; MRR lenient 1.0, **strict 0.25**; source MRR lenient 1.0 / strict 0.5; source hit@3 lenient = strict = 1 (sources only). Evidence: P1 is required, with two quotes (`#04` and `#26`); `#04 (6799,7630)` at rank 4 contains the `default` quote → evidence @3 = 0, @4 = 1, @5 = 1 (any-of within the point). **All 16 values equal.**

### Extra 3 — `evidence_hit` per-point rule, all 32 cases, independent recompute

My script (no import from `retrieval.py`) collapses whitespace with `re.sub(r"\s+", " ")` on the raw `normalized.jsonl` text of **every** document, maps offsets back, and classifies each quote occurrence against the case's expected and alternate spans.

- **Counts match the report:** 32 answerable + 4 insufficient; **100 quotes: 97 with an occurrence in an expected section, 3 only in alternate sections** — Q-EVAL-003 P3, Q-EVAL-004 P3 (`#13 … > Developer Exception Page`, v1 `[196453,198206)`), Q-EVAL-023 P2+P3 (`SuppressDiagnosticsCallback`). 77 required points, 35 optional, 17 required points with > 1 quote (also via `required_point_quotes`). Every quote was located (0 unlocated). Every required point has ≥ 1 quote with an expected-section occurrence (no message printed).
- **Rule:** `evidence_hit_at_k` = all-of across required points, any-of across a point's quotes, optional ignored (`retrieval.py:118-126`); the 3 alternate quotes count because `required_point_quotes` takes every `evidence[].supports`. Hand-checked in Extra 2 (017/022/031 incl. a quote split over points and an any-of point).
- **DEFECT (C1): the claim "no case can be evidence-hit from alternate-section quotes alone / evidence_hit behaves like the strict rule for retrieval that found only an alternate section" is false for 4 of 32 cases.** The report's claim is about the 3 quotes whose *only* location is an alternate section, and for those it holds. But the same quote text also occurs verbatim in other approved alternate sections, so a chunk from an alternate section alone can satisfy every required point:
  - **Q-EVAL-003 and Q-EVAL-004:** the P1, P2 and P3 quotes all occur in `#12 Handle errors in ASP.NET Core APIs > Developer Exception Page` (v1 `[798,4939)`), which is an approved alternate of both cases.
  - **Q-EVAL-007 and Q-EVAL-008:** both quotes (P1+P2, P2+P3) occur in `#23 Routing > Route constraint reference` (v1 `[333503,337935)`), an approved alternate.
  - Proved on real chunks, using the real functions: chunks that overlap **no expected span** of the case, both arms — Arm A: 003 and 004 with `#12 (798,2137)` + `#12 (2130,3235)`, 007 and 008 with `#23 (333503,334600)`; Arm B: `#12 (0,1600)` + `#12 (1400,3000)` and `#23 (333200,334800)`. In each, `evidence_hit@5 = 1`, lenient section hit = 1, **strict section hit = 0**. So 4/32 cases (12.5 %) can score `evidence_hit = 1` for retrieval that found only alternates. The report's item 5, its "Unverified / open" bullet and the **evaluation-spec line the owner is told to paste** ("evidence_hit behaves like the strict rule for retrieval that found only an alternate section") would put a false statement into the spec. No code defect: the implemented rule is the owner's; the claim about its behaviour is wrong. **Bound of the finding:** the quote-location scan covered every occurrence in all 24 documents, not only approved sections. In the 4 cases every occurrence outside the expected sections is in an *approved alternate* section (printed labels: `ALT` only, never `OTHER`), and in the other 28 cases at least one required point has all its quote occurrences inside expected sections, so no chunk that overlaps no expected span can complete them. So no case can be evidence-hit from unrelated, non-approved sections; the leak is limited to approved alternates in 003, 004, 007, 008.

### Extra 4 — statistics

- **McNemar:** hand examples, all equal to the function (`b` = A-only, `c` = B-only): b=1, c=6 → `2·(1+7)/128 = 0.125`; b=0, c=6 → `2/64 = 0.03125` (and the swapped input gives b=6, c=0, same p); b=2, c=8 → `2·(1+10+45)/1024 = 0.109375`; b=c=3 → raw `84/64`, capped to **1.0**; no discordant pairs → 1.0.
- **Bootstrap, pairs resampled together:** a constant shift `b = a + 1` over ten different values gives CI `[0.9999999999999991, 1.0000000000000009]` with delta 1.0 — a degenerate interval, only possible when `a[i]` and `b[i]` are drawn with the same index. Resampling the two arms independently on the same data would give `[-3.9, 5.9]`. My independent reimplementation (`random.Random(42)`, `randrange(n)` per draw, sorted, ranks 250 and 9750 = indexes 249 / 9749) reproduced the function's bounds bit-for-bit on a 12-case binary sample (`[-0.24999999999999994, 0.5833333333333333]`); output is deterministic across calls; `resamples == 10000`, `seed == 42`. The ranks 250 / 9750 rely on the exact `Fraction` tail; my check of the float `(1 - 0.95) / 2 * 100` prints `2.500000000000002` (the report writes `…0022`; cosmetic).
- **Wilcoxon exact, no ties:** d = [1,2,3,4,5,6,−7] → W+ = 21, W− = 7, subsets of {1..7} with sum ≤ 7 = 19 → `p = 2·19/128 = 0.296875` (function: 0.296875); n=5 all positive → `2/32 = 0.0625`; d = [1,2,3,−4] → `14/16 = 0.875`; an 8-value no-tie sample cross-checked against a brute-force enumeration of all 256 sign patterns (both `p = 0.25`, W+ = 27); zeros dropped (`zeros_dropped = 3`) with the same p; tie case d = [1,1,2] → `2/8 = 0.25`.

### Extra 5 — `expected-spans-v1.json`

`expected_spans_document()` rebuilt in memory: **parsed JSON identical and bytes identical** to the tracked file (no CRLF). Header hashes: `eval-v1.jsonl` `3436870e…2937` and `normalized.jsonl` `a6db2f26…9ae95`, both equal to `sha256` of the files in the worktree. `main()` was **not** run (it would overwrite the tracked file); the function it calls was.

## B. Tests

`PYTHONPATH=src` from the worktree, `.venv/Scripts/python.exe -m pytest -q`, run **twice**:

```
272 passed, 1 deselected in 11.02s   (exit 0)
272 passed, 1 deselected in 10.18s   (exit 0)
```

`186 + 86 new = 272`; `pytest --collect-only` per file: 8 / 9 / 22 / 29 / 18 (spans, latency, mapping, retrieval, stats) = 86, as the report says. **The truncated-run anomaly did not recur in either run.** However, a related environment failure did occur while I ran the mutation harness: one pytest subprocess died with exit code `3221225773` (0xC000012D, "commit limit reached", no pytest output) with only ~875 MB of virtual memory free system-wide; the same subprocess passed on every re-run. The report's anomaly (stopped at ~60 % with exit 1 and no summary) is consistent with the same machine-wide memory pressure from parallel sessions, but I could not reproduce its exact exit code, so the cause stays **UNVERIFIED (environmental, likely)**; no test failure was ever seen.

**Mutations** (scratch copy of `src`/`tests`/`scripts`/`data`; each restored and the baseline re-run: `47 passed`):

| Mutation | Result |
|---|---|
| M1 overlap `<` → `<=` | fails `test_touching_half_open_spans_do_not_overlap` (+ `test_section_hit_touching_chunk_is_a_miss`) |
| M2 strict returns all spans | fails `test_slot_rule_strict_and_lenient[sources0-1-0-1.0]` |
| M3 bootstrap breaks the pairing | fails `test_bootstrap_resamples_pairs_together` |
| M4 per-point `all` → `any` | fails `test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss` (reproduced 3×; one earlier run of the harness died with the memory error above) |
| M5 optional points no longer filtered | fails 3 tests (`…two_slot_case…`, `…ignores_a_missing_optional_point_quote`, `test_required_point_quotes_counts_a_quote_for_every_point_it_supports`). The report shows "1 failed" for M5, which is only true when just the optional-point test is run; every real run of the file gives ≥ 3 failures. Not a defect of the code; the transcript is narrower than the file. |

Test quality: read `test_eval_retrieval_metrics.py` line by line. Values are worked out by hand in the test text (touching spans, `1/3`, strict 1.0 vs 0.333, S1/S2 example with source *and* section, split quote, U+00A0 real chunk from Arm A #18, per-point rule with owner's three cases). No assertion-free or mock-only tests; expected values are not copied from output.

## C. Claims vs reality

| Claim | Result |
|---|---|
| Files table, 36 cases / 120 spans (72/48), 0 empty | PASS (Extra 5) |
| 86 new tests, 272 total, counts per file | PASS (B) |
| `display_text == normalized_text[start:end]` for all 733 Arm A and 859 Arm B chunks | PASS — recomputed: 733/733 and 859/859 |
| Sections never nest: 636 sections in 24 docs, 0 with `char_start` < previous `char_end` | PASS — recomputed: 636, 24, 0 |
| Corpus max 8 variants of one (source, heading) = `#13 … Additional resources`; 6 spans in one section (Q-EVAL-022); 10 in one slot (Q-EVAL-013 S1) | PASS — all three recomputed |
| 32 answerable, 77 required, 35 optional, 100 quotes, 17 multi-quote required points; 97 + 3 quote locations, the 3 named | PASS (Extra 3) |
| First normalized record is `#01` (the earlier draft said `#04`) | PASS |
| Frozen hashes and `git diff origin/dev` empty | PASS (D) |
| Mutation M1–M5 outcomes | PASS for M1–M4; M5 transcript shows 1 failure, real = 3 (B) |
| "no case can be evidence-hit from alternate-section quotes alone (checked for all 32 cases)"; "strict-like" | **FAIL (C1)** — see Extra 3. The check the report describes (only the 3 alternate-only quotes) is narrower than what the sentence and the spec line claim. |
| Anomaly "unexplained, unverified" | consistent with my observation (B); still UNVERIFIED as a cause |
| GitNexus: index cannot see this worktree; `git diff --name-status` used instead | UNVERIFIED (the index is registered for the main checkout); the scope check itself is PASS |
| Owner decisions of 2026-09-26 (exception to the prerequisite rule; evidence_hit per point) | UNVERIFIED (chat decisions; the verbatim text is in the report appendix; implementation matches it) |

## D. Project rules

- **Layers:** `grep -rniE "chromadb|google.genai|PySide6|gemini|AIza"` over `application/evaluation/` and the 5 test files → no hits; `test_project_structure.py` is inside the two green runs. `application` imports `scripts.evaluation.validate_questions` (a CLI module) — allowed by the structure test, disclosed (report item 6); running the metrics code outside pytest or `python -m` needs the repo root on `sys.path` (I hit `ModuleNotFoundError: scripts` when running a helper from another directory).
- **Model names:** no `gemini-` string in `application/evaluation/`.
- **Secrets:** `git grep -nE "AIza[0-9A-Za-z_-]{20,}"` → no hits; the spans file contains no key.
- **Corpus / excluded docs:** the diff has no `corpus/` file; `expected-spans-v1.json` has no source_id 14/19/24/25/27.
- **Frozen files:** `sha256sum` → `eval-v1.jsonl` `3436870ef02dfc2c25bd9d403ec6c8dd44cb46dfacbf02d586161dedd1252937`, `dev-v1.jsonl` `37d349e5a7fa43a179755d1c7993ef5a8438954f995bedcaee07bcfbf4da21d6`; both equal `docs/snapshots/evaluation/eval-v1.md`; not in the diff.
- **No eval-set tuning:** no tuning happens in this task; real eval cases are read only as test fixtures (Q-EVAL-023, 028).
- **No Gemini / no Chroma:** 0 requests; no `chromadb` import.

## E. Scope

No unrequested work. The owner-allowed exception and the owner's evidence_hit decision are recorded in the report. Extras beyond the prompt: `any_evidence_hit_at_k` (asked for as a diagnostic), `RankedChunk`, `JudgeVerdict` (disclosed). Spans cover only `eval-v1` (as instructed; dev cases left to 09b). Not a scope defect, but a follow-up: `collapse_whitespace` should move into `application/evaluation/` (needs a `scripts/` edit, out of scope here).

**Ledger deviation (output item 4).** 99-VERIFY says to set the task's row to `verified with fixes`. EVAL-003b-pre has no row of its own (a pre-work exception for 09b, and shared docs were off limits to the task), so I did **not** change a status: row 09b stays `not started`, and I appended a note to its Notes cell. The task report proposes its own Notes line for the same cell; the two must be merged by the owner at merge time. Also: this VERIFY commit makes PR #12 touch `AI_WORKLOG.md` and `task-ledger.md`; PRs #10 and #11 also insert text just before `## Summary` in `AI_WORKLOG.md`, so expect a merge conflict there.

## F. Quality spot-read

`retrieval.py` (`slots_satisfied`, `reciprocal_rank`, `required_point_quotes`, `_quotes_found`), `stats.py` (`mcnemar_exact`, `wilcoxon_signed_rank`, `paired_bootstrap_ci`), `mapping.py`, `latency.py`. No swallowed exceptions; every impossible input raises (`k < 1`, empty spans, insufficient case, required point without quote, unknown coverage, unpaired lengths); no silent fallback. Off-by-one candidates checked and fine: half-open overlap (touching = miss), `chunks[:k]`, nearest-rank `ceil(p·n/100)` with exact fractions, bootstrap index 249 / 9749, slot ordering (`S2 < S10`). Observations, not defects: `reciprocal_rank(k=0)` is rejected by `_check` before the `if k` shortcut (fine); Wilcoxon p uses `min(1, 2·min(lower, upper))`, the standard exact two-sided form; with ties it is exact where scipy would use a normal approximation (disclosed).

## G. Explain-it-back

All six bullets are correct. Two need a correction: (1) "Why evidence_hit is counted per required point" is right about the rule, but the report body and the pasted spec line then overstate it as *strict-like* (see C1); the accurate statement is "alternate-only retrieval can still score `evidence_hit` = 1 in 4 of 32 cases (003, 004, 007, 008), because their quotes also occur in an approved alternate section". (2) "Why exact methods" — fine; the float-off-by-one example for the CI tail is real (`2.500000000000002`).

## Verdict: ACCEPT WITH FIXES

**0 code defects, 1 FAIL (report/spec-claim C1), 3 UNVERIFIED** (GitNexus on this worktree, the owner's chat decisions, the anomaly's cause), 2 cosmetic mismatches (M5 transcript "1 failed"; `2.5000000000000022`). The functions, the spans file and the statistics are correct. What must be fixed before the owner pastes the "lines for the owner" into shared docs: the claim that `evidence_hit` is strict-like.

Open, non-blocking:
1. 09b proper should decide whether `evidence_hit` should also be reported next to strict section hit, or restricted to chunks that overlap an expected span, because alternates can score it in 4/32 cases (owner decision; not a bug).
2. Move `collapse_whitespace` out of `scripts/` (application → script coupling; sys.path).
3. Add dev cases to the spans file if dev runs need retrieval metrics.
4. The Windows commit-limit failure means a full-suite run under memory pressure can die silently; re-run when a run is truncated.

## Owner decision needed first (this is issue #1)

The owner's note asked that `evidence_hit` behave like strict. The implemented rule (the owner's own per-point rule) does not do that for Q-EVAL-003, 004, 007, 008. I did not pick for the owner. Choose one, then run the fix prompt for that choice:

- **(a) Keep the rule.** Only the wording changes: fixes 1-4 below (docs only, no source change).
- **(b) Make the code match the note.** A quote counts only when it lies in a top-k chunk that overlaps an expected span of the case (alternate-only chunks then score 0). This needs a code change in `retrieval.py` (`evidence_hit_at_k` and `any_evidence_hit_at_k` receive the case's expected spans), a test on the four cases using the real Arm A chunks named in Extra 3 (expected value 0 for alternate-only, 1 with an expected chunk), and a mutation proof that dropping the span condition fails it. Fixes 3-4 still apply; fixes 1-2 change to describe the new rule and the 3 alternate-only quotes (which then cannot count on their own).

## Fix prompt (paste into a new session; branch `eval-003b-pre`; written for choice (a), adapt fixes 1-2 for (b))

Re-verify scope note: after the `VERIFY EVAL-003b-pre` commit this branch also modifies `AI_WORKLOG.md` and `docs/plans/task-ledger.md`. A re-verifier should run the scope check as `git diff --name-status origin/dev...8adeb71` (the task's own commits) and treat the VERIFY commit and later fix commits separately.

1. **`docs/reports/execution/EVAL-003b-pre.md`, "Design decisions" item 5, the bullet starting "Correction to the owner's note", and "Unverified / open" first bullet.** Replace "no case can be evidence-hit from alternate-section quotes alone … so evidence_hit never credits retrieval that found only an alternate section … strict-like" with the measured fact: 97 of 100 quotes lie in expected sections and 3 only in alternate sections (unchanged); **and** 4 of 32 cases (Q-EVAL-003, 004: quotes also in `#12 … Developer Exception Page`; Q-EVAL-007, 008: quotes also in `#23 … Route constraint reference`) can be evidence-hit with chunks that overlap no expected span (proved on Arm A and Arm B chunks: evidence@5 = 1, lenient section = 1, strict section = 0). Check: run the alt-only script described in `docs/reviews/evaluation/EVAL-003b-pre-verify.md` § Extra 3 (or re-derive it) and paste its real output.
2. **Same report, "Lines for the owner", the `evaluation-spec.md` bullet and the `CHANGELOG.md` row.** Remove "behaves like the strict rule for retrieval that found only an alternate section" and the "(strict-like)" note; state instead that `evidence_hit` is not restricted to expected sections and can be 1 for alternate-only retrieval in cases 003/004/007/008. Check: `grep -n "strict-like\|behaves like the strict" docs/reports/execution/EVAL-003b-pre.md` → no hits.
3. **Same report, mutation block M5.** Replace "1 failed in 0.04s" by the real result of running the whole `test_eval_retrieval_metrics.py` (3 failed) or state that the transcript was for a single test. Check: rerun M5 on a scratch copy and paste the real summary line.
4. **Same report, "Unverified / open" anomaly bullet.** Add that a later verifier run hit Windows exit `3221225773` (commit limit reached) in one pytest subprocess with about 875 MB virtual memory free, which is consistent with the earlier truncated run being environmental. Check: none needed (documentation of an observed fact).
5. (Optional, one test) **`tests/unit/application/test_eval_expected_spans.py` or `test_eval_retrieval_metrics.py`:** a test that pins the measured set `{Q-EVAL-003, 004, 007, 008}` of cases whose required points can all be satisfied outside the expected spans, computed from `eval-v1.jsonl` and `normalized.jsonl` (quote text located in the normalized documents), so a change to the ground truth changes the test. It must fail if a case is added to or removed from this set. Check: a mutation that changes an alternate section's heading path in a fixture fails it.

# VERIFY EVAL-001

Verifier session, 2026-09-24. Reviewed commits `585f434`, `a15f443`, `9e0ab15`, `ce04909` and `b58a50d` against the full prompt (`docs/prompt-log/claude-code/EVAL-001 — Design Evaluation Dataset.md`), the addendum (`agents/prompts/01-EVAL-001-design-dataset.md`) and `agents/prompts/_common.md`. The verifier re-ran every check. Nothing was copied from the execution report. Scripts were run from the session scratchpad and read the repo only. One exception: `scripts/evaluation/build_coverage_matrix.py` writes to `coverage-matrix.yaml` when it runs. It was run twice, the output was byte-identical to the committed file (SHA-256 `bf9109d5…1481` before and after both runs), and `git status` did not change.

Uncommitted at review time, not part of this task: `AGENTS.md` and `CLAUDE.md`. The only change in each is the GitNexus count line (1638→1673 symbols).

## A. Acceptance / gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| A1 | No pipeline, runner, index, Gemini call, generated answers or results | PASS | The 5 commits touch only docs, `data/evaluation/questions/*`, one script, one test file and deps. No blueprint has `generated_answer`/`result`/`latency`/`retrieval_results` (script check: `[]`). |
| A2 | Corpus unmodified; excluded docs unused; #25 not invented | PASS | `git diff --stat 916b5bc HEAD -- corpus data/processed` is empty. No `"14"/"19"/"24"/"25"/"27"` source ID and no `excluded/` path appears in the 3 YAML files. |
| A3 | ~36 eval slots, ≥ 30 remain after drops | PASS | Script: 36 eval = 28 single + 4 cross + 4 insufficient. 32 answerable, so 30 remain if 2 are dropped. |
| A4 | EN + VI, ~18/18 | PASS | eval 18/18; dev 3/3 |
| A5 | 6–8 parallel groups, same ground truth | PASS | 7 groups (PG-001…007 = 001–014). The shared fields are YAML anchors, and the parallel-group test compares them. |
| A6 | Small docs and #13/#17/#23 covered | PASS | Expected-source counts: #22 3, #29 2, #18 1; #13 5, #17 1, #23 3. #09 is not an expected source (links only, 13 of 16 non-heading lines are link bullets). It is used as a distractor, as justified in design §5. |
| A7 | All 8 ADR-0003 failure modes | PASS | specific_heading 6, tiny_doc 5, fixed_size_code_split 4, mixed_version 3, repeated_version_sections 3, link_list_noise 3, near_duplicate_topk 3, large_doc_outranks_small 2, none 7 |
| A8 | easy/medium/hard; all 6 cognitive levels | PASS | 7/17/12; recall 6, explain 6, apply 9, analyze 4, compare 3, diagnose 8 |
| A9 | Single-source majority; cross-doc premises each from one doc | PASS | 28 vs 4. Spot-checked 031: the #20 alternate has `stands_in_for: "26"`. |
| A10 | Ground truth: source_id + heading path; answer and citation criteria per case | PASS | Heading-path test green. All 17 fields of prompt §16 are present on all 42 blueprints (script: no `MISSING`). |
| A11 | Blueprint fields; no final question wording | PASS | `status: proposed` everywhere. `question_notes` hold only guidance: none contains a "?" question. |
| A12 | Coverage matrix covers all §15 dimensions + dominance + gaps | PASS | The matrix has language, source, size class, level, difficulty, scope, retrieval challenge, failure mode and parallel status, plus dominance checks and `sources_without_expected_case`. It is deterministic (A-intro). |
| A13 | Design doc has all 20 required sections | PASS | `docs/specs/evaluation-dataset-design.md` headings §1–§20 |
| A14 | Addendum 1: OD-4/OD-5 asked and written into `evaluation-spec.md` | PASS (the question itself is UNVERIFIED) | `evaluation-spec.md:20` OD-4 and `:28` OD-5, both "decided by the owner"; master-plan OD table rows 269–270. The AskUserQuestion exchange is a session event with no artifact. |
| A15 | Addendum 2: near-miss insufficient cases with a grep proof | PASS | I re-ran the zero-hit terms (the test does this too). I also ran a broader search of my own: `tracking`, `throttl`, `rate limiting`, `ValidateOnBuild`, `captive`, `Moq`, `versioning`, `api version` all have 0 hits. The hits for `429` (#16, `4294967295`), `refresh` (#10, "refresh of the Index page") and `verify` (#03/#15/#23) are unrelated to the cases. The evidence map records the method and an example command, not one command per term. Acceptable. |
| A16 | Addendum 3: verbatim quote ≤ 300 chars, heading path in the inventory | PASS (note) | 107 evidence entries (84 unique), max 289 chars. 106 are raw substrings of the named section. 1 (BP-EVAL-028, #18 "Introduction") matches only after whitespace normalization, which design §12 discloses. |
| A17 | Addendum 4: dev set 5–6, disjoint, `split: dev` | PASS | 6 dev (4 single, 2 insufficient; sources #02/#04/#06/#07). My script compared expected and alternate sections, and separately evidence sections, between dev and eval: both intersections are empty. |
| A18 | `_common`: prompt saved verbatim | PASS | `cmp agents/prompts/01-EVAL-001-design-dataset.md docs/prompt-log/claude-code/EVAL-001.md` → identical |
| A19 | `_common`: execution report + worklog entry | PASS | `docs/reports/execution/EVAL-001.md`; `AI_WORKLOG.md` EVAL-001 entries |
| A20 | `_common`: status updated in master plan + epic | PARTIAL | These still say "awaiting owner review": `master-plan.md:167`, `EPIC-05-evaluation.md:3` and design doc line 3 ("waiting for the owner's review"). The report (line 3) and design §20 say the owner has reviewed and only the re-check of changed cases is pending. |
| A21 | `_common`: `gitnexus_detect_changes()` before the commits | UNVERIFIED | Nothing in the report or worklog records it. |
| A22 | `_common`: final chat report with "Explain it back" | UNVERIFIED | The verifier cannot see the chat. See G. |
| A23 | New dependency declared in both files, with a reason | PASS | `PyYAML>=6.0,<7.0` in `pyproject.toml:15` and `requirements.txt:4`. The reason is in the report. |

## B. Tests
`.venv/Scripts/python.exe -m pytest -q` → `45 passed in 2.08s`. `tests/unit/test_evaluation_blueprints.py` alone → `17 passed`.

These are real data assertions, not mock checks. Mutation checks run by the verifier (scratchpad, repo untouched):
- Removing `stands_in_for` from the alternates makes `test_cross_document_alternates_name_the_source_they_stand_in_for` fail on BP-EVAL-031.
- Dropping the first quote of BP-EVAL-001 makes `test_every_required_point_is_supported_by_a_quote` fail (`{'P1'}` unsupported).
- Running `_inline_comment_lines` on `9e0ab15~1` finds 33 lines: the 32 cut prose values plus the harmless top-level `status: proposed # …` comment. It finds 0 at HEAD. The mapping-typed variation in BP-EVAL-024 before the fix is also reproduced.

Limits, not defects:
- The absence test only searches the terms the author chose. My broader search above covers that gap once, but no test covers it.
- The dev/eval disjointness test compares expected sources only. My script covers alternates and evidence too.
- `test_design_covers_failure_modes_levels_and_key_documents` uses `>=` set checks, so it cannot detect a mode that is no longer covered well enough, only one that is gone.
- The `evidence_variant` branch in `test_evidence_quotes_are_verbatim_inside_their_section` is currently unused (no case sets the field). It is documented as optional.

## C. Claims vs reality

| Claim (source) | Result |
|---|---|
| 36 eval + 6 dev, 28/4/4, 18/18, 7 groups, 7/17/12, level counts (report, design §2–§8) | PASS (script) |
| Per-language difficulty EN 3/10/5, VI 4/7/7; groups 2/3/2 by difficulty and by size (design §3–§4) | PASS (matrix) |
| Retrieval-challenge counts 9/11/9/4/6/3/3/5 (design §6) | PASS (matrix: subsection 9, cross_source_overlap 11, version_variants 9, two_sources 4, code_heavy 4 + table 2, link_hub 3, long 3, paraphrase 5) |
| Top source #13 = 5/32 (16%), huge docs are the only source in 25%, huge docs are 73% of the text (design §5) | PASS (matrix 0.156/0.25; recomputed 0.733 of 1,197,929 chars) |
| #08 has 48 link items of 50, #09 13 of 15 (design §5) | PASS in substance (48 of 51 and 13 of 16 non-heading lines; the extra line is a caption or title) |
| **"Plain semantic matches 6%" (design §19, line 131)** | **FAIL**. The matrix says `share_direct_semantic: 0.094` (3/32). The review response #22 changed it from 0.062 to 0.094, but §19 was not updated. §6 correctly says 3 cases. |
| **"14 offline checks" (report file table, line 13)** | **FAIL**. The file now has 17 tests (`pytest … → 17 passed`). 14 was the count at `a15f443`. |
| 62 → 79 quotes (report line 27) | PASS historically (`grep -cE "^ *quote:"`: 62 at `585f434`, 79 at `a15f443`). It is 85 now (after `ce04909`). No current total is stated anywhere, so this is not wrong, but it is incomplete. |
| 32 values cut at " #" + 1 mapping (report, worklog, `9e0ab15`) | PASS (B) |
| 24 findings: 4 high, 9 medium, 11 low (report line 29) | PASS (severity column of review §2) |
| "23 accepted, 1 partly accepted" (report, worklog) | PASS with a wording note. Review §5 has 22 "Accepted", 1 "Partly accepted" and #24 "Decided" (DEV-006 scoring rule, decided by the author). |
| Evidence map: 6 absence proofs, 11 distractors | PASS |
| Matrix deterministic (two identical SHA-256) | PASS (A-intro) |
| Review fixes spot-checked: #2 (031 `stands_in_for`), #4 (`IsPrime_ValuesLessThan2_ReturnFalse` only in #28), #9 (016/031 P2 optional), #10 (009/010 P2/P4), #22 (002 `direct_semantic`), #3 (036 `must_not_claim`), #24 (DEV-006) | PASS |
| Reading claims ("full reads of #09, #18, #22, #29; first 9 sections of #08") | UNVERIFIED (session events). #08 does have 21 inventory sections, as stated. |

No fabricated number was found. The two FAILs are values left stale after later edits.

## D. Project rules
- Layers: `grep -E "chromadb|google\.genai|PySide6"` in `src` matches only `presentation/desktop/app.py`. The structure test is among the 45 that pass. PASS
- Model names: `grep -E "gemini-[0-9]"` in `src scripts` gives no hits. PASS
- Secrets: `git grep -E "AIza[0-9A-Za-z_-]{30}"` gives no hits. PASS
- Corpus untouched, excluded docs unused: PASS (A2)
- Eval freeze / tuning leakage: N/A. No `eval-freeze-v1` tag exists yet (EVAL-002). No tuning has run. The dev set is disjoint (A17).
- Ground truth written before indexes: PASS. No chunk or index exists.

## E. Scope
- Disclosed deviations: separate question/result files instead of the prompt's single record, merged `must_not_claim`, required flags on answer points, HOUSE-001 first. All are reasonable and documented in report §Deviations and design §18.
- New fields added beyond the prompt schema: `split`, `supports`, `stands_in_for`, `near_miss_sources`, `question_notes`, `size_class`, `retrieval_challenges`. All support the prompt's goals and are marked proposed where they affect metrics.
- Decisions: OD-4 and OD-5 were taken to the owner. The DEV-006 scoring rule (review #24) was "Decided" by the authoring session, not the owner. It affects only a dev case and is low risk, but it is a decision the author took without asking.
- `AGENTS.md`/`CLAUDE.md` GitNexus count refreshes rode along in `585f434`/`a15f443`. These are tool-generated, harmless and not disclosed.

## F. Quality spot-read
- `build_coverage_matrix.py`:
  - Deterministic: sorted counts, and `max(sorted(...))` breaks ties by source ID.
  - Digit-only strings are quoted, so source IDs stay strings.
  - `_dominance` would raise `ValueError` on an eval set with no answerable case. That cannot happen with the current data. No silent fallbacks.
- `_section_texts` / quote test: reads raw inventory line ranges and normalizes whitespace on both sides. Correct for the inventory's 1-based inclusive `line_start`/`line_end`. It matches the design's instruction to compare quotes against `display_text` with the same normalization.
- `_inline_comment_lines`: scans scalar tokens and checks the rest of the line for `\s+#`. It catches the defect class that `9e0ab15` fixed (B).
- Blueprint 036: the refusal may mention #03's general mock terminology (acceptable variation). Citing #03 for a Moq API counts as a hallucination. This is consistent with ABS-004. ABS-004's `closest_corpus_text` does not quote #03's "a *mock* verifies interactions" sentence or the `Assert.True(mockOrder.Validated)` example. The judge prompt in EVAL-003 should see that context (low).

## G. Explain-it-back
The chat report cannot be seen. The report's exit-gate table (§22 rows) was checked row by row against A and C, and every row is correct. Two report statements need correcting:
- "14 offline checks" → 17.
- "Status: done. Owner reviewed" contradicts the master plan, EPIC-05 and design line 3, which still say "awaiting owner review".

## Verdict
**ACCEPT WITH FIXES.**
- FAIL: 2 (C: design §19 "6%", report "14 offline checks").
- PARTIAL: 1 (A20, stale status lines).
- UNVERIFIED: 4 (A14 question event, A21 detect_changes, A22 chat report, C reading claims).

The ground truth, quotes, absence proofs and counts all reproduce. The fixes are documentation-only.

## Fix prompt (run in a new session)

```
EVAL-001 doc fixes from docs/reviews/evaluation/EVAL-001-verify.md. Docs only: do NOT edit blueprint.yaml,
evidence-map.yaml, coverage-matrix.yaml, scripts or tests.

1. docs/specs/evaluation-dataset-design.md §19 (line ~131): "Plain semantic matches 6%" → the current value.
   Check: equals share_direct_semantic in data/evaluation/questions/coverage-matrix.yaml (0.094 → "9%").
2. docs/reports/execution/EVAL-001.md file table (line 13): "14 offline checks" → the current count.
   Check: `.venv/Scripts/python.exe -m pytest --collect-only -q tests/unit/test_evaluation_blueprints.py` (17).
   Optionally add the current quote total (85 `quote:` lines; `grep -cE "^ *quote:" data/evaluation/questions/blueprint.yaml`).
3. Status lines: docs/plans/master-plan.md:167, docs/plans/epics/EPIC-05-evaluation.md:3 and
   docs/specs/evaluation-dataset-design.md:3 say "awaiting/waiting for the owner's review". Change them to the
   real state: owner reviewed, independent review done, pending the owner's re-check of the changed cases
   (design §20).
   Check: `grep -rn "awaiting owner review\|waiting for the owner's review" docs/` returns nothing.
4. Report/worklog wording "23 accepted, 1 partly accepted": say "22 accepted, 1 partly accepted, 1 decided by
   the author (DEV-006 scoring rule)", and list that rule under open decisions for the owner to confirm.
   Check: matches the Decision column of docs/reviews/evaluation/EVAL-001-blueprint-review.md §5.
5. Run `.venv/Scripts/python.exe -m pytest -q` (expect 45 passed) and gitnexus_detect_changes(), then commit
   "EVAL-001: doc fixes from verification" with only the files above.
```

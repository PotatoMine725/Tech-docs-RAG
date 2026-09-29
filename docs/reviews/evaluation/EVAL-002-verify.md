# VERIFY EVAL-002

Verifier sub-agent, 2026-09-25, fresh context, independent of the author. Linux container, `.venv/bin/python` (Python 3.11.15). No Gemini call, no ChromaDB index, no network.

Scope: the four `EVAL-002` commits on branch `eval-002` (`git log --oneline origin/dev..HEAD`), diffed against `origin/dev` = `9ee70bd`:
- `4172e98` Step 0 (ledger row 02, BP-EVAL-017 #10 alternate note "P1 and P2" → "P1");
- `459a902` question files, builder, validator, tests;
- `80b83f7` review sheet `eval-v1-review.md`;
- `743f713` report, prompt log, worklog, plan status, session handoff.

Requirements = `agents/prompts/02-EVAL-002-write-and-freeze.md` + `_common.md` + the owner's run instruction in `docs/prompt-log/claude-code/EVAL-002.md` §1 (overrides 1–7). Per override 2, steps 5–6 (approval, `eval-freeze-v1` tag, final snapshot, M1) are out of scope and are judged "correctly not done". Per override 1, "ask the user" is replaced by recorded AI decisions and ground-truth proposals.

## A. Acceptance / gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| A0 | Entry: no ChromaDB index; prerequisites verified | PASS | `ls -a data/chroma` → `. .. .gitkeep`. `git show origin/dev:docs/plans/task-ledger.md`: rows 01, 00R, 01o, 04a `verified`. `data/evaluation/results/` holds only `.gitkeep`. |
| A1 | Step 0: ledger row 02 "ready — OWNER-001 and INGEST-004 verified"; master-plan ~129 and EPIC-02 line 3 say INGEST-004 verified; 017 note trimmed to "P1" | PASS | Ledger row 02 was set in `4172e98`, then moved to "done (freeze pending …)" in `743f713` (expected). `master-plan.md:129` and `EPIC-02-ingestion-pipeline.md:3` already read "verified 2026-09-25" on `origin/dev` (done by `9ee70bd`), so no edit was needed. `git diff origin/dev..HEAD -- data/evaluation/questions/blueprint.yaml` → one line, the note only. |
| A2 | Step 1: every blueprint → one case; eval 36, dev 6; §18 / 09a fields present | PASS | Own script (`yaml.safe_load` of `blueprint.yaml` at `origin/dev` vs the JSONL, joined by `blueprint_id`): 42 cases for 42 blueprints. Fields checked present in every case: `answerable`, `answer_points[{id,text,required}]` (optional points kept), `expected_sources[{source_id,heading_path,slot}]`, `acceptable_alternate_sources[{…,slot,note}]`, `evidence[{source_id,heading_path,quote,supports}]`, `acceptable_variations`, `must_not_claim`, `citation_criteria`, `parallel_group_id`, `tags{difficulty,cognitive_level,size_class,failure_mode,scope}` (field list in `09a-EVAL-003a-runner.md:11`). Slots never flattened. |
| A3 | Step 1: ground truth and generated fields separated; generated null | PASS | `generated: {generated_answer: null, citations: null, result: null}` in all 42 cases (test `test_generated_fields_are_null_and_separate`, and my own read of the JSONL). |
| A4 | Ground truth in the JSONL equals the approved blueprints (no GT change without the owner) | PASS | Own comparison, every GT field of every case vs `origin/dev` blueprint: split, language, parallel group, answerable, answer_points, evidence, expected_sources, alternates (incl. slot, `evidence_variant`), variations, must_not_claim, citation criteria, scope/difficulty/level/size/failure mode, near-miss → **1 mismatch: BP-EVAL-017 alternate `note`**, which is exactly the owner-approved Step 0 trim. Blueprint HEAD vs `origin/dev`: only `BP-EVAL-017.acceptable_alternate_sources[1].note` differs. G1 (011/012 `must_not_claim`) is a proposal, not applied: `blueprint.yaml:519` still reads "The type must be public (internal is also allowed)." |
| A5 | Build is deterministic; files are the build output | PASS | `git archive HEAD scripts data/evaluation docs/reviews/evaluation` into a scratch copy, ran `build_question_files.py` there → `cmp` against the committed files: **byte-identical** (eval + dev). `build_review_sheet.py` in the copy → sheet byte-identical. No CR bytes in the JSONL or wording YAML. |
| A6 | Step 2: Vietnamese wording natural, not word-by-word | PASS (verifier opinion; owner reviews) | Read all 18 VI eval + 3 VI dev questions. Natural developer register ("Mình…", "load sẵn", "gửi query xuống database", "có ổn không"), terms kept in English as the blueprint notes ask. Not literal translations of their EN pair (e.g. 001/002, 013/014). Concerns listed under "Notes for the owner". |
| A7 | Step 3: validator: schema, unique IDs, ≥ 30 eval, both languages, parallel pairs share source/heading/points | PASS | `.venv/bin/python scripts/evaluation/validate_questions.py` → `eval: 36 cases (32 answerable); dev: 6 cases; evidence quotes checked: 107` / `OK`, exit 0. Code: `_schema_errors` (`validate_questions.py:81-114`), duplicate IDs and languages in `validate()`, `_parallel_errors` compares `PARALLEL_SHARED`. |
| A8 | Step 3: every source_id accepted (not 14/19/24/25/27); every heading path in the inventory | PASS | Validator `_corpus_errors` (sources incl. near-miss; heading paths of expected, alternate and evidence refs). Own script: 0 excluded IDs, 0 heading paths missing from `section-inventory.jsonl`. `git diff origin/dev..HEAD --stat -- corpus data/processed` → empty (corpus untouched). |
| A9 | Step 3: every evidence quote an exact substring after EPIC-02 normalization (anti-hallucination) | PASS (note N3) | Own independent script: 107/107 quotes found (whitespace-collapsed) in the raw `corpus/sources/*.md`, in the whole normalized document, and inside a span of their own `(source_id, heading_path)` section from `normalized.jsonl`. 106/107 are exact substrings of the raw file with no collapsing at all; the one exception is N3. Manual spot-read of 016, 018, 020, 024, 026, 030 quotes against the source files: verbatim. |
| A10 | Step 3: eval and dev disjoint | PASS | `_disjoint_errors` checks ID, blueprint, question text, expected sections; validator OK. |
| A11 | Step 4: review sheet with id, lang, question, expected answer, source, heading path, evidence quote | PASS | `docs/reviews/evaluation/eval-v1-review.md`: 42 case rows (51 `^\| Q-` lines incl. the 9-row look-first table) with columns ID, Lang, Group, Question, Expected answer, Expected source · heading path, Evidence quote(s), OK?. |
| A12 | Override 3: checklist (VI natural; no leak of answer/name; answer matches quote) and "look at these first" list | PASS | Sheet § "(a) Checklist" (4 items incl. the three required) and § "(b) Look at these first" (9 cases, one line why each). |
| A13 | Override 1: AI decisions recorded; GT changes only as proposals | PASS | Handoff § "AI decisions to confirm" A1–A10, none changes a GT field (A4 check above confirms); § "Ground-truth proposals (NOT applied)" G1. |
| A14 | Steps 5–6 / override 2: no tag, no final snapshot, M1 not marked | PASS (correctly not done) | `git tag -l` → empty. `docs/snapshots/evaluation/` holds only `.gitkeep`. `master-plan.md` G5A: box 2 ("committed before any index") and box 3 open; M1 text says "not reached". Box 1 is ticked with "(EVAL-002 draft …; not frozen yet)", see N4. |
| A15 | Do not: Gemini, indexes, generated answers | PASS | No `src/` change; no Gemini import in the new scripts; `data/chroma/`, `data/evaluation/results/` hold only `.gitkeep`. |

## B. Tests

| # | Item | Result | Evidence |
|---|---|---|---|
| B1 | Full suite | PASS | `.venv/bin/python -m pytest -q` → **`140 passed in 4.42s`**. Baseline: `git worktree add` of `origin/dev` → `121 passed in 4.00s` (worktree removed, `git status` clean). |
| B2 | New tests assert behaviour, can fail | PASS (gap N1) | `tests/unit/test_eval_dataset.py`: 19 tests (5 + 13 parametrized + 1). Validator mutations I ran on `validate_questions.py` (each restored from a backup; `sha256sum -c` → OK; `git status` clean afterwards): quote match not tied to the section → **1 failed**; required-point support check off → **1 failed**; parallel-pair comparison off → **2 failed**; alternate-slot check off → **1 failed**; eval/dev expected-section overlap check off → **19 passed** (N1); forbidden-ID set dropped (manifest check only) → 19 passed (redundant check, the manifest already excludes those IDs; not a gap). |
| B3 | Windows run | UNVERIFIED | Linux container only; the owner re-runs on Windows 3.13.3 (override 6). |

## C. Claims vs reality

| # | Claim (report / handoff / worklog) | Result | Evidence |
|---|---|---|---|
| C1 | 121 baseline, 140 after, 19 new tests | PASS | B1; counted the tests in the file. |
| C2 | Validator output 36 / 32 answerable / 6 dev / 107 quotes, OK | PASS | A7 (re-run). |
| C3 | SHA-256 (draft) `f265f527…6785` eval, `37d349e5…21d6` dev | PASS | `sha256sum` re-run → same values. |
| C4 | OD-4 mix: 28/4/4, 18 EN/18 VI, 7 parallel groups | PASS | `Counter((scope, language))` → single-source 14/14, cross-document 2/2, corpus-insufficient 2/2; test `test_eval_set_keeps_the_od4_mix`. |
| C5 | Mutation "quote check → any section counts" → 2 failed | PASS (equivalent) | My variant (any section of the same document) → 1 failed; the author's "any section counts" is broader, so 2 failures is plausible. Not an untraceable number. |
| C6 | "Only docs/YAML text edited in existing files; no existing symbol edited" | PASS | `git diff --stat origin/dev..HEAD`: the only code files are new (`scripts/evaluation/build_question_files.py`, `build_review_sheet.py`, `validate_questions.py`, `tests/unit/test_eval_dataset.py`). |
| C7 | Prompt saved verbatim | PASS | The task-prompt block in `docs/prompt-log/claude-code/EVAL-002.md` equals `agents/prompts/02-EVAL-002-write-and-freeze.md` byte for byte (Python compare → `True`). |

## D. Project rules

| # | Item | Result | Evidence |
|---|---|---|---|
| D1 | Layer rules | PASS | No `src/` change; `tests/unit/test_project_structure.py` part of the 140 passed. |
| D2 | Model names in config only; no API key | PASS | No model name in the new files. `git grep -nE "AIza[0-9A-Za-z_-]{20,}"` → no hit. |
| D3 | Corpus untouched; excluded docs unused | PASS | A8. |
| D4 | Eval file hash unchanged since `eval-freeze-v1` | N/A | The tag does not exist yet (correct per override 2). |
| D5 | No eval question used for tuning | PASS | `git grep -l "Q-EVAL-"` outside `data/evaluation/questions/` and `docs/` → only the validator and its test. No results or tuning outputs exist. |
| D6 | GitNexus impact / `detect_changes` | UNVERIFIED | GitNexus is not available in this container (verifier and author). No existing symbol was edited (C6), so no impact analysis was required. |
| D7 | LF line endings (override 6) | PASS | `grep -lI $'\r'` over all changed files → none. |

## E. Scope

| # | Item | Result | Evidence |
|---|---|---|---|
| E1 | Nothing outside the prompt + overrides | PASS | Extras are disclosed and justified: `question-wording-v1.yaml` + builder (report Deviation 3, A7), `build_review_sheet.py`, the handoff (asked for by the run instruction), design §16 sentence aligned with the trimmed note (A9, text only). |
| E2 | No decision taken silently | PASS | A1–A10 recorded for the owner; G1 not applied. |

## F. Quality spot-read

| # | Function | Result | Notes |
|---|---|---|---|
| F1 | `build_question_files.build_case` / `build` | PASS | Copies GT fields as-is; fails if a blueprint has no wording or two wordings; `expected_answer` = required points joined (design §18). Deterministic: blueprint order, `ensure_ascii=False`, `newline="\n"`. |
| F2 | `validate_questions._corpus_errors` | PASS (N3) | Section-bound quote lookup; `evidence_variant` honoured for expected sources; 300-char limit on the raw quote. Whitespace collapse uses Python `\s`, which also matches NBSP. |
| F3 | `validate_questions._ground_truth_errors` | PASS | Required points must be supported by a quote; alternates only in slots that have an expected source; every expected source has a quote; unanswerable → no sources/points/evidence + `expected_behavior`. No swallowed exceptions (a missing key in a malformed case is stopped by the schema pass first). |

## G. Explain-it-back (report § "Explain it back")

All five bullets are correct. One precision for bullet 2 ("whitespace is collapsed on both sides because line wrapping is not meaning"): the collapse also makes a regular space in a quote match a no-break space in the source (N3). It is still whitespace, but it is looser than ADR-0003 D1, which keeps NBSP.

## Notes (non-blocking)

- **N1 (test gap):** `_disjoint_errors`' expected-section overlap check can be switched off and all 19 tests still pass; `test_validator_rejects_overlap_and_too_few_cases` is caught by the ID/blueprint/question overlap instead. A mutation case where a dev case reuses only an eval case's expected section would close it.
- **N2 (for the owner's review, Q-EVAL-024 vi):** besides `Assembly.Location` (flagged in the sheet), "vì test không chạy trong thư mục output" states the cause half of P1 ("execute in a different directory than the output directory"). This leaks more than the sheet says. Suggest dropping that clause.
- **N3:** Q-EVAL-028's quote has a normal space in "C# applications"; the source (`corpus/sources/18-…md:29`) and `normalized.jsonl` have U+00A0. It matches only because `\s` collapses NBSP. This is correct for ground truth, but any later exact-match of citation excerpts should use the same collapse.
- **N4:** G5A box 1 in `master-plan.md` is ticked before the freeze, with an explicit "not frozen yet" note. The fact holds (≥ 30 cases, schema test passes), and M1 is not marked. The owner may prefer to tick it at the freeze.
- **N5 (cosmetic):** every blueprint still has `status: proposed` (and the file header "status: proposed") although EVAL-002 treats them as approved. The owner may flip it at the freeze (text, not ground truth).
- **Other VI/EN wording notes:** Q-EVAL-033 says "not keep track of the entities", which is close to the missing API name (`AsNoTracking`). This is acceptable for a near-miss unanswerable case, because the lexical pull toward #22 is the point of the case. The 9 look-first items are reasonable. No leak found in 016: both the output comment and the page's "both variables refer to the same object" comment were removed.

## Verdict

**ACCEPT.** FAIL: 0. UNVERIFIED: 2 (B3 Windows run; D6 GitNexus not available). Freeze remains pending: the owner reviews the sheet, answers A1–A10 and G1, then merges and tags `eval-freeze-v1`.

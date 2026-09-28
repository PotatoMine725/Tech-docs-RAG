# VERIFY EVAL-003c

Verifier session, 2026-09-28, Windows 11, the main checkout's `.venv` Python by absolute path,
`OPENBLAS_NUM_THREADS=1`. Own git worktree `.claude/worktrees/verify-eval-003c`, detached at `origin/eval-003c`
(`34ff5bb`), separate from the implementer's `.claude/worktrees/eval-003c`. Merge-base with `origin/dev` =
`491f137` (`git log HEAD..origin/dev` empty). Reviewed against `agents/prompts/09c-EVAL-003c-report-generator.md`,
`agents/prompts/_common.md`, `docs/specs/evaluation-spec.md`, CLAUDE.md, `docs/reports/execution/EVAL-003c.md`, and
the owner's 8 extra checks (pasted task).

**Zero Gemini/embedding requests. `.env` never opened.** Every script below imports only `scripts.evaluation.*`
(report tools, never `judge_run.py`/`run_eval.py`), `knowledge_assistant.application.evaluation.*` and
`knowledge_assistant.config`. `config.py` reads `os.getenv` only; `grep -rln dotenv src scripts` lists only entry
points this session never imported (`judge_run.py`, `run_eval.py`, `ask.py`, `build_index.py`, the desktop app, the
generation checks). EVAL-004 artefacts were read with `git show origin/eval-004:<path>` into a scratch folder,
byte-exact (both `summary.json` SHA-256s match the ones printed in `EVAL-004a.md`: `02e6f4f6…`, `9dcc4eae…`); the
owner's graded sheet was never edited (hash identical before/after). Mutations ran on a `git archive HEAD` scratch copy,
never in the worktree; `git status --porcelain` in the worktree was empty before this review was written.

The scratch scripts behind every number in this review are reproduced verbatim in Appendices A–E.

## A–G (99-VERIFY standard checks)

| # | Check | Result | Evidence |
|---|---|---|---|
| A | Acceptance / gate items | **PASS** | Do-1: `make_tables.py` computes every metric through `scoring.py`/`metrics/*` (no hand-typed value: `grep` of the renderers shows only `summary[...]` lookups); 9 `AUTO` markers + `judge_agreement` placeholder (report lines 5–161); missing marker appended (`test_a_new_marker_is_appended_as_a_new_section`); each caption states run ids, n and exclusions (9/9 captions, check 3); `summary-<A>-<B>.json` and `eval-table-<run>.csv` with the brief's 5 columns + extras (`CSV_COLUMNS`, `make_tables.py:72`); **determinism re-run by me**: both generator commands from the report, run twice in a scratch copy → all 5 committed artefacts byte-identical both times (report, summary JSON, 2 CSVs, spot-check sheet). Do-2: `make_spot_check.py --fraction 0.2 --seed 42` stratified by (result, language), sheet columns as asked, `human_result`/`human_note` blank; `score_spot_check.py` computes agreement/κ/confusion/disagreements and refuses on a blank `human_result` (tested). Do-3: every listed test exists (see B). "Do not": no evaluation run, no analysis text. **But** see checks 4 and 5 for what the prompt's wording did not foresee. |
| B | Tests | **PASS, with gaps** | Full offline suite once at the end: `817 passed, 1 deselected in 20.62s`. Collected: dev (`origin/dev` archive) `775/776 (1 deselected)`, branch `817/818` → +42, as claimed. Targeted incl. structure test: `93 passed`. Gaps: 3 of 9 mutants survive (check 6): no test on caption content, on the per-case table's cell order, or on lenient vs strict columns; no test pins `score_row` to `score_record` (check 2). The CLI test's `header == CSV_COLUMNS` is self-referential (the value mapping is tested separately and does kill a swap). |
| C | Claims vs reality | **FAIL** (3 claims) | (1) `AI_WORKLOG.md:510-511`: "the two paths agree exactly (tested directly: `tests/unit/test_eval_report_data.py`)" is false: that file's 6 tests never call `score_record`. The agreement is true (check 2 proves it empirically), but it was argued, not tested. The same goes for the report's "provably identical" (`EVAL-003c.md:281`). (2) `EVAL-003c.md:223-224`: "nothing here is presented as, or could be mistaken for, an actual evaluation result" is contradicted by check 4. (3) The new spec sentence "unlabelled records … are excluded from every denominator above" is false for the citation denominators (check 7). Everything else I traced reproduces: 775→817, 42 new tests, the two committed dev `judgements.jsonl` lines (`wc -l` = 2), 0 duplicate groups in the dev data, both generator commands, byte-identical output. |
| D | Project rules | **PASS** | Structure test green (in the 93 above). New files import no `chromadb`/`google.genai`/`PySide6`/`GeminiLLM`/`infrastructure.llm` and contain no `gemini-<n>` model name (grep, exit 1). `git grep -c -E "AIza[0-9A-Za-z_-]{35}" HEAD` → no match (exit 1). `git diff origin/dev...HEAD --name-only -- corpus data/evaluation/questions src config` → 0 files. `git diff --stat eval-freeze-v1 HEAD -- data/evaluation/questions` → only `expected-spans-v1.json` added (EVAL-003b-pre `7e70180`, logged, not this task); frozen question files unchanged. Eval ids in this task's added lines: 2 hits, both the report quoting its own `grep -E "Q-EVAL-\|BP-EVAL-"` pattern (no actual id). Excluded docs untouched. |
| E | Scope | **PASS** | Check 1. `--runs` accepting ≥1 run and `run_split` duplicated rather than imported (to avoid importing the Gemini adapter) are disclosed deviations and reasonable. |
| F | Quality spot-read | **PASS, 1 note** | Read line by line: `eval_report_data.score_row`/`judgements_and_prompt_version`/`build_chunk_indexes`, `make_tables.base_caption`/`render_sections`/`replace_or_append_section`/`csv_rows`, `make_spot_check.sample_stratified`, `score_spot_check.parse_sheet`/`check_filled`/`cohens_kappa`. No swallowed exception; an unresolvable duplicate raises (`RankedChunk.from_record`, `retrieval.py:53-58`). Note (drift risk, check 2): the report path derives the judge prompt version from the judgement lines (`eval_report_data.py:135-136`), while the canonical EVAL-004a path uses config (`get_judge_settings().prompt_version`). They agree today (`judge_v1` on both real runs). A `judgements.jsonl` holding only a stale version would be labelled by the report but counted as "missing" by the canonical path. |
| G | Explain-it-back | **PASS, 2 corrections** | "When spans are available, the two paths are provably identical": correct in fact (72/72 real, 22/22 synthetic, check 2), but it was shown here, not proven or tested by the task. "Every one of the 9 sections says … which cases were excluded": correct (9/9), but untested (mutant a3 survives). The other bullets (sheet collapsing, chunk index from retrieved chunks, no mutation testing) are accurate. |

## Owner's extra checks

### 1. Scope: **PASS**

`git diff origin/dev...HEAD --name-status` (local `dev` 7db105b is behind `origin/dev` 491f137, so I diffed the remote
tip, as the task branched from it): 22 files. **No file under `src/` changed**, so no scoring/metric/judge code changed.
New: 4 scripts (`eval_report_data.py`, `make_tables.py`, `make_spot_check.py`, `score_spot_check.py`), 5 test files,
the generated dev artefacts (report, summary JSON, 2 CSVs, spot-check sheet), the report and prompt-log. Modified: the
three housekeeping files (`evaluation-spec.md` +5, `EVAL-003b.md` ±1, `test_eval_judge.py` +12) and tracking docs
(`AI_WORKLOG.md`, `task-ledger.md`, `master-plan.md`, `EPIC-05-evaluation.md` plan).

### 2. Two scoring paths: **PASS (equivalent today), drift risk**

Textually, `score_row` (`eval_report_data.py:105-128`) is `score_record` (`scoring.py:158-179`) plus the guard. Proven
empirically, field by field (JSON-normalised dict diff), with the `spans_unavailable` key removed before comparing:

| Data | Records | vs committed `summary.json` rows (canonical EVAL-004a output) | vs `score_record`, identical inputs | vs `score_record` as EVAL-004a ran it (full 733/859-chunk index from `data/processed/chunks/arm-{a,b}.jsonl` + config `judge_v1`) | `spans_unavailable` true |
|---|---|---|---|---|---|
| `origin/eval-004` `20260928-eval-A-full-491f137` + `…-B-…` (read-only) | 72 | **0 diffs** | **0 diffs** | **0 diffs** | 0 |
| Synthetic eval-split fixture, arms A and B, 11 shapes each | 22 | — | **0 diffs** (also via `load_run` → `score_runs`) | **0 diffs** (full index) | 0 |

The synthetic shapes cover correct, partially_correct with a non-supporting marker, `judge_error`, judgement missing,
retrieval mode, a **duplicate-rule change resolved through the report's retrieved-chunk index**
(`dup_changed=True`), corpus-insufficient bare refusal, an answered unanswerable question (hallucination), a false
refusal with a related note, a runner error and an answer with no citation (`citation_missing`). On the real runs the
report's index held 123/127 chunks against the canonical 733/859. It made no difference: no retrieved chunk has a
non-empty `duplicate_chunk_ids` (0 in both runs), and a duplicate that cannot be resolved raises. It never produces a
different number silently. Judgement keying matched: same keys and values as `latest_judgements` (29 in A, 31 in B),
and the derived prompt version was `judge_v1` in both runs.

**Why drift is possible anyway:** the logic is duplicated, and no test pins the two paths together. A future change
to `score_record` (a new field, a new guard) would not reach `score_row`, and nothing would fail. There is also the
prompt-version input described in F.
**Smallest fix:** in `score_row`, when the record is not `spans_unavailable`, return
`{**scoring.score_record(record, spans_by_case, index, judgements, prompt_version), "spans_unavailable": False}`. Keep
the recomposed path only for the uncovered-answerable branch. Add one test asserting `score_row(...) minus
spans_unavailable == score_record(...)` on a covered fixture. Separately, abort, or at least list the mismatch in the
caption, when the derived judge prompt version differs from `get_judge_settings().prompt_version` (which reads
`os.getenv` only), or take it as an explicit `--judge-prompt-version` argument.

### 3. `spans_unavailable` named in every caption: **behaviour PASS, test FAIL**

`base_caption` (`make_tables.py:102-113`) is prepended to all 9 sections (`render_sections`, `:331-348`). In the
committed report: `grep -c 'Excluded from retrieval and citation scoring.*Q-DEV-001:A, Q-DEV-002:A'` → **9**, one per
section. The records are still visible per row (`spans_unavailable` column in the per-case table) and still scored
for `answer`. The summarisers drop `None` retrieval/citation from those denominators only (`scoring.py:194, 237`).
Nothing is silently dropped. **But no test asserts any caption text**: the e2e fixture has no uncovered answerable
record, and `test_eval_report_data.py` checks only the flag. Mutant a3 (remove the excluded list from every caption)
passes all 40 targeted tests.

### 4. `docs/reports/epics/EPIC-05-evaluation.md` from DEV dry-runs: **FAIL**

It could be mistaken for the evaluation result. It sits at the path of the real EPIC-05 report. Its only heading is
`# EPIC-05 evaluation report (generated)`, and there is no top banner. The dev warning appears only as a bold
sentence at the end of each caption paragraph, after the run list, and the per-case table carries real labels
(`correct`, `correct_refusal`). It was also not moved under `validation/`.
**The fix is not a hand-written banner.** `replace_or_append_section` leaves text outside markers untouched on
purpose, so a manual banner would survive EVAL-004b's regeneration into the real report. Fix: regenerate the dry-run
with `--out validation/evaluation/EPIC-05-evaluation-dev-dryrun.md` and delete
`docs/reports/epics/EPIC-05-evaluation.md`, so EVAL-004b creates it fresh. Move the dev spot-check sheet
(`docs/reviews/evaluation/judge-spot-check-20260927-dev-A-full-05680f9.md`) under `validation/evaluation/` too.
Optionally, `make_tables.py` can also emit the banner itself inside its own `<!-- AUTO:status -->` marker at the top,
conditional on any input run having `split == "dev"`.

### 5. Spot-check tooling vs the owner-graded EVAL-004a sheet: **FAIL (format, and rule)**

Run read-only (`--out` pointed at a scratch file):

```
python scripts/evaluation/score_spot_check.py <scratch>/validation/evaluation/judge-spot-check.md --out <scratch>/scratch-report.md
ABORTED: cannot parse a case heading: '## S01 (answer check)'
exit=3        sheet unchanged: True        report written: False
```

**It computes no agreement at all.** There are two separate incompatibilities:

1. **Format.** `score_spot_check.py` expects `## <case_id> (arm X, lang)` headings, `- **Field:** value` lines, an
   inline `Judge result`, a typed `human_result` label and a `<!-- run_id -->` marker. The owner's sheet is **blind**:
   `## Sxx (answer|refusal) check` headings and an `Owner verdict` table of per-point grades (`P1 covered` …,
   `contradicts ground truth`, `unsupported claims`, per-citation support, or `presents_related_as_answer`). The
   judge's label and the S-id → case/arm/run mapping live in a separate key file (`judge-spot-check-judge.md`).
2. **Rule.** Even on its own format, the tool compares a hand-typed `human_result` label against the judge's label.
   That is the holistic route. The judge's label comes from `map_result` over per-point verdicts, so the owner's side
   must go through the same `map_result`. Otherwise the tool reproduces the holistic 9/10, which ignores
   `map_result`, instead of the rule-based 8/10.

What the tool's own math (`agreement_rate`, `cohens_kappa`, `confusion_matrix`) gives once a scratch adapter (Appendix C)
supplies rule-based pairs. The adapter parses the blind tables, joins the key, rebuilds a `JudgeVerdict` from the
owner's grades and calls `map_result(answerable, insufficient, has_related_note, citations, verdict)` with the
record's own fields:

| S-id | case:arm | check | judge label | owner via `map_result` | holistic column |
|---|---|---|---|---|---|
| S01 | Q-EVAL-017:A | answer | partially_correct | partially_correct | yes |
| S02 | Q-EVAL-035:B | refusal | correct_refusal | correct_refusal | yes |
| S03 | Q-EVAL-012:A | answer | partially_correct | partially_correct | **no** |
| S04 | Q-EVAL-035:A | refusal | correct_refusal | correct_refusal | yes |
| S05 | Q-EVAL-024:A | answer | correct | correct | yes |
| S06 | Q-EVAL-025:A | answer | correct | correct | yes |
| S07 | Q-EVAL-024:B | answer | correct | correct | yes |
| S08 | Q-EVAL-022:B | answer | correct | correct | yes |
| S09 | Q-EVAL-020:B | answer | partially_correct | **correct** | yes |
| S10 | Q-EVAL-017:B | answer | partially_correct | **correct** | yes |

**Rule-based agreement 8/10 = 0.800, Cohen's κ = 0.6875** (p_o = 0.8, p_e = 0.4·0.6 + 0.2·0.2 + 0.4·0.2 = 0.36).
Disagreements: **S09, S10**. Confusion (rows judge, cols owner; correct / correct_refusal / partially_correct):
`[4,0,0] [0,2,0] [2,0,2]`. The holistic "agree with the judge?" column gives 9/10, with S03 the only "no". Under the
rule, S03 agrees at label level (both `partially_correct`); it differs only at point level. This matches the owner's
figure (8/10 by the set rules) and the corrected EVAL-004a report / ledger row 11.

**Adapter needed** (in `score_spot_check.py`, without touching the owner's sheet):
- (a) Parse the blind `## Sxx (<check> check)` sections and their `Owner verdict` table.
- (b) Join `judge-spot-check-judge.md` for case/arm/run/check/judge label.
- (c) Load each record from its run folder and derive the owner label with `map_result` (per-point coverage,
  contradicts, unsupported; or `presents_related_as_answer`).
- (d) Report the rule-based agreement as the headline, and the holistic column only as a secondary line.

`make_spot_check.py` should emit that same per-point grading table, blind with a separate key, instead of a single
typed `human_result` label. The `judge_agreement` placeholder text (`make_tables.py:67-71`) points the owner at the
old path and format, so it needs updating as well.

### 6. Mutations (scratch copy, 40 targeted tests, each file restored and SHA-256-checked): **FAIL for (b) tables and caption**

| Mutant | Result | Killing test |
|---|---|---|
| a1 `spans_unavailable` flag forced `False` | **killed** | `test_an_answerable_case_outside_expected_spans_skips_retrieval_and_citation_but_not_answer` |
| a2 guard removed (`has_spans = True`) | **killed** | same |
| a3 excluded list dropped from every caption | **SURVIVED** (40 passed) | none |
| b1 `csv_rows`: `question` ↔ `expected_answer` values | **killed** | `test_csv_rows_have_the_briefs_five_columns_correctly_mapped` |
| b2 per-case table: `result` ↔ `citation_auto_class` cells | **SURVIVED** (40 passed) | none |
| b3 retrieval table: lenient ↔ strict columns | **SURVIVED** (40 passed) | none |
| c1 seed ignored (`random.Random(0)`) | **killed** | `test_sample_is_reproducible_with_the_same_seed_and_changes_with_a_different_seed` |
| c2 unseeded `random.Random()` (3 runs) | **killed** 3/3 | same |
| c3 stratification broken (constant stratum key) | **killed** | `test_sample_covers_every_non_empty_stratum_with_at_least_one_record` |

Every mutant run printed `restored_byte_for_byte=True`. After all runs, the three scratch files' hashes equal the
worktree's. The baseline on the unmutated scratch copy was `40 passed`. `knowledge_assistant` is not pip-installed,
so pytest in the scratch copy imports the scratch code: the killed mutants prove that.

### 7. Housekeeping from EVAL-003b-verify: **done; one new sentence is wrong (doc-only)**

- (a) Denominators and nearest-rank prose, `evaluation-spec.md` +5 lines with an amendment line. The nearest-rank
  paragraph matches `metrics/latency.py:4-5,19-40` (`ceil(p/100·n)`, clean = `retry_count == 0 and not
  fallback_used`). **The denominator bullet is partly wrong.** It says unlabelled records (judge missing /
  `judge_error`) "are excluded from every denominator above". `summarize_citations` (`scoring.py:237-239`) never
  filters by label, so an answered answerable record with a `judge_error` stays in `presence_rate`,
  `source_precision`, `section_precision` and `auto_class`. It leaves only `support_rate`/`judge_class`, and
  groundedness/points_covered, which use judged records. Demonstrated (Appendix E): one `ok` and one `judge_error`
  answered record → `unlabelled: ['Q-TEST-002:A']`, `accuracy n: 1`, `groundedness n: 1`, **`citation answered n:
  2`**. The code's behaviour is defensible, since the automatic span check needs no judge, so fix the spec
  sentence, not the code.
- (b) Duplicated-citation-marker test: present (`test_eval_judge.py`, 2 parametrizations) and meaningful. It uses
  the real `parse_verdict` and passes in the full suite.
- (c) `EVAL-003b.md` Explain-it-back: "wrong section" → "wrong document", exactly as described.

### 8. Offline suite, structure test, key scan: **PASS**

Offline collected: `origin/dev` **775** / branch **817** (1 `gemini` deselected in each). Full run: `817 passed, 1
deselected`. `tests/unit/test_project_structure.py` green (inside the targeted `93 passed`). `AIza[0-9A-Za-z_-]{35}`
over the HEAD tree: 0 matches.

## Verdict: **ACCEPT WITH FIXES**

6 FAIL (C, extra 3-test, 4, 5, 6, 7-sentence), 0 UNVERIFIED. **None of the FAILs changes a committed number.** Scoring
equivalence is proven on real and synthetic data, and all five committed artefacts regenerate byte-identical. The
failures are in labelling (check 4), spot-check tooling (check 5), test strength (checks 3 and 6) and one spec
sentence (check 7). **Check 5 blocks EVAL-004b from using `score_spot_check.py`** on the owner-graded sheet until the
adapter lands. Top 3: (1) check 5, incompatible format and the holistic-label rule; (2) check 4, the dev dry-run sits
at the real report path; (3) check 6b, Markdown table columns untested (plus caption, a3).

## Fix prompt (run in a new session on branch `eval-003c`, own worktree, zero Gemini requests, never open `.env`)

```
EVAL-003c fixes (from docs/reviews/evaluation/EVAL-003c-verify.md). Zero Gemini requests. Offline tests only.

1. Dev dry-run is not the evaluation report (check 4).
   - Regenerate: make_tables.py --runs 20260927-dev-A-full-05680f9 20260927-dev-A-retrieval-05680f9
     --out validation/evaluation/EPIC-05-evaluation-dev-dryrun.md
   - Move docs/reviews/evaluation/judge-spot-check-20260927-dev-A-full-05680f9.md under validation/evaluation/.
   - git rm docs/reports/epics/EPIC-05-evaluation.md (EVAL-004b creates it fresh). Do NOT hand-write a banner
     outside markers: it would survive into the real report.
   - Optional: make_tables.py emits a "DEV DRY-RUN - NOT EVALUATION RESULTS" banner inside its own
     <!-- AUTO:status --> marker at the top whenever any input run has split == "dev".
   - Fix links (EVAL-003c.md, ledger 09c, EPIC-05 plan, AI_WORKLOG).
   Proof: docs/reports/epics/EPIC-05-evaluation.md absent; if the option is taken, a test shows the banner appears
   for a dev run and not for an eval run.

2. Spot-check scoring by the set rules (check 5).
   score_spot_check.py must score the EVAL-004a blind format:
   - "## Sxx (answer|refusal) check" + the "Owner verdict" table;
   - the key file judge-spot-check-judge.md for S-id -> case/arm/run/check/judge label;
   - derive the owner label with metrics.mapping.map_result from the per-point grades + contradicts + unsupported
     (or presents_related_as_answer) and the record's answerable/insufficient/has_related_note/citations;
   - headline = rule-based agreement, kappa, confusion, disagreements;
   - holistic "agree with the judge?" column reported as a secondary line only.
   make_spot_check.py emits the same blind per-point sheet + a separate key file (no typed human_result label).
   Update JUDGE_AGREEMENT_PLACEHOLDER (make_tables.py:67-71) to the new path and format.
   Never edit the owner's sheet.
   Proof: a test on a small fixture in that format; and read-only on
   git show origin/eval-004:validation/evaluation/judge-spot-check.md + judge-spot-check-judge.md:
   8/10 agreement, kappa 0.6875, disagreements S09, S10; holistic 9/10 (S03).

3. Tests that kill the surviving mutants (checks 3 and 6).
   (a) The caption names every spans_unavailable case_id:arm in all 9 sections, plus the dev-split banner line
       (fixture with an uncovered answerable record).
   (b) The per-case table's cells are in header order, on a fixture where result != citation_auto_class.
   (c) The retrieval table puts lenient in the "lenient (headline)" column and strict in "strict", on a fixture
       where they differ.
   Proof: re-apply mutants a3, b2, b3 from the review's Appendix D; each must fail a test; restore.

4. Pin score_row to score_record (check 2).
   When a record is not spans_unavailable, return
   {**scoring.score_record(...), "spans_unavailable": False}; keep the recomposed path only for the
   uncovered-answerable branch.
   Add a test: score_row minus spans_unavailable == score_record on a covered fixture (several shapes).
   Abort, or name it in the caption, when the judge prompt version derived from judgements.jsonl !=
   get_judge_settings().prompt_version (os.getenv only), or take --judge-prompt-version explicitly.
   Proof: the new test; a mutant adding a field to score_record's row fails it.

5. evaluation-spec.md denominator sentence (check 7).
   Unlabelled (judge missing / judge_error) answered answerable records ARE counted in presence_rate,
   source_precision, section_precision and auto_class. They are excluded from accuracy-family rates,
   groundedness_rate, points_covered_mean, support_rate and judge_class.
   Add a dated amendment line. No code change.
   Proof: a test with one ok + one judge_error answered record: citation answered n == 2, accuracy n == 1.

6. Report corrections (check C/G).
   - AI_WORKLOG.md: "tested directly: tests/unit/test_eval_report_data.py" becomes true only after fix 4; say so.
   - EVAL-003c.md: correct "provably identical" and "could not be mistaken for an actual evaluation result".
   - Update ledger row 09c and re-run 99-VERIFY on the fixes.
```

## Appendix A: `equiv.py` (check 2, real eval-004 runs, verbatim)

Run: `python equiv.py <verify worktree> <scratch root with origin/eval-004 files> "<main checkout>/data/processed/chunks"`.
Output: `TOTAL {'records': 72, 'diffs_vs_summary': 0, 'diffs_vs_score_record_same_inputs': 0,
'diffs_vs_score_record_full_index': 0, 'spans_unavailable_true': 0}`; report index 123/127 chunks vs full 733/859;
`retrieved chunks with non-empty duplicate_chunk_ids: 0` (both runs); derived prompt version `judge_v1` (both).

```python
"""VERIFY EVAL-003c check 2: score_row vs scoring.score_record, field by field.

Read-only. Inputs: the committed eval-004 run folders (extracted byte-exact to a scratch root) and, when present, the
full per-arm chunk files the canonical EVAL-004a scorer used. Zero network.
"""
import json
import sys
from pathlib import Path

WT = Path(sys.argv[1])          # verify worktree (code under test)
ROOT = Path(sys.argv[2])        # scratch root with data/evaluation/results/<run>
CHUNKS = Path(sys.argv[3])      # main checkout data/processed/chunks (read-only)
sys.path[:0] = [str(WT / "src"), str(WT)]

from scripts.evaluation import eval_report_data as erd  # noqa: E402
from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.judge import latest_judgements  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from knowledge_assistant.config import get_judge_settings  # noqa: E402

RUNS = {"20260928-eval-A-full-491f137": "arm-a.jsonl", "20260928-eval-B-full-491f137": "arm-b.jsonl"}


def norm(x):
    return json.loads(json.dumps(x, ensure_ascii=False))


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: only in {'row' if k in a else 'ref'}")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
    elif a != b:
        out.append(f"{path}: row={a!r} ref={b!r}")
    return out


def jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


runs = erd.load_runs(list(RUNS), ROOT)
spans = erd.load_spans_by_case(ROOT)
report_indexes = erd.build_chunk_indexes(runs)
cfg_version = get_judge_settings().prompt_version
print("config judge prompt_version:", cfg_version)
total = {"records": 0, "diffs_vs_summary": 0, "diffs_vs_score_record_same_inputs": 0,
         "diffs_vs_score_record_full_index": 0, "spans_unavailable_true": 0}
for run in runs:
    rid = run["run_id"]
    arm = run["manifest"]["config"]["arm"]
    judgements, derived_version = erd.judgements_and_prompt_version(run["judgement_lines"])
    canonical_judgements = latest_judgements(jsonl(ROOT / "data/evaluation/results" / rid / "judgements.jsonl"))
    print(f"\n== {rid} arm={arm} records={len(run['records'])} derived_version={derived_version} "
          f"judgement keys report={len(judgements)} canonical={len(canonical_judgements)} "
          f"same_keys={set(judgements) == set(canonical_judgements)} "
          f"same_values={all(judgements[k] == canonical_judgements[k] for k in judgements)}")
    ref_rows = {(r["case_id"], r["arm"], r["mode"]): r
                for r in json.loads((ROOT / "data/evaluation/results" / rid / "summary.json").read_text(encoding="utf-8"))["rows"]}
    full_index = None
    if (CHUNKS / RUNS[rid]).exists():
        full_index = chunk_index(jsonl(CHUNKS / RUNS[rid]))
    rindex = report_indexes.get(arm)
    print(f"   report index chunks={len(rindex)}  full index chunks={None if full_index is None else len(full_index)}")
    dup_nonempty = sum(1 for r in run["records"] for c in r["retrieved"] if c.get("duplicate_chunk_ids"))
    print(f"   retrieved chunks with non-empty duplicate_chunk_ids: {dup_nonempty}")
    for rec in run["records"]:
        key = (rec["case_id"], rec["arm"], rec["mode"])
        total["records"] += 1
        row = norm(erd.score_row(rec, spans, rindex, judgements, derived_version))
        total["spans_unavailable_true"] += row.pop("spans_unavailable")
        # (1) vs committed canonical rows
        d1 = diff(row, norm(ref_rows[key]))
        # (2) vs score_record on the identical inputs
        d2 = diff(row, norm(scoring.score_record(rec, spans, rindex, judgements, derived_version)))
        # (3) vs score_record as EVAL-004a ran it: full index + config prompt version
        d3 = []
        if full_index is not None:
            d3 = diff(row, norm(scoring.score_record(rec, spans, full_index, canonical_judgements, cfg_version)))
        for name, d in (("summary", d1), ("score_record_same_inputs", d2), ("score_record_full_index", d3)):
            if d:
                total[f"diffs_vs_{name}"] += 1
                print(f"   DIFF {name} {key}: {d[:5]}")
print("\nTOTAL", total)
```

## Appendix B: `equiv_synth.py` (check 2, synthetic eval-split fixture, verbatim)

Run: `python equiv_synth.py <verify worktree>`. Output: 22 lines (one per arm x case, summarised in check 2), then `records=22 diffs=0 spans_unavailable_true=0`.

```python
"""VERIFY EVAL-003c check 2 (synthetic): score_row / score_runs vs scoring.score_record on an eval-split fixture that
exercises every branch. Offline, writes only under a temp dir."""
import json
import sys
import tempfile
from pathlib import Path

WT = Path(sys.argv[1])
sys.path[:0] = [str(WT / "src"), str(WT)]

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from scripts.evaluation import eval_report_data as erd  # noqa: E402
from tests.eval_report_fakes import (judgement_line, span_dict, write_judgements, write_manifest,  # noqa: E402
                                     write_records, write_spans_file)
from tests.judge_fakes import answer_verdict, chunk_entry, make_record, refusal_verdict  # noqa: E402


def norm(x):
    return json.loads(json.dumps(x))


def rec(n, run_id, arm="A", **kw):
    r = make_record(n, arm=arm, **kw)
    r["split"], r["run_id"] = "eval", run_id
    return r


def build(run_id, arm):
    records, lines = [], []
    r = rec(1, run_id, arm, cited=(1,)); records.append(r)                                   # correct
    lines.append(judgement_line(r, scoring.judge_check(r), answer_verdict()))
    r = rec(2, run_id, arm, answer="Part 2 [1] and [2].", cited=(1, 2)); records.append(r)   # partial, 1 bad marker
    lines.append(judgement_line(r, scoring.judge_check(r), answer_verdict(points=(("P1", "partial"),),
                                                                       markers=((1, "yes"), (2, "no")))))
    r = rec(3, run_id, arm, cited=(1,)); records.append(r)                                   # judge_error
    lines.append(judgement_line(r, scoring.judge_check(r), "", status="judge_error"))
    records.append(rec(4, run_id, arm, cited=(1,)))                                          # judgement missing
    records.append(rec(5, run_id, arm, mode="retrieval", cited=()))                          # retrieval mode
    r = rec(6, run_id, arm, cited=(2,))                                                       # duplicate rule
    r["retrieved"][0]["duplicate_chunk_ids"] = ["06:header-1600:0000"]
    r["retrieved"].append({**chunk_entry(6), "rank": 4})                                     # dup retrieved elsewhere
    records.append(r)
    lines.append(judgement_line(r, scoring.judge_check(r), answer_verdict(markers=((2, "no"),))))
    records.append(rec(7, run_id, arm, answerable=False, insufficient=True, cited=(), answer="Not in corpus."))
    r = rec(8, run_id, arm, answerable=False, cited=(1,)); records.append(r)                  # unanswerable, answered
    lines.append(judgement_line(r, scoring.judge_check(r), refusal_verdict(True)))
    r = rec(9, run_id, arm, insufficient=True, cited=(1,), answer="Not enough; related [1].")  # false refusal w/ note
    records.append(r)
    if scoring.judge_check(r):
        lines.append(judgement_line(r, scoring.judge_check(r), refusal_verdict(False)))
    records.append(rec(10, run_id, arm, status="error"))                                     # non-ok
    r = rec(11, run_id, arm, cited=()); records.append(r)                                    # answered, no citation
    lines.append(judgement_line(r, scoring.judge_check(r), answer_verdict(markers=())))
    return records, lines


root = Path(tempfile.mkdtemp())
spans_cases = {f"Q-TEST-{n:03d}": {"answerable": True, "slots": {"S1": [span_dict(f"{n:02d}", f"Doc > Part {n}")]}}
               for n in (1, 2, 3, 4, 5, 6, 9, 11)}
spans_cases.update({f"Q-TEST-{n:03d}": {"answerable": False, "slots": {}} for n in (7, 8)})
write_spans_file(root, spans_cases)
runs_def = {"20990101-eval-A-full-x": "A", "20990101-eval-B-full-x": "B"}
full_chunks = {}
for rid, arm in runs_def.items():
    d = write_manifest(root, rid, arm=arm, split="eval")
    records, lines = build(rid, arm)
    write_records(d, records)
    write_judgements(d, lines)
    full_chunks[arm] = [c for r in records for c in r.get("retrieved", [])]

spans = erd.load_spans_by_case(root)
runs = erd.load_runs(list(runs_def), root)
idx = erd.build_chunk_indexes(runs)
report_rows = erd.score_runs(runs, spans, idx)
n = diffs = unavailable = 0
for run in runs:
    arm = run["manifest"]["config"]["arm"]
    judgements, version = erd.judgements_and_prompt_version(run["judgement_lines"])
    full = chunk_index(full_chunks[arm])
    for record in run["records"]:
        n += 1
        a = norm(erd.score_row(record, spans, idx[arm], judgements, version))
        unavailable += a.pop("spans_unavailable")
        b = norm(scoring.score_record(record, spans, full, judgements, "judge_v1"))
        pipe = next(r for r in report_rows if (r["run_id"], r["case_id"], r["mode"]) ==
                    (run["run_id"], record["case_id"], record["mode"]))
        pipe = norm({k: v for k, v in pipe.items() if k not in ("run_id", "split", "spans_unavailable")})
        if a != b or pipe != b:
            diffs += 1
            print("DIFF", record["case_id"], arm, {k: (a.get(k), b.get(k)) for k in b if a.get(k) != b.get(k)})
        dup = (b["duplicate_rule_changed"] or [])
        res = (b["answer"] or {}).get("result")
        print(f"{arm} {record['case_id']} {record['mode']:9} status={record['status']:5} result={res} "
              f"judge={(b['answer'] or {}).get('judge_status')} dup_changed={bool(dup)} "
              f"auto={(b['citation'] or {}).get('auto_class')} judge_class={(b['citation'] or {}).get('judge_class')}")
print(f"records={n} diffs={diffs} spans_unavailable_true={unavailable}")
```

## Appendix C: `adapt_spot.py` (check 5, owner sheet via `map_result`, verbatim)

Run: `python adapt_spot.py <verify worktree> <scratch root with origin/eval-004 files>`. Output: the S01-S10 table in check 5, then `rule-based (map_result) agreement: 8/10 = 0.800; kappa=0.688`, the confusion matrix, and `holistic 'agree with the judge?' column: 9/10`.

```python
"""VERIFY EVAL-003c check 5: what score_spot_check.py *would* compute on the owner-graded EVAL-004a sheet, via a
scratch adapter. Read-only: parses the blind sheet + key file, re-derives the owner's label with map_result (the same
rule the judge label came from), then feeds (judge, human) pairs to score_spot_check's own pure functions."""
import json
import re
import sys
from pathlib import Path

WT, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(WT / "src"), str(WT)]

from knowledge_assistant.application.evaluation.judge import has_related_note  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.mapping import JudgeVerdict, map_result  # noqa: E402
from scripts.evaluation import score_spot_check as ssc  # noqa: E402

sheet = (ROOT / "validation/evaluation/judge-spot-check.md").read_text(encoding="utf-8")
key = (ROOT / "validation/evaluation/judge-spot-check-judge.md").read_text(encoding="utf-8")

owner = {}
for m in re.finditer(r"(?m)^## (S\d+) \((answer|refusal) check\)$", sheet):
    sid, check = m.group(1), m.group(2)
    end = sheet.find("\n## S", m.end())
    body = sheet[m.end(): end if end != -1 else len(sheet)]
    rows = {r[0].strip(): (r[1].strip(), r[2].strip()) for r in
            (line.strip("|").split("|") for line in body.splitlines() if line.startswith("| ") and "---" not in line)
            if len(r) >= 3}
    owner[sid] = {"check": check, "rows": rows}

judge = {}
for m in re.finditer(r"(?m)^## (S\d+)\n\n- Case: `(\S+)`, arm (\S+), run `(\S+)`\n- Check: (\w+);.*label: \*\*(\w+)\*\*", key):
    judge[m.group(1)] = {"case_id": m.group(2), "arm": m.group(3), "run": m.group(4), "check": m.group(5),
                         "label": m.group(6)}

records = {}
for sid, j in judge.items():
    lines = (ROOT / "data/evaluation/results" / j["run"] / "records.jsonl").read_text(encoding="utf-8").splitlines()
    recs = [json.loads(l) for l in lines if l.strip()]
    records[sid] = [r for r in recs if r["case_id"] == j["case_id"] and r["arm"] == j["arm"] and r["mode"] == "full"][-1]

pairs_rule, holistic, detail = [], [], []
for sid in sorted(owner):
    o, j, r = owner[sid], judge[sid], records[sid]
    rows = o["rows"]
    if o["check"] == "answer":
        points = tuple(v for k, (v, _) in sorted(rows.items()) if re.fullmatch(r"P\d+ covered", k))
        unsupported = rows["unsupported claims"][0]
        verdict = JudgeVerdict(required_points=points,
                               contradicts_ground_truth=rows["contradicts ground truth"][0] in ("yes", "true"),
                               unsupported_claims=() if unsupported in ("no", "none", "") else (unsupported,))
    else:
        verdict = JudgeVerdict(presents_related_as_answer=rows["presents_related_as_answer"][0] == "true")
    human = map_result(r["answerable"], r["insufficient"], has_related_note(r), bool(r["citations"]), verdict)
    agree_col = rows["agree with the judge? (fill after opening the key)"][0]
    pairs_rule.append((j["label"], human))
    holistic.append(agree_col == "yes")
    detail.append(f"{sid} {j['case_id']}:{j['arm']} {o['check']:7} judge={j['label']:18} owner_rule={human:18} "
                  f"holistic={agree_col:3} {'AGREE' if j['label'] == human else 'DISAGREE'}")

print("\n".join(detail))
agr = ssc.agreement_rate(pairs_rule)
print(f"\nrule-based (map_result) agreement: {agr['count']}/{agr['n']} = {agr['value']:.3f}; "
      f"kappa={ssc.cohens_kappa(pairs_rule):.3f}")
labels, matrix = ssc.confusion_matrix(pairs_rule)
print("confusion (rows judge, cols owner):", labels)
for lab in labels:
    print(f"  {lab:18}", [matrix[lab][h] for h in labels])
print(f"holistic 'agree with the judge?' column: {sum(holistic)}/{len(holistic)}")
```

## Appendix D: `mutate.py` (check 6, verbatim)

Run: `python mutate.py <scratch git-archive copy of HEAD> <python.exe>`. Output: the table in check 6.

```python
﻿"""VERIFY EVAL-003c check 6: mutations on a scratch copy; each must fail a test; files restored byte-for-byte."""
import hashlib
import subprocess
import sys
from pathlib import Path

M = Path(sys.argv[1])
PY = sys.argv[2]
TESTS = ["tests/unit/test_eval_report_data.py", "tests/unit/test_make_tables.py", "tests/unit/test_make_spot_check.py",
         "tests/unit/test_score_spot_check.py"]
ERD, MT, MSC = "scripts/evaluation/eval_report_data.py", "scripts/evaluation/make_tables.py", "scripts/evaluation/make_spot_check.py"

MUTANTS = [
    ("a1 spans_unavailable flag forced False", ERD,
     'row["spans_unavailable"] = record["answerable"] and not has_spans',
     'row["spans_unavailable"] = False'),
    ("a2 guard removed (has_spans always True)", ERD,
     'has_spans = (not record["answerable"]) or (record["case_id"] in spans_by_case)',
     'has_spans = True'),
    ("a3 excluded list dropped from every caption", MT,
     "    if excluded_spans:\n        parts.append(",
     "    if False:\n        parts.append("),
    ("b1 csv_rows: question <-> expected_answer values swapped", MT,
     '"question": record["question"], "expected_answer": record["expected_answer"] or "",',
     '"question": record["expected_answer"] or "", "expected_answer": record["question"],'),
    ("b2 per_case table: result <-> citation_auto_class cells swapped", MT,
     '            answer.get("result") or "–", _fmt(points_covered) if points_covered is not None else "–",\n'
     '            citation.get("auto_class") or "–",',
     '            citation.get("auto_class") or "–", _fmt(points_covered) if points_covered is not None else "–",\n'
     '            answer.get("result") or "–",'),
    ("b3 retrieval table: lenient <-> strict columns swapped", MT,
     'rows.append((f"source_hit@{k}", _mean_cell(_mean_of(summary, f"source_hit@{k}")), _mean_cell(_mean_of(summary, f"source_hit@{k}:strict"))))',
     'rows.append((f"source_hit@{k}", _mean_cell(_mean_of(summary, f"source_hit@{k}:strict")), _mean_cell(_mean_of(summary, f"source_hit@{k}"))))'),
    ("c1 seed ignored (Random(0))", MSC, "rng = random.Random(seed)", "rng = random.Random(0)"),
    ("c2 unseeded Random()", MSC, "rng = random.Random(seed)", "rng = random.Random()"),
    ("c3 stratification broken (constant stratum key)", MSC,
     'return row["answer"]["result"], record["language"]', 'return "all", "all"'),
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


for name, rel, old, new in MUTANTS:
    path = M / rel
    original = path.read_bytes()
    before = sha(path)
    text = original.decode("utf-8")
    assert text.count(old) == 1, f"{name}: anchor found {text.count(old)} times"
    path.write_bytes(text.replace(old, new).encode("utf-8"))
    runs = []
    for _ in range(3 if name.startswith("c2") else 1):  # unseeded: repeat to expose flakiness
        proc = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf", "--color=no", *TESTS], cwd=M,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        failed = [l.split(" - ")[0].replace("FAILED ", "") for l in proc.stdout.splitlines() if l.startswith("FAILED")]
        runs.append((proc.stdout.strip().splitlines()[-1], failed))
    path.write_bytes(original)
    restored = sha(path) == before
    print(f"\n[{name}]  restored_byte_for_byte={restored}")
    for summary, failed in runs:
        print(f"   {summary}   {'KILLED' if failed else 'SURVIVED'}")
        for f in failed:
            print(f"     - {f}")
```

## Appendix E: `denom.py` (check 7, verbatim)

Run: `python denom.py <verify worktree>`. Output: `unlabelled: ['Q-TEST-002:A'] accuracy n: 1 groundedness n: 1` / `citation answered n: 2 presence_rate: {'n': 2, 'count': 2, 'value': 1.0} ...`.

```python
"""VERIFY EVAL-003c check 7: does an unlabelled (judge_error / missing) answered answerable record enter the citation
denominator? The new evaluation-spec.md prose says unlabelled records are excluded from every denominator."""
import sys
from pathlib import Path

WT = Path(sys.argv[1])
sys.path[:0] = [str(WT / "src"), str(WT)]
from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan  # noqa: E402
from tests.eval_report_fakes import judgement_line  # noqa: E402
from tests.judge_fakes import answer_verdict, make_record  # noqa: E402

spans = {f"Q-TEST-{n:03d}": [ExpectedSpan(slot="S1", role=EXPECTED, source_id="01", heading_path="Doc > Part 1",
                                          variant=0, char_start=0, char_end=20)] for n in (1, 2)}
ok, err = make_record(1, cited=(1,)), make_record(2, cited=(1,))
lines = [judgement_line(ok, "answer", answer_verdict()), judgement_line(err, "answer", "", status="judge_error")]
judgements = {(l["case_id"], l["arm"], l["answer_sha256"], l["judge_prompt_version"]): l for l in lines}
rows = [scoring.score_record(r, spans, None, judgements, "judge_v1") for r in (ok, err)]
s = scoring.summarize(rows)
print("unlabelled:", s["answer"]["unlabelled"], "accuracy n:", s["answer"]["accuracy"]["n"],
      "groundedness n:", s["answer"]["groundedness_rate"]["n"])
print("citation answered n:", s["citation"]["answered"], "presence_rate:", s["citation"]["presence_rate"],
      "auto_class:", s["citation"]["auto_class"])
```

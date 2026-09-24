# EVAL-003c — Tables, CSV and spot-check tooling (every reported number is generated)

Read `agents/prompts/_common.md` first and follow it.
Entry: EVAL-003b done.

## Do
1. `scripts/evaluation/make_tables.py --runs RUN_A RUN_B [--out docs/reports/epics/EPIC-05-evaluation.md]`:
   - computes all EVAL-003b metrics from the run folders (never from hand-typed values);
   - writes Markdown tables **between markers** in the target report: `<!-- AUTO:retrieval -->…<!-- /AUTO:retrieval -->` (also `answer`, `refusal`, `citation`, `latency`, `cost`, `per_language`, `parallel`, `per_case`). Text outside markers is never touched; missing markers → append a new section, don't fail;
   - each table caption states: run ids, n, and which records were excluded and why;
   - `data/evaluation/results/summary-<runA>-<runB>.json` with every number used;
   - `data/evaluation/results/eval-table-<run>.csv` with at least the brief's 5 columns: `question, expected_answer, expected_source, generated_answer, result` (+ case_id, arm, language, citations, latency_total_ms).
   - Deterministic: running twice gives byte-identical output (test it).
2. **Judge spot-check tooling:**
   - `scripts/evaluation/make_spot_check.py --run RUN --fraction 0.2 --seed 42`: stratified sample by (`result`, language) → `docs/reviews/evaluation/judge-spot-check-<run>.md` with columns: case, question, expected answer, generated answer, cited excerpts, judge result, judge reason, **human_result** (blank), **human_note** (blank).
   - `scripts/evaluation/score_spot_check.py FILE`: reads the filled sheet → agreement %, Cohen's κ, confusion matrix (judge vs human), list of disagreements → writes into the report between `<!-- AUTO:judge_agreement -->` markers. Refuses to run while any `human_result` is blank.
3. Tests: markers replaced idempotently, text outside untouched; CSV has the 5 columns; stratified sampler reproducible with a seed and covers every stratum with ≥ 1 record; κ on a hand-computed 2×2 example.

## Do not
Run the real evaluation, or write any analysis text (that is EVAL-004 / EXP-001).

# EVAL-003c prompt log

Date: 2026-09-28 · Tool: Claude Code (background job) · Effort: medium-high

## Owner invocation (chat, verbatim)

```text
Run agents/prompts/09c-EVAL-003c-report-generator.md (EVAL-003c). Read ledger rows 09a/09b and the EVAL-003b report.
0. Own git worktree, branch eval-003c from current dev. Standard git block, PR into dev, do not merge, stop for 99-VERIFY.
   Zero Gemini requests. Another session is running the eval in parallel: do not read or depend on its run folders.
   Develop on the committed dev dry-run runs + hand-made fixtures.
1. Read split from run.json (the pre-fix dev records lack the split field).
2. Housekeeping from the EVAL-003b verify (non-blocking items):
   (a) evaluation-spec.md states in prose the answerable-vs-answered denominators and the nearest-rank percentile method;
   (b) add a test for a duplicated citation marker;
   (c) fix the "wrong section" → "wrong document" wording in the EVAL-003b report's Explain-it-back.
3. The generated report must show, per metric: lenient headline with strict next to it; judge_error/runner-error records
   listed, not silently dropped; gate refusals on answerable cases; the duplicate-rule change count; and a placeholder
   section for the owner's judge spot-check agreement (filled in later).
4. Report + "Explain it back", ledger 09c, AI_WORKLOG.
```

## Task prompt (`agents/prompts/09c-EVAL-003c-report-generator.md`, verbatim at the time of the run)

```text
# EVAL-003c — Tables, CSV and spot-check tooling (every reported number is generated)

Read `agents/prompts/_common.md` first and follow it.
Entry: EVAL-003b done.

## Do
1. `scripts/evaluation/make_tables.py --runs RUN_A RUN_B [--out docs/reports/epics/EPIC-05-evaluation.md]`:
   - computes all EVAL-003b metrics from the run folders (never from hand-typed values);
   - writes Markdown tables **between markers** in the target report: `<!-- AUTO:retrieval -->…<!-- /AUTO:retrieval -->` (also `answer`, `refusal`, `citation`, `latency`, `cost`, `per_language`, `parallel`, `per_case`). Text outside markers is never touched; missing markers → append a new section, don't fail;
   - each table caption states: run ids, n, and which records were excluded and why;
   - `data/evaluation/results/summary-<runA>-<runB>.json` with every number used;
   - `data/evaluation/results/eval-table-<run>.csv` with at least the brief's 5 columns: `question, expected_answer, expected_source, generated_answer, result` (+ case_id, arm, language, citations, latency_total_ms). These are the brief's column names; map them from the run record as in `evaluation-dataset-design.md` §18 (`expected_source` ← `expected_sources`, `generated_answer` ← `answer`, `latency_total_ms` ← `latency_ms.total`; owner 2026-09-25, REORIENT-001 C5).
   - Deterministic: running twice gives byte-identical output (test it).
2. **Judge spot-check tooling:**
   - `scripts/evaluation/make_spot_check.py --run RUN --fraction 0.2 --seed 42`: stratified sample by (`result`, language) → `docs/reviews/evaluation/judge-spot-check-<run>.md` with columns: case, question, expected answer, generated answer, cited excerpts, judge result, judge reason, **human_result** (blank), **human_note** (blank).
   - `scripts/evaluation/score_spot_check.py FILE`: reads the filled sheet → agreement %, Cohen's κ, confusion matrix (judge vs human), list of disagreements → writes into the report between `<!-- AUTO:judge_agreement -->` markers. Refuses to run while any `human_result` is blank.
3. Tests: markers replaced idempotently, text outside untouched; CSV has the 5 columns; stratified sampler reproducible with a seed and covers every stratum with ≥ 1 record; κ on a hand-computed 2×2 example.

## Do not
Run the real evaluation, or write any analysis text (that is EVAL-004 / EXP-001).
```

## Shared rules (`agents/prompts/_common.md`, verbatim at the time of the run)

```text
# Common rules for every task prompt (read this first)

## Before you start
1. Read `CLAUDE.md`, `docs/plans/master-plan.md`, `docs/specs/assignment-requirements.md`, and every ADR/spec the task names.
2. Check the task's entry condition. If it is not met, STOP and report why.
3. Check `git status`. If there are uncommitted changes you did not make, list them and ask before touching them.
4. Open `docs/plans/task-ledger.md`. Every prerequisite must be `verified`; otherwise STOP. If work for this task already exists (done outside the prompt set), audit it against this prompt instead of redoing it, and record the audit in the execution report.

## While working
- MUST NOT fabricate results, scores, latency, ground truth, or "tests passed". Unverified = say "unverified".
- Offline tests by default: `.venv/Scripts/python.exe -m pytest`. Live Gemini calls only when the task says so; every live result is cached to disk so quota is never spent twice.
- Existing symbols: run GitNexus impact analysis before editing (CLAUDE.md). New files: no impact check needed.
- An open decision (OD-x in master-plan §8) that blocks the task: give 2–3 options with trade-offs and a recommendation, then ask the user (AskUserQuestion). Record the answer in an ADR or the owning spec. Never decide silently.
- Keep the layer rules (presentation → application → core ← infrastructure). `tests/unit/test_project_structure.py` must stay green.
- Small, reviewable changes. No new dependency without saying why; add it to BOTH `pyproject.toml` and `requirements.txt`.

## When done (all steps required)
1. Save this prompt verbatim to `docs/prompt-log/claude-code/<TASK-ID>.md`.
2. Execution report → `docs/reports/execution/<TASK-ID>.md`: files changed, commands run, test summary (real output), what is unverified, deviations from the prompt.
3. Append an entry to `AI_WORKLOG.md` (format is in that file): what AI did, what the AI got wrong in this task and how it was found/fixed (only real events: failing tests, user corrections, wrong assumptions; write "none observed" if none).
4. Update task/epic status and gate checkboxes in `docs/plans/master-plan.md` and the epic file, and update the task's row in `docs/plans/task-ledger.md`.
5. Run `gitnexus_detect_changes()`, then commit: `<TASK-ID>: <summary>`. Do not push unless the task says so.
6. Final chat report: files, tests, gate status, open decisions, and an **"Explain it back"** section — 3–5 bullets the user must be able to defend in an interview (why this design, what the alternative was). Save the same bullets in the execution report (section "Explain it back") before the commit, so the verifier can check them; chat alone is not enough.
7. STOP. Do not start the next task. The user will run `99-VERIFY.md` for this task in a fresh session.
```

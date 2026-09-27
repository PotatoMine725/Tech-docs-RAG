# EVAL-004a prompt log

Date: 2026-09-28 · Tool: Claude Code (CLI), Claude Opus 5.5

Task file: `agents/prompts/11-EVAL-004-run-and-report.md`, part 1 only (runs and judging). The owner's invocation
overrides the prompt file where they differ (see the execution report, "Deviations").

## Owner invocation (chat, verbatim)

```text
Run agents/prompts/11-EVAL-004-run-and-report.md, PART 1 ONLY (runs + judging). The report tables come later, after
EVAL-003c (09c) is merged. Read ledger rows 09a, 09b, 11 and the EVAL-003a/003b reports first.

0. Own git worktree on a new branch eval-004 from dev (after the PR #17 merge). The tree must be clean: run.json records
   the commit, and a dirty tree is not allowed for these runs. OPENBLAS_NUM_THREADS=1. Standard git block, PR into dev, do not merge.
1. This is the first time the EVAL split is used. Rules:
   - No config, prompt, threshold or code change during or after the runs (Goodhart).
   - If something looks wrong, STOP and report. Do not tweak and re-run.
   - A resume is allowed only with an identical config.
2. Order:
   a. --estimate-only for both arms; print the embed/LLM estimate vs RPD.
   b. Full run, arm A, --split eval.
   c. Full run, arm B, --split eval (0 embed requests expected: the query vectors are cached from arm A).
   d. judge_run for run A, then for run B. Never concurrently with a runner.
   Budget: ≤ 40 embed, ≤ 170 LLM requests total. A quota error → stop and print the resume command; do not loop.
3. After the runs, sanity only, no analysis:
   - counts per arm (ok / error / judge_error);
   - gate refusals on answerable cases (listed);
   - fallback_used must be 0;
   - how many values the duplicate rule changed;
   - the first 429/5xx body if any was captured (redacted), which answers RAG-003's open question.
   Compute summary JSON with scoring.py for both runs (numbers only; the narrative is EVAL-004b).
4. Owner spot-check (ledger row 11, self-preference mitigation):
   - Build validation/evaluation/judge-spot-check.md with 10 judged records, stratified across result labels and arms (seed 42).
   - For each: question, ground truth, answer, cited passages, and EMPTY columns for the owner's verdict.
   - The judge's verdicts go in a SEPARATE file, so the owner grades blind first.
   - Do not fill in the owner columns.
5. Commit the run folders (records, judgements, run.json, errors) plus the summaries. Report docs/reports/execution/EVAL-004a.md
   with quota used, wall time, errors, and "Explain it back". Ledger row 11 (part 1 done), AI_WORKLOG. Stop.
```

## Exchanges during the task (verbatim where quoted)

1. Entry check: PR #17 (EVAL-003b) was verified (ACCEPT) but not merged, so `dev` had no `judge_run.py` / `scoring.py`.
   I stopped before creating anything and asked. Owner: "merge PR #17 then proceed with option 1" (option 1 = the
   owner merges PR #17, then branch `eval-004` from the new `dev`). I merged PR #17 (`491f137`) on that instruction.
2. Judge B returned one `judge_error` (Q-EVAL-002, arm B: citation marker 22 instead of 1). I stopped and asked. Owner:

```text
Option 1, as a rule that applies to BOTH arms equally:- every judge_error gets exactly one resume with the identical config (--max-llm-calls sized to the number of errors);- if it fails again, leave it unlabelled, list it, and stop retrying;- if arm A has any judge_error, apply the same single resume to it.Keep both attempts in judgements.jsonl. In the EVAL-004a report, record: the judge_error count before and afterthe resume per arm, the raw reason (marker 22 vs 1), and state it as a judge-reliability observation(format errors / total judge calls). Do not change the judge prompt or the parser.
```

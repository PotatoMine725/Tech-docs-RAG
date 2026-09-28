# EVAL-004b prompt log

Date: 2026-09-28 · Tool: Claude Code (CLI), Claude Sonnet 5

Task file: `agents/prompts/11-EVAL-004-run-and-report.md`, part 2 (tables, judge reliability, appendix, prose). Part 1
(the runs and judging) is EVAL-004a. The owner's invocation below overrides the prompt file where they differ.

## Owner invocation (background job task, verbatim)

```text
EVAL-004b: generate the evaluation report (part 2 of agents/prompts/11-EVAL-004-run-and-report.md) from the committed
eval-004 runs using the EVAL-003c tools. Own worktree, branch eval-004b from dev (after the PR #19 merge). Zero Gemini
requests. No config/code/prompt change. Standard git block, PR into dev, do not merge, stop for 99-VERIFY.
1. Generate docs/reports/epics/EPIC-05-evaluation.md + summary/CSV from both runs.
   - Lenient headline with strict next to it.
   - Unlabelled Q-EVAL-002:B listed.
   - Gate refusals on answerable cases listed per arm (A: 001, 016, 018; B: 016, 018).
   - Duplicate rule: 0 values changed.
   - Latency per stage p50/p95; cost estimate labelled "estimate, free tier used".
2. Judge reliability section:
   - owner spot-check 8/10 rule-based (kappa 0.69), 9/10 holistic, n=10; disagreements S03/S09/S10 with reasons;
   - judge format errors 2/61 (Q-EVAL-002:B, source id copied into the marker field);
   - 0 x 429/5xx in ~158 requests.
3. The brief's 5 columns (question, ground truth, expected source, generated answer, result) for all 36 cases x 2 arms,
   as a CSV/Markdown appendix.
4. Fix the stale "9 of 10 agree" line in EVAL-004a.md Limitations -> "8/10 rule-based (9/10 holistic)".
5. Report + "Explain it back", ledger row 11 -> done, AI_WORKLOG. EPIC-06 (EXP-001) may land in dev while you work;
   link to it from EPIC-05 only if it is merged, otherwise leave a TODO line.
```

## Notes on execution

- Entry check: PR #19 (EVAL-003c) was merged (`c863ea0`) before this task started; PR #20 (EXP-001/EPIC-06) was still
  open (not merged) throughout — left as a TODO line in EPIC-05 per instruction 5, not linked.
- No AskUserQuestion / clarification round was needed: the invocation's own numbered items, the already-existing
  EVAL-003c tools (`make_tables.py`, `score_spot_check.py`, `eval_report_data.py`) and EVAL-004a's committed run data
  fully determined the work. All numbers in the report are tool-derived or directly quoted from EVAL-004a.md /
  `records.jsonl` / `summary.json`, not hand-typed.

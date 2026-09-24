# EVAL-004 — Run evaluation (both arms), judge, spot-check, evaluation report (gate G5B)

Read `agents/prompts/_common.md` first and follow it.
Entry: EVAL-003a/b/c done. Before any live call, estimate today's calls (answers + judge) against master-plan §5 and tell the user; the daily reset is 14:00 UTC+7.

## Run order (stop and report after each numbered step if anything looks wrong)
1. Retrieval only (embeddings, cheap):
   `run_eval.py --arm A --mode retrieval` then `--arm B --mode retrieval` → `make_tables.py` retrieval section only. Check arm B used 0 new query-embedding requests.
2. Dry run: `run_eval.py --arm A --mode full --cases <3 ids: 1 EN, 1 VI, 1 unanswerable>` → read the 3 records by hand. A bug fix now → delete that dry-run folder, note it in the report.
3. Full answers: `--arm A --mode full`, then `--arm B --mode full` (resume with `--run-id` if quota/503 interrupts).
4. Judge: `judge_run.py` on both runs.
5. Tables: `make_tables.py --runs <A> <B>`.
6. **OD-13** (ask user; recommend 20 %, stratified, seed 42): `make_spot_check.py` for each run → the USER fills `human_result` → `score_spot_check.py`. If κ < 0.6, say so plainly in the report and list the disagreements; do not re-prompt the judge to raise agreement without logging it as a judge-prompt amendment.

## Report `docs/reports/epics/EPIC-05-evaluation.md` (you write the prose, tables come from markers)
1. Dataset: size, EN/VI mix, parallel groups, unanswerable cases, how ground truth was written and frozen (tag + commit date vs first index date — show both timestamps).
2. For each metric group (retrieval, answer, refusal, citation, latency, cost): **how it was measured** (definition, who judges, what is excluded) → AUTO table → 2–4 sentences of observation citing case IDs.
3. Judge reliability (spot-check agreement, κ, disagreements).
4. Measurement limitations: n ≈ 36 (one case ≈ 3 pp), single run per arm, self-grading bias, free-tier latency noise, VI detection limits.
5. Snapshot → `docs/snapshots/evaluation/<date>.md` (run ids, commit, file hashes).

## Do not
Edit ground truth, re-run only failed-looking cases to "improve" numbers, or type any number outside AUTO markers except when quoting a generated file.

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

## Fix round (2026-09-29, from EVAL-004b-verify)

The verifier's fix prompt (verbatim from [EVAL-004b-verify.md](../../reviews/evaluation/EVAL-004b-verify.md) §
"Fix prompt"):

```text
1. File: docs/reports/epics/EPIC-05-evaluation.md, "Dataset" section (the sentence beginning "The first index
   was built...").
   Expected behaviour: replace "The first index was built 2026-09-26 14:55:42 +0700 (commit a998b68, PR
   #10 rag-001b -> dev, 733/859 chunks for arm A/B), 7 h 22 min after the ground truth froze." with the
   correct first-build time and source: Arm A's live index build started 2026-09-26 09:12:06 +0700
   (validation/retrieval/indexing-log.jsonl, first entry, started_at: 2026-09-26T02:12:06+00:00 UTC;
   docs/reports/execution/RAG-001b.md "Arm A, live", D:\ChromaDB), ~ 1 h 39 min after the ground truth froze
   -- not the a998b68/14:55:42 PR-merge timestamp, which records when the later, zero-API-cost rebuild into
   data/chroma/ was committed, not when the first index was actually built. Keep the "frozen before either arm's
   chunks or embeddings existed" conclusion -- it still holds under the corrected numbers, just with a smaller gap.
   Also correct (or add alongside) the freeze citation: the eval-freeze-v1 tag points to commit 739676f
   ("EVAL-002: freeze eval-v1"), 07:31:08 +0700 -- 2 min 33 s before the 1dd3b88d PR-merge timestamp EPIC-05
   currently cites; either cite 739676f or note both timestamps.

2. File: docs/reports/epics/EPIC-05-evaluation.md, "Measurement limitations" (the "Single run per arm" bullet).
   Expected behaviour (recommended, non-blocking): add one sentence noting that any per-arm figure pulled
   directly from the committed summary.json (e.g. breakdown/arm/A/answer/accuracy = 23/32 = 0.719) is an
   unpaired, single-run-per-arm figure, and will legitimately differ from EPIC-06's paired McNemar table
   (Arm A accuracy 22/31 = 0.710) because EPIC-06 drops cases without a same-question partner in the other arm
   (e.g. Q-EVAL-002:A is correct but has no B partner) -- so a reader comparing the two reports should not read the
   difference as an inconsistency.
```

Owner additions on top of the fix prompt (verbatim):

```text
0. Merge origin/dev (it now contains PR #20, EXP-001) into eval-004b: merge commit, keep every AI_WORKLOG/ledger/master-plan
   entry chronologically. Run the suite: expect ~866.
1. Leakage timeline in EPIC-05 "Dataset":
   - The first index = Arm A live build into D:\ChromaDB starting 2026-09-26 09:12:06 +0700 (indexing-log.jsonl, RAG-001b.md).
   - The gap from the freeze is ~ 1 h 39 min.
   - Mention the later zero-cost rebuild into data/chroma (a998b68, 14:55) only as a separate, later event.
   - Keep the conclusion "frozen before any index" and cite both sources.
2. Replace the EPIC-06 TODO line with a real link to docs/reports/epics/EPIC-06-experiment.md.
3. Add one note to EPIC-05: per-arm figures here are unpaired (e.g. Arm A accuracy 23/32). EPIC-06 compares arms on paired
   cases (22/31, Q-EVAL-002 excluded), so the two reports legitimately differ.
4. Re-run make_tables.py: the AUTO tables must stay byte-identical (only prose changes). Commit, push, do not merge. Stop.
```

Execution notes:

- Step 0: fast-forwarded `eval-004b` to `origin/eval-004b` (picking up the `VERIFY EVAL-004b` commit `55f8b73`
  first), then merged `origin/dev` (PR #20 EXP-001, `81cb6da`). Two conflicts (`AI_WORKLOG.md`,
  `docs/plans/task-ledger.md`), both from independent same-day entries appended at the same anchor point;
  resolved by hand, keeping every entry from both sides (chronological order: EXP-001's original entry, 14:19-14:21;
  EVAL-004b's entry, 19:56-19:57; EXP-001's post-verify follow-up entry, 19:37-20:03 — the follow-up is placed last
  since its concluding action, the `origin/dev` merge into `exp-001`, is the latest event of the three). `master-plan.md`
  auto-merged with no conflicts. 866 passed, 1 deselected, matching the owner's expectation.
- Owner's "≈ 1 h 39 min" was a rounded estimate; recomputed precisely against both anchors (09:12:06 minus 07:31:08
  tag = 1 h 40 min 58 s; minus 07:33:41 PR-merge = 1 h 38 min 25 s) and reported both, since the report already cites
  both freeze timestamps.
- The verifier's fix prompt said to keep "frozen before either arm's chunks or embeddings existed" unchanged.
  Checked against the ledger (row 04a, INGEST-004) and `git log`: Arm A's 733 chunks (`data/processed/chunks/arm-a.jsonl`)
  were committed 2026-09-25 20:42:39 +0700 (`bdd43ba`) — the day *before* the 2026-09-26 07:31:08 freeze tag. The
  chunks therefore did exist before the freeze; only the embeddings/index did not. Corrected the sentence to
  "embeddings or index" and named the chunk commit, since the file's own Goodhart-risk argument depends on this
  being right (per this project's rule against unverified success/correctness claims). The Goodhart conclusion is
  unaffected: chunks alone reveal nothing about retrieval or answer output.
- `make_tables.py` re-run twice (once before the chunks/gap correction, once after) against the same two run ids;
  `summary-*.json` and both per-arm CSVs stayed byte-identical to the pre-fix committed hashes both times (SHA-256
  confirmed). Only `EPIC-05-evaluation.md`'s prose changed.
- Updated the stale SHA-256 for `EPIC-05-evaluation.md` in `EVAL-004b.md`'s Files table (the hash is disclosed there
  as commit-time-only, per that report's own footnote) and annotated (not rewritten) the wrong "First index built"
  row in the point-in-time snapshot `docs/snapshots/evaluation/2026-09-28.md`, per this project's rule that
  snapshots are point-in-time records.

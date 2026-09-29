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

The verifier's fix prompt is already stored verbatim in
[EVAL-004b-verify.md](../../reviews/evaluation/EVAL-004b-verify.md) § "Fix prompt" (items 1–2) — not re-quoted here
to avoid a second, possibly-drifted copy.

Owner additions on top of the fix prompt (verbatim, background-job task message):

```text
Owner additions to the EVAL-004b fix prompt:
0. Merge origin/dev (it now contains PR #20, EXP-001) into eval-004b: merge commit, keep every AI_WORKLOG/ledger/master-plan
   entry chronologically. Run the suite: expect ≈ 866.
1. Leakage timeline in EPIC-05 "Dataset":
   - The first index = Arm A live build into D:\ChromaDB starting 2026-09-26 09:12:06 +0700 (indexing-log.jsonl, RAG-001b.md).
   - The gap from the freeze is ≈ 1 h 39 min.
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
  resolved by hand, keeping every entry from both sides, ordered by when each entry's content was last touched:
  EXP-001's original entry (created `734e8ca` 14:19, last text `c7b440d` 14:21), EXP-001's post-verify follow-up
  entry (created `f7a72ff` 19:37, last text — the `origin/dev` merge into `exp-001` — `181c6b2` 20:03), then
  EVAL-004b's entry (created `fbc7fce` 19:56, but its "Verifier findings" bullet was appended later by `55f8b73`
  at 20:37 — the latest touch of the three, so it goes last). `master-plan.md` auto-merged with no conflicts.
  866 passed, 1 deselected, matching the owner's expectation.
- First edit pass copied the owner's "≈ 1 h 39 min" as given, and kept "frozen before either arm's chunks or
  embeddings existed" exactly per the verifier's "keep" instruction. An advisor review flagged both as worth
  double-checking before committing. Recomputed the gap from `git log`: 09:12:06 minus 07:31:08 (tag) = 1 h 40 min
  58 s; minus 07:33:41 (PR #8 merge) = 1 h 38 min 25 s — neither matches "1 h 39 min" exactly, so both are reported
  instead. For the chunks claim: `git log -1 --format=%ci` on `bdd43ba` (INGEST-004, Arm A's 733 chunks) gives
  2026-09-25 20:42:39 +0700, the day *before* the 2026-09-26 07:31:08 freeze tag (`739676f`) — chunks existed before
  the freeze, only the embeddings/index did not. Corrected the sentence to "embeddings or index" and named the
  chunk commit; the Goodhart conclusion itself is unaffected (chunks alone reveal nothing about retrieval or answer
  output). Both deviations from the owner's/verifier's exact wording are flagged for the owner in the execution
  report and worklog rather than applied silently.
- `make_tables.py` re-run twice (once before the chunks/gap correction, once after) against the same two run ids;
  `summary-*.json` and both per-arm CSVs stayed byte-identical to the pre-fix committed hashes both times (SHA-256
  confirmed). Only `EPIC-05-evaluation.md`'s prose changed.
- Updated the stale SHA-256 for `EPIC-05-evaluation.md` in `EVAL-004b.md`'s Files table (the hash is disclosed there
  as commit-time-only, per that report's own footnote), added a one-line parenthetical next to `EVAL-004b.md`'s own
  `a998b68` reference (a scope-check command list, not a claim, but worth flagging which commit that timestamp
  belongs to), and annotated (not rewritten) the wrong "First index built" row in the point-in-time snapshot
  `docs/snapshots/evaluation/2026-09-28.md`, per this project's rule that snapshots are point-in-time records.
- `gitnexus_detect_changes` (CLAUDE.md MUST) was **not run**: this task is docs-only (`git diff --name-status acae17f`
  shows 6 `docs/`/`AI_WORKLOG.md` files, zero `src/`/`config/`/`scripts/`/`tests/`), and the `eval-004b` worktree is
  not in GitNexus's repo registry (only the main checkout and the `eval-003c` worktree are indexed), so there was no
  matching index to run it against. Disclosed here as not evidenced, not claimed as passing.

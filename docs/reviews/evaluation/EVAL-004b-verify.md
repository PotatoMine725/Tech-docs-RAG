# EVAL-004b — Verify (99-VERIFY)

Task: `agents/prompts/11-EVAL-004-run-and-report.md`, part 2 only (tables, judge reliability, brief appendix, prose).
Claims: [`docs/reports/execution/EVAL-004b.md`](../../reports/execution/EVAL-004b.md). Change: branch `eval-004b`
(`fbc7fce`, `6a48172`, `b2dbdda`) from `dev` at `c863ea0`, PR #21 into `dev`, not merged. Verifier: own worktree
`.claude/worktrees/verify-eval-004b` (detached at `b2dbdda`), zero Gemini/embedding requests, `.env` never opened,
`OPENBLAS_NUM_THREADS=1`. Date: 2026-09-28.

## Step 0 — EXP-001 / dev gap

`origin/dev` (`81cb6da`) has PR #20 (EXP-001, `EPIC-06-experiment.md`) merged. `eval-004b`'s merge-base with `dev` is
`c863ea0`, its own tip (`b2dbdda`, 2026-09-28 19:57:49 +0700) predates `dev`'s merge of exp-001 (2026-09-28
20:10:28 +0700) — confirmed with `git merge-base --is-ancestor origin/exp-001 origin/dev` (yes) and `git merge-base
origin/dev origin/eval-004b` (`c863ea0`, not `81cb6da`). So `dev` has EXP-001, `eval-004b` does not, exactly as the
verify prompt anticipated. Noted for the executor's fix round; not merged here.

## Checks A–G

| # | Check | Verdict | Evidence |
| --- | --- | --- | --- |
| A | Acceptance/gate items | PASS | Re-ran `make_tables.py --runs 20260928-eval-A-full-491f137 20260928-eval-B-full-491f137 --out docs/reports/epics/EPIC-05-evaluation.md` and `score_spot_check.py validation/evaluation/judge-spot-check.md validation/evaluation/judge-spot-check-judge.md --out ...` myself. Output byte-identical to committed (see "Extra check 2"). `master-plan.md` gate G5B's 3 boxes independently checked: 72 records (36×2) confirmed in the appendix; every number traces to `summary.json`/CSVs (see checks 2-3, 6); judge spot-check n=10/κ=0.688/8:10/9:10 confirmed (see check 5). |
| B | Tests | PASS | `.venv/Scripts/python.exe -m pytest -q -m "not gemini"`, run twice from this worktree: **848 passed, 1 deselected** both times, no failure either run (matches the report's own final-run number; the one flaky failure the report describes did not reproduce here either — see extra check 8). No test files changed by this task (scope confirms), so no new-test-quality read applies. |
| C | Claims vs reality | **1 FAIL** | Every traced number matched except one: EPIC-05's "Dataset" section states the first index was built 2026-09-26 14:55:42 +0700 (commit `a998b68`). Primary evidence (`validation/retrieval/indexing-log.jsonl` first entry, `RAG-001b.md` "Arm A, live") shows the actual first build started 2026-09-26 09:12:06 +0700, in `D:\ChromaDB`. See "Extra check 4" below — full detail and fix. |
| D | Project rules | PASS | No `src/`/`config/`/`scripts/`/`tests/` file changed (scope diff). `git diff eval-freeze-v1 HEAD -- data/evaluation/questions/eval-v1.jsonl` empty → eval set unchanged since freeze. No excluded source id (14/19/24/27) appears as an `expected_source` in the 72-row appendix. Secret scan (`AIza...`, `api_key=`, `GEMINI_API_KEY=`, `sk-...`, `Bearer ...`, `password=`) on `git diff origin/dev...eval-004b` — 0 matches. `.env` not in the diff, never opened by this verify session. `tests/unit/test_project_structure.py` — 9 passed (layer rule still enforced; irrelevant to this docs-only task but confirmed green). |
| E | Scope | PASS | `git diff origin/dev...eval-004b --name-status`: 4 modified (`AI_WORKLOG.md`, `docs/plans/master-plan.md`, `docs/plans/task-ledger.md`, `docs/reports/execution/EVAL-004a.md`) + 8 new (all `docs/`/`data/evaluation/results/`), matching the execution report's own "Files" table exactly. The one deviation (EnterWorktree defaulting to `origin/main`) was caught and fixed before any file was touched, and is disclosed in the report — not an undisclosed decision. |
| F | Quality spot-read | PASS | No committed code this task (only the uncommitted scratch `tmp_render_appendix.py`, reproduced verbatim in the report's Appendix A). Read it: reads the two `make_tables.py`-generated CSVs, sorts by `(case_id, arm)`, escapes `\|`/newline for Markdown, writes 72 rows — matches the committed `eval-table-eval-004-appendix.md` (see check 6). No edge-case defect found (no untested quoting issue arises with this dataset: no `\|` or embedded newlines observed in the sampled generated answers). |
| G | Explain-it-back | PASS (except the timeline bullet, see C) | The four "Explain it back" bullets in `EVAL-004b.md` (zero Gemini calls; why S03 needed hand-adding; why the appendix is a separate file; why `section_precision` < `source_precision`/`auto_class`; why the EN/VI gap is a refusal story) were checked against the underlying data/code in checks 3, 5-8 below and are all correct. |

## Extra checks (owner's list)

**1. Scope.** `git diff origin/dev...eval-004b --name-status` (PowerShell, since a `git diff` inside the isolated
worktree via the rtk-wrapped Bash tool was refused as ambiguous): `AI_WORKLOG.md` (M), 4 `data/evaluation/results/*`
(A), `docs/plans/master-plan.md` (M), `docs/plans/task-ledger.md` (M), `docs/prompt-log/claude-code/EVAL-004b.md` (A),
`docs/reports/epics/EPIC-05-evaluation.md` (A), `docs/reports/execution/EVAL-004a.md` (M),
`docs/reports/execution/EVAL-004b.md` (A), `docs/snapshots/evaluation/2026-09-28.md` (A). No `src/`, `config/`,
`prompts/` file. **PASS.**

**2. Reproducibility.** From this worktree, using the main checkout's `.venv` (relative path `../../../.venv/Scripts/
python.exe`, `OPENBLAS_NUM_THREADS=1`):
- Saved the committed `EPIC-05-evaluation.md`, `summary-*.json`, both `eval-table-*.csv` to a scratch dir.
- Re-ran `make_tables.py --runs 20260928-eval-A-full-491f137 20260928-eval-B-full-491f137 --out
  docs/reports/epics/EPIC-05-evaluation.md`: regenerated report, summary JSON and both CSVs are **byte-identical**
  (`diff` clean; SHA-256 matches the report's own claimed hashes exactly, e.g. report `EPIC-05-evaluation.md` →
  `430a3b5f...94ef`, regenerated → same).
- Re-ran `score_spot_check.py validation/evaluation/judge-spot-check.md validation/evaluation/judge-spot-check-judge.md
  --out docs/reports/epics/EPIC-05-evaluation.md`: only diff is the `Sheet:`/`key:` absolute path line (this
  worktree's own path vs. the original task's worktree path) — which the report's own footnote (line 393-396)
  explicitly predicts and explains as invocation-path-dependent, not committed content. All numbers (8/10, κ=0.688,
  9/10, confusion matrix, three disagreements) identical.
- Restored the worktree to the committed state (`git checkout --`) afterward; confirmed clean.
**PASS — genuinely reproduced, not just re-diffed against itself** (first attempt used a wrong python path and
produced a false "identical" by not running at all; caught by checking the command's own exit status/output before
trusting the diff).

**3. Numbers vs sources / EPIC-05 vs EPIC-06 paired-unpaired note.** Every headline number in EPIC-05's Summary
traces to `data/evaluation/results/summary-20260928-eval-A-full-491f137-20260928-eval-B-full-491f137.json`
(`breakdown/overall/answer/accuracy` = 46/63 = 0.730; `lenient_accuracy` = 57/63 = 0.905; per-language 26/32 EN,
20/31 VI; etc. — all matched by direct read of the JSON). The task's example figure, Arm A accuracy 23/32, is real:
`breakdown/arm/A/answer/accuracy` = `{"n": 32, "count": 23, "value": 0.71875}` in the same file. `origin/dev`'s
`docs/reports/epics/EPIC-06-experiment.md` (merged via PR #20, not present in this branch) states explicitly: "Arm
A's accuracy in the table is 22/31 = 0.710, while `summary.json`'s unpaired figure is 23/32 = 0.719:
`Q-EVAL-002:A` is correct but has no B partner" — so EPIC-06 already documents this exact discrepancy on its own
side. EPIC-05 itself never displays a per-arm accuracy figure in prose (only combined/per-language/parallel-subset
tables) and never uses the word "unpaired," though it does note in "Measurement limitations" that EPIC-06 "addresses
[non-determinism] with paired statistics across the same 36 questions." **Not a hard FAIL** (EPIC-05 makes no false
claim; a reader would only hit the discrepancy by pulling `summary.json`'s `breakdown/arm` block directly), but the
owner's check asked for one or the other — recommending the fix below so a reader who does cross-reference the two
reports isn't left to work out the 23/32-vs-22/31 gap unaided.

**4. Leakage timeline. FAIL.** Freeze: EPIC-05 cites commit `1dd3b88d` (the PR #8 `eval-002`→`dev` merge),
2026-09-26 07:33:41 +0700 — confirmed by `git log -1 --format="%ci" 1dd3b88d`. However the `eval-freeze-v1` tag
itself points to `739676f` ("EVAL-002: freeze eval-v1"), 07:31:08 +0700, 2 min 33 s earlier — EPIC-05 cites the PR
merge, not the tagged commit. `data/chroma/` at `1dd3b88d` holds only `.gitkeep` (`git ls-tree -r 1dd3b88d --
name-only | grep chroma`) — confirms "no index existed yet" at freeze time.
First index: EPIC-05 states "The first index was built 2026-09-26 14:55:42 +0700 (commit `a998b68`, PR #10
`rag-001b` → `dev`, 733/859 chunks for arm A/B), 7 h 22 min after the ground truth froze." `a998b68`'s timestamp
(`git log -1 --format="%ci" a998b68`) is indeed 14:55:42 +0700, but reading `docs/reports/execution/RAG-001b.md`
("Arm A, live", "Where the index actually is") shows this is the commit for the PR that *also* documents a later,
**zero-cost rebuild** into `data/chroma/` at 14:38 (from the embedding cache, after the owner's 14:37 decision to
move `CHROMA_PATH`) — not the first build. The actual first index build was **Arm A, live, `D:\ChromaDB`,
2026-09-26 09:12:04-09:19:13 +0700** (RAG-001b report), confirmed independently from the raw
`validation/retrieval/indexing-log.jsonl`: its first line has `"arm": "A", "started_at":
"2026-09-26T02:12:06+00:00"` (UTC) = **09:12:06 +0700**. Arm B's own first live build was 14:09:55-14:22:04 +0700
(same source), also before the `a998b68` commit time.
**Correct reading:** ground truth froze at 07:31:08 (tag) / 07:33:41 (PR merge) +0700; the first index (Arm A) was
built **≈ 1 h 39-41 min later**, at 09:12:06 +0700 — not 7 h 22 min later at 14:55:42. The **"frozen before any
index" conclusion still holds** (freeze precedes the first build either way), but the cited time, gap and commit are
wrong and should be corrected — this is exactly the kind of claim `evaluation-spec.md`'s Goodhart-risk argument
depends on being right.

**5. Judge reliability.** EPIC-05's "Judge spot-check agreement" table: 8/10 rule-based (κ=0.688), 9/10 holistic —
matches the re-run in check 2 exactly. S03 (`Q-EVAL-012`, arm A): EPIC-05's account ("judge credited required point
P2 as `partial`; the owner's blind grade was `no`, with the note 'agree with judge on P1 but no on P2, as the answer
didn't give any clue about the generator silently skips validation for the type'") matches `EVAL-004a.md` lines
177-179 **verbatim** (same quoted owner note, same case id, same P1/P2 read). "n = 10 (small)" wording present in
both EPIC-05 ("n = 10 of 59 is small") and `EVAL-004a.md` ("n = 10 (small sample; wide uncertainty — OD-13...)").
**PASS.**

**6. Appendix.** `eval-table-eval-004-appendix.md`: 72 rows confirmed (36 × 2, `wc`/row count). 5 rows sampled at
`random.seed(12345)` (Q-EVAL-027:B, Q-EVAL-001:B, Q-EVAL-020:A, Q-EVAL-024:B, Q-EVAL-013:A) — for each, appendix
`question`/`expected_answer`/`expected_source` matched `eval-v1.jsonl`'s `question`/`expected_answer`/
`expected_sources[].source_id` exactly, and `generated_answer`/`result` matched the corresponding
`records/<run>/records.jsonl` answer text and `summary.json`'s `per_case` result label exactly. Q-EVAL-002:B's
`result` column in the appendix is blank (confirmed by direct read of that row) — matches the claim that it is shown
unlabelled. **PASS.**

**7. Cost/latency labelling.** Cost section: "estimate, free tier used" is the report's own stated wording (Cost
Observation); `scoring.py:312-313` computes `usd = (prompt_tokens * input_price + (output_tokens + thoughts_tokens) *
output_price) / 1_000_000` — confirmed at the source that `thoughts_tokens` is added into the output-priced term, not
just coincidentally zero here. Latency: fetched raw `latency_ms` for the four cited slow records — Q-EVAL-015:A
(`generate` 36583.7 ms, `throttle_wait` 35048.1 ms), Q-EVAL-030:A (37020.2 / 35229.6), Q-EVAL-014:B (42441.8 /
40867.8), Q-EVAL-029:B (39423.2 / 37698.3), all with `retry_wait: 0.0` — matches the report's corrected-latency-cause
sentence exactly (figures, and the "retry_wait is 0 on all four" claim). Confirmed 0 of 72 answer records and 0 of 61
judge lines have `retry_count > 0` or `fallback_used`, matching "retried/fallback: 0" in the latency table. (The
latency table's judge row n=60 vs. 61 raw judge lines is not a discrepancy: `judgements.jsonl` keeps both raw
attempts for the one Q-EVAL-002:B judge_error case per the report's own note, while the "clean" latency count
dedupes to the latest attempt per case×arm — 59 ok + 1 deduped judge_error = 60.) **PASS.**

**8. Flaky HNSW-compaction test.** Named:
`tests/unit/infrastructure/test_chroma_store.py::test_top_k_larger_than_the_collection_returns_everything`
(`chromadb.errors.InternalError: Error in compaction: Failed to get hnsw segment writer`, per the execution report).
Ran the full offline suite twice from this worktree: **848 passed, 1 deselected** both times — the flaky failure did
not reproduce here either. Logged as **QC-001 item** (non-blocking): this test touches ChromaDB's on-disk HNSW
segment state and has now been reported flaky at least twice (once in EVAL-004b's own run, not reproduced in either
of this verify session's two runs) — worth a QC-001 look at whether it needs isolation from concurrent
worktree/session ChromaDB access, but it is not blocking this review.

**9. Stale line / secret scan / offline test count.** `grep -rn "9 of 10 agree"` across this worktree: only hits are
the fix-documentation lines (`AI_WORKLOG.md`, `EVAL-004b.md`, prompt-log) describing the fix itself — no literal
stale instance remains in `EVAL-004a.md`. Secret scan (see check D) — 0 matches, `.env` untouched. Offline suite:
**848 passed, 1 deselected**, reproduced twice (see check 8) — matches the report's own final-run number.

## Verdict

**ACCEPT WITH FIXES** — 1 FAIL (leakage-timeline citation, check C/4), 0 UNVERIFIED. Everything else (scope,
reproducibility, appendix, judge reliability, cost/latency labelling, tests, project rules, explain-it-back) holds up
under independent re-derivation. Becomes `verified` after the fix below is re-verified.

## Fix prompt (run in a new session)

1. **File:** `docs/reports/epics/EPIC-05-evaluation.md`, "Dataset" section (the sentence beginning "The first index
   was built...").
   **Expected behaviour:** replace "The first index was built **2026-09-26 14:55:42 +0700** (commit `a998b68`, PR
   #10 `rag-001b` → `dev`, 733/859 chunks for arm A/B), **7 h 22 min** after the ground truth froze." with the
   correct first-build time and source: Arm A's live index build started **2026-09-26 09:12:06 +0700**
   (`validation/retrieval/indexing-log.jsonl`, first entry, `started_at: 2026-09-26T02:12:06+00:00` UTC;
   `docs/reports/execution/RAG-001b.md` "Arm A, live", `D:\ChromaDB`), **≈ 1 h 39 min** after the ground truth froze
   — not the `a998b68`/14:55:42 PR-merge timestamp, which records when the later, zero-API-cost rebuild into
   `data/chroma/` was committed, not when the first index was actually built. Keep the "frozen before either arm's
   chunks or embeddings existed" conclusion — it still holds under the corrected numbers, just with a smaller gap.
   Also correct (or add alongside) the freeze citation: the `eval-freeze-v1` tag points to commit `739676f`
   ("EVAL-002: freeze eval-v1"), 07:31:08 +0700 — 2 min 33 s before the `1dd3b88d` PR-merge timestamp EPIC-05
   currently cites; either cite `739676f` or note both timestamps.
   **Proven by:** this review's "Extra check 4" — `git log -1 --format="%ci"` on `1dd3b88d`/`739676f`/`a998b68`,
   `git ls-tree -r 1dd3b88d -- data/chroma` (only `.gitkeep`), `validation/retrieval/indexing-log.jsonl`'s first
   line, and `RAG-001b.md`'s "Arm A, live" / "Where the index actually is" sections.

2. **File:** `docs/reports/epics/EPIC-05-evaluation.md`, "Measurement limitations" (the "Single run per arm" bullet).
   **Expected behaviour (recommended, non-blocking):** add one sentence noting that any per-arm figure pulled
   directly from the committed `summary.json` (e.g. `breakdown/arm/A/answer/accuracy` = 23/32 = 0.719) is an
   **unpaired**, single-run-per-arm figure, and will legitimately differ from EPIC-06's **paired** McNemar table
   (Arm A accuracy 22/31 = 0.710) because EPIC-06 drops cases without a same-question partner in the other arm (e.g.
   `Q-EVAL-002:A` is correct but has no B partner) — so a reader comparing the two reports should not read the
   difference as an inconsistency.
   **Proven by:** this review's "Extra check 3" — `summary.json`'s `breakdown/arm/A` block, and
   `origin/dev:docs/reports/epics/EPIC-06-experiment.md`'s own explicit note on the same 23/32-vs-22/31 gap.

Both fixes are docs-only (no code, config, data file or committed number needs to change) and need no new Gemini or
embedding requests to apply or re-verify.

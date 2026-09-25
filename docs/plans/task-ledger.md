# Task ledger

The single place for task status (created by REORIENT-001, 2026-09-24). Filled from git history and files only.
The master plan links here instead of repeating statuses. Task order = `agents/prompts/README.md`.

## Rules
- **A task starts only when every prerequisite is `verified` here** (`agents/prompts/_common.md`, "Before you start" step 4). `verified with fixes` does **not** count: the fixes must be re-verified first.
- The task session updates its own row when it finishes (`_common.md`, "When done" step 4). The verifier session (`99-VERIFY.md`) sets `verified` / `verified with fixes`.
- Status values: `not started` · `in progress` · `done` (finished, not yet verified) · `verified` · `verified with fixes` (verdict ACCEPT WITH FIXES; fixes not yet re-verified) · `cut`.
- "Needs" mirrors the README "Needs" column. Commits are listed by hash; REORIENT-001's own commits by message.

## Ledger

| # | Prompt file | Task ID | Needs | Status | Commits | Execution report | Verify review → verdict | Open items |
|---|---|---|---|---|---|---|---|---|
| — | (none; pre-prompt-set, master plan EPIC-01 + gate G1) | CORPUS-001 (EPIC-01) | Phase 0 | done | `a69a12a` | [epic report](../reports/epics/EPIC-01-corpus-analysis.md) (no `docs/reports/execution/` file) | none | Never run through `99-VERIFY` (optional; no prompt in README needs CORPUS-001 directly). If run: requirements = master-plan §4 EPIC-01 deliverables + G1; claims = the epic report. No prompt-log copy exists (prompt given in chat before the prompt set; not reconstructed). Accepted gaps: see [REORIENT-001 report](../reports/execution/REORIENT-001.md) §Audit. |
| 00 | `00-HOUSE-001-repo-hygiene-and-submission.md` | HOUSE-001 | — | verified | `916b5bc`, `cdcdc67` | [HOUSE-001](../reports/execution/HOUSE-001.md) | [HOUSE-001-verify](../reviews/code/HOUSE-001-verify.md) → ACCEPT (`28f4c6f`) | Accepted gaps: `gitnexus_detect_changes()` not recorded; "git status clean" not met at commit time (disclosed); no test guards `.gitattributes`. |
| 00R | `00R-REORIENT-001-sync-state-with-prompts.md` | REORIENT-001 | 00, 01 done | verified | "CHORE: GitNexus index counts in CLAUDE.md/AGENTS.md"; "REORIENT-001: task ledger, prompt changelog, spec/prompt reconciliation"; "REORIENT-001: master plan synced to the prompt set" (branch `reorient-001`); "REORIENT-001: fixes from verification" | [REORIENT-001](../reports/execution/REORIENT-001.md) | [REORIENT-001-verify](../reviews/code/REORIENT-001-verify.md) → ACCEPT WITH FIXES (`a7f506e`); [REORIENT-001-reverify](../reviews/code/REORIENT-001-reverify.md) → ACCEPT | Fixes 1–5 of the first verify (applied in "REORIENT-001: fixes from verification") re-verified 2026-09-25 → ACCEPT. The REORIENT-001 prerequisite of 02 and 03 is now met. Open, non-blocking: (1) report Deviation 4 lists the wrong files for `c867943` (actually AI_WORKLOG, ledger, report, re-check sheet); (2) not evidenced: AskUserQuestion events for C1–C4, `gitnexus_detect_changes()` before the original commits (compare run after the fact: 0 processes, risk low). One-off: its entry rule was "done", not "verified" (written before this ledger existed). |
| 01 | `01-EVAL-001-design-dataset.md` (+ `docs/prompt-log/claude-code/EVAL-001 — Design Evaluation Dataset.md`) | EVAL-001 | 00 | verified with fixes | `585f434`, `a15f443`, `9e0ab15`, `ce04909`, `b58a50d`, `831d5a0`, `629b931` | [EVAL-001](../reports/execution/EVAL-001.md) | [EVAL-001-verify](../reviews/evaluation/EVAL-001-verify.md) → ACCEPT WITH FIXES (`e5e27b1`) | (1) Fixes in `629b931` not re-verified — see fix mapping below. (2) `831d5a0` (owner decisions D1–D3: slots in `blueprint.yaml`, tests, spec) came **after** the verify and was never verified. (3) [Owner re-check](../reviews/evaluation/EVAL-001-owner-recheck.md) of 009/010, 016, 022, 023, 024, 025, 031, 036: verdict lines empty. (4) A21 `gitnexus_detect_changes()` not recorded → accepted process gap. (5) A22 chat report not visible to the verifier → accepted (not re-checkable). |
| 02 | `02-EVAL-002-write-and-freeze.md` | EVAL-002 | 01 + owner review + 00R verified | not started | — | — | — | **Blocked** until all three: every `owner verdict:` in the owner re-check filled; EVAL-001 `verified` (re-verify, covering `629b931` and `831d5a0`); REORIENT-001 `verified`. |
| 03 | `03-INGEST-001-models-parser-normalization.md` | INGEST-001 | 00 + 00R verified (parallel with 01/02) | verified | `1858e27`; `98fdb5a` ("INGEST-001: fixes from verification") | [INGEST-001](../reports/execution/INGEST-001.md) | [INGEST-001-verify](../reviews/code/INGEST-001-verify.md) → ACCEPT WITH FIXES (`50f45b1`); [INGEST-001-reverify](../reviews/code/INGEST-001-reverify.md) → ACCEPT | Fixes 1–5 of the first verify re-verified 2026-09-25 → ACCEPT (`normalized.jsonl` unchanged, 63 tests pass). The INGEST-001 prerequisite of 04/05 is met. Open, non-blocking: (1) page-footer removal (`- Last updated on` + date + `---`, 19 docs), an extension of ADR-0003 D1: **confirmed by owner 2026-09-25**; (2) known residue (`---` before "Additional resources", #15 Q&A text): **kept, owner 2026-09-25**; (3) "#12/#13" → "#12": fixed in `864fb7e`; (4) byline regex could hit prose in a future corpus (INGEST-003). Not evidenced: pre-edit impact runs, chat "Explain it back". |
| 04 | `04-INGEST-002-chunkers-and-stats.md` | INGEST-002 | 03 | done | "INGEST-002: header-aware + fixed-size chunkers, chunk files, stats, G2 checks" (branch `claude/inspiring-cray-fspsdh`) | [INGEST-002](../reports/execution/INGEST-002.md) | — (run `99-VERIFY`) | G2 checks 11/11 PASS, 92 tests. Owner decision 2026-09-25: split-table header repeated in `embed_text` only. Open for the owner: 19 heading-only Arm A chunks from the D3 sibling-only merge (changing it needs an ADR-0003 amendment). |
| 05 | `05-INGEST-003-markitdown-optional.md` | INGEST-003 | 03 | not started | — | — | — | Cuttable (OD-15). |
| 06a | `06a-RAG-001a-embedder-and-cache.md` | RAG-001a | M1 (02) + 04 | not started | — | — | — | — |
| 06b | `06b-RAG-001b-chroma-and-indexing.md` | RAG-001b | 06a | not started | — | — | — | — |
| 07 | `07-RAG-002-retrieval-generation-citation.md` | RAG-002 | 06b | not started | — | — | — | — |
| 08 | `08-RAG-003-resilience-cli-smoke.md` | RAG-003 | 07 | not started | — | — | — | — |
| 09a | `09a-EVAL-003a-runner.md` | EVAL-003a | 08 | not started | — | — | — | — |
| 09b | `09b-EVAL-003b-metrics-and-judge.md` | EVAL-003b | 09a | not started | — | — | — | — |
| 09c | `09c-EVAL-003c-report-generator.md` | EVAL-003c | 09b | not started | — | — | — | — |
| 10 | `10-GUI-001-desktop-app.md` | GUI-001 | 08 (parallel) | not started | — | — | — | — |
| 11 | `11-EVAL-004-run-and-report.md` | EVAL-004 | 09c | not started | — | — | — | — |
| 12 | `12-EXP-001-experiment-and-failure-analysis.md` | EXP-001 | 11 | not started | — | — | — | — |
| 13 | `13-BONUS-001-hybrid-and-query-rewrite.md` | BONUS-001 | 12 | not started | — | — | — | Optional (OD-16). |
| 14 | `14-QC-001-final-submission.md` | QC-001 | 12 | not started | — | — | — | — |

`99-VERIFY.md` is not a task; it runs after every task and fills the "Verify review" column. SETUP-001 (`3d5a606`) predates both the plan and the prompt set and is not tracked here.

## EVAL-001: verify findings → fixing commit

Source: [EVAL-001-verify.md](../reviews/evaluation/EVAL-001-verify.md) (verdict, "Fix prompt"). Mapping built from `git show 629b931`. Nothing here is verified; the re-verify decides.

| Finding | Fix-prompt item | Fixed in | What changed | Check from the fix prompt (REORIENT-001 re-run, 2026-09-24) |
|---|---|---|---|---|
| C FAIL: design §19 "Plain semantic matches 6%" | 1 | `629b931` | `evaluation-dataset-design.md:132` → "9%" | Line 132 reads "Plain semantic matches 9%"; `coverage-matrix.yaml:355` `share_direct_semantic: 0.094`. |
| C FAIL: report "14 offline checks" | 2 | `629b931` | `docs/reports/execution/EVAL-001.md:13` → "17 offline checks (85 evidence quotes …)" | `pytest --collect-only -q tests/unit/test_evaluation_blueprints.py` → "17 tests collected"; `grep -cE "^ *quote:" blueprint.yaml` → 85. |
| A20 PARTIAL: stale "awaiting owner review" | 3 | `629b931` | `master-plan.md:29` and `:167`, `EPIC-05-evaluation.md:3`, `evaluation-dataset-design.md:3` | `grep -rn "awaiting owner review\|waiting for the owner's review" docs/` → 3 hits, all inside `EVAL-001-verify.md` itself (it quotes the old text); 0 in the three target files. |
| G: "23 accepted, 1 partly accepted" | 4 | `629b931` | `AI_WORKLOG.md:75`, `EVAL-001.md:31` → "22 accepted, 1 partly accepted, 1 decided by the author" | Wording matches review §5 Decision column. |
| G: list the DEV-006 rule as an open owner decision | 4 (second half) | superseded by `831d5a0` | Owner decision D2 (2026-09-24) confirmed and generalised the DEV-006 rule (review §5 "Owner decisions") | No longer open. |
| Run pytest + `gitnexus_detect_changes()` before the fix commit | 5 | `629b931` (commit only) | — | Neither run is recorded for `629b931`. REORIENT-001 re-ran pytest: 45 passed. |
| A21 UNVERIFIED: `detect_changes` not recorded | — | not fixable after the fact | — | **Accepted process gap** (here + `AI_WORKLOG.md`). Run before every commit from now on. |
| A22 UNVERIFIED: chat report not visible | — | n/a | — | Accepted: a chat is not an artifact. |
| A14 UNVERIFIED: the OD-4/OD-5 question event | — | n/a | — | Accepted: decisions are recorded in `evaluation-spec.md`. |

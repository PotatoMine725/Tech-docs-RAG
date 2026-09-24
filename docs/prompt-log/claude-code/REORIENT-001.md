# REORIENT-001 — Re-align the repo with the prompt set (one-off, no feature work)

Read `agents/prompts/_common.md` first and follow it.

## Why
Part of the work (CORPUS-001, HOUSE-001, EVAL-001) started **before** the prompt set in `agents/prompts/` existed, and some later fixes were made ad hoc. From now on the prompt set is the only workflow: tasks run in the order of `agents/prompts/README.md`, each followed by `99-VERIFY.md`. This task makes the repo's records match that, and closes the loose ends. It writes **no pipeline code** and changes **no ground truth**.

## Known state (verify each line — do not trust it)
| Task | Prompt | Evidence | Known open items |
|---|---|---|---|
| CORPUS-001 / EPIC-01 | (pre-prompt-set) | `a69a12a`, `docs/reports/epics/EPIC-01-corpus-analysis.md` | never verified by `99-VERIFY` |
| HOUSE-001 | `00-…` | `916b5bc`, `cdcdc67`; `docs/reviews/code/HOUSE-001-verify.md` = ACCEPT | — |
| EVAL-001 | `01-…` + original long prompt | `585f434` … `629b931`; `docs/reviews/evaluation/EVAL-001-verify.md` = ACCEPT WITH FIXES; fixes in `629b931` | fixes not re-verified; owner re-check of changed cases pending (009/010, 016, 022, 023, 024, 025, 031, 036); verifier UNVERIFIED items A21 (`gitnexus_detect_changes` not recorded), A22 |
| Prompt edits | — | `8d04044` (D1/D2 into 07/09a/09b) + an **uncommitted** edit to `09b` | not logged anywhere as prompt changes |
| Working tree | — | `CLAUDE.md`, `AGENTS.md` modified (GitNexus symbol counts only) | uncommitted |
| Everything from EVAL-002 on | `02` … `14` | nothing | not started |

## Do
1. **Task ledger** → create `docs/plans/task-ledger.md`, the single place for task status from now on. One row per prompt file in `agents/prompts/README.md` order (00 … 14, plus CORPUS-001 and this task): prompt file, task ID, status (`not started` / `in progress` / `done` / `verified` / `verified with fixes` / `cut`), commits, execution report, verify review + verdict, open items. Fill it from git history and files only.
2. **Audit the pre-prompt work against the current prompts** — for CORPUS-001 (against master-plan G1), HOUSE-001 (`00-…`) and EVAL-001 (`01-…` + its addendum + `_common.md` end steps): list each requirement → met / not met / not applicable, with evidence. Do NOT redo work that is met. Classify every gap: **must fix now** (a later task depends on it), **accept and document** (record in the ledger + AI_WORKLOG), or **n/a**. Fix only the must-fix gaps, and only documentation/records unless the user approves more.
3. **Spec ↔ prompt conflicts.** Grep the prompts `06a`–`14` against `docs/specs/*` and the ADRs for contradictions. One is already known:
   - `evaluation-spec.md` (line ~40) says an answer marked insufficient is `correct_refusal` with **no judge call**; the uncommitted edit to `09b` says an insufficient answer that carries a related-content note or related citations **goes to the judge** (so a refusal that still says "use MapGroup('/v1')" can be caught as a hallucination).
   For each conflict: show both texts, recommend one, **ask the user** (AskUserQuestion), then change the spec (decisions live in specs/ADRs) and make the prompt match. Log every prompt change in a new `agents/prompts/CHANGELOG.md` (date, file, what, why, decided by). Back-fill `8d04044` and the `09b` edit there.
4. **Master plan sync** (`docs/plans/master-plan.md`): task IDs = the prompt files (RAG-001a/b, EVAL-003a/b/c, REORIENT-001, VERIFY after each task); link the ledger instead of repeating statuses; add the rule "a task starts only when its prerequisites are `verified` in the ledger"; update the day-by-day timeline to the real position (EVAL-001 finished 24 Sep, so the plan is ahead). Keep the 1 Oct deadline and the cut line unchanged.
5. **Guard against this happening again** — add to `_common.md` → "Before you start": *4. Open `docs/plans/task-ledger.md`. Every prerequisite must be `verified`; otherwise STOP. If work for this task already exists (done outside the prompt set), audit it against this prompt instead of redoing it, and record the audit in the execution report.* Also add to "When done": *update the task's row in the ledger*. Log both in `CHANGELOG.md`.
6. **Close EVAL-001 properly:**
   - Map each FAIL/fix in `EVAL-001-verify.md` to the commit that fixed it; put the mapping in the ledger. Do not self-verify — recommend that the user runs `99-VERIFY.md for TASK-ID=EVAL-001` again in a fresh session.
   - Produce `docs/reviews/evaluation/EVAL-001-owner-recheck.md`: for each changed case (009/010, 016, 022, 023, 024, 025, 031, 036) one short block — what changed, old vs new ground truth, the supporting quote — with an empty `owner verdict: ` line. STOP and ask the user to fill it. EVAL-002 must not start until it is filled.
   - Record A21 (`gitnexus_detect_changes` not recorded) as an accepted process gap in the ledger + AI_WORKLOG, and run `gitnexus_detect_changes()` now before this task's commit.
7. **Commits** (separate, in this order): `CHORE: GitNexus index counts in CLAUDE.md/AGENTS.md` · `REORIENT-001: task ledger, prompt changelog, spec/prompt reconciliation` · `REORIENT-001: master plan synced to the prompt set`. Nothing else.

## Do not
Write or change code under `src/`, `scripts/`, `tests/`; edit `blueprint.yaml`, `coverage-matrix.yaml`, `evidence-map.yaml`; start EVAL-002 or INGEST-001; call Gemini; build indexes.

## Final report (chat)
1. The ledger table. 2. Gaps found per pre-prompt task and what was done with each. 3. Conflicts found and the user's decisions. 4. What the user must do next, in order — expected: (a) fill `EVAL-001-owner-recheck.md`, (b) run `99-VERIFY` for EVAL-001, (c) run `99-VERIFY` for REORIENT-001, (d) then `02-EVAL-002` and, in parallel, `03-INGEST-001`. STOP.

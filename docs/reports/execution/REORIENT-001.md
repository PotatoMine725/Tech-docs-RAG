# REORIENT-001 execution report: re-align the repo with the prompt set

**Date:** 2026-09-24 · **Prompt:** [`00R-REORIENT-001-sync-state-with-prompts.md`](../../prompt-log/claude-code/REORIENT-001.md) · **Model:** Claude Opus 5.5 (Claude Code) · **Branch:** `reorient-001` (git worktree `.claude/worktrees/reorient-001`, created from local `main` at `629b931`) · **Status:** done, not verified.

No pipeline code, tests, scripts or ground-truth files were changed. No Gemini call, no index.

## Files
| File | Change |
|---|---|
| `AGENTS.md`, `CLAUDE.md` | GitNexus count line only (owner's uncommitted tool refresh), own commit `CHORE: …` |
| `docs/plans/task-ledger.md` (new) | Ledger: one row per prompt + CORPUS-001; EVAL-001 fix → commit mapping |
| `agents/prompts/CHANGELOG.md` (new) | Prompt change log, back-filled `8d04044`, the owner's 09b and README edits |
| `agents/prompts/00R-…md` (new, owner's), `agents/prompts/README.md` (owner's 00R row) | Committed unchanged |
| `agents/prompts/09b-…md` | Owner's uncommitted edit (C1) + C2 label names + C3 judge input / span test + C4 points-covered |
| `agents/prompts/09a-…md`, `agents/prompts/02-…md` | C3 schema; 02 entry condition (re-check filled, EVAL-001 `verified`) |
| `agents/prompts/_common.md` | "Before you start" step 4 (verbatim from the prompt); "When done" step 4 also updates the ledger |
| `agents/prompts/99-VERIFY.md` | Verifier may update the ledger row; verdict → status rule |
| `docs/specs/evaluation-spec.md` | C1 routing, C2 names fixed, C3 schema pointer, C4 formula; status line |
| `docs/reviews/evaluation/EVAL-001-owner-recheck.md` (new) | 9 changed cases, old vs new, quotes, empty verdict lines |
| `docs/prompt-log/claude-code/REORIENT-001.md` (new), `docs/prompt-log/README.md` | Prompt copy (`cmp` → identical) and index |
| `AI_WORKLOG.md` | REORIENT-001 entry; A21 recorded as an accepted process gap |
| `docs/plans/master-plan.md` | Task IDs = prompt files, ledger link, start rule, timeline (separate commit) |

## Commands run (real output)
- `git rev-parse main origin/main`: local `main` = `629b931`, `origin/main` = `e82c922`; 19 unpushed commits. The worktree was therefore made from local `main`, not origin.
- Owner's uncommitted files copied into the worktree: `AGENTS.md`, `CLAUDE.md`, `agents/prompts/09b-…`, `agents/prompts/README.md`, `agents/prompts/00R-…` (untracked).
- `.venv/Scripts/python.exe -m pytest -q` (the main checkout's interpreter; the worktree has no `.venv`; `knowledge_assistant` is not installed, so the worktree's own `src` is tested): **45 passed in 2.18s**. `tests/unit/test_corpus_inventory.py` + `tests/unit/infrastructure/test_markdown_structure.py`: **19 passed**.
- `pytest --collect-only -q tests/unit/test_evaluation_blueprints.py` → 17 tests collected; `grep -cE "^ *quote:" blueprint.yaml` → 85; `coverage-matrix.yaml:355 share_direct_semantic: 0.094`.
- `grep -rn "awaiting owner review\|waiting for the owner's review" docs/` → 3 hits, all in `EVAL-001-verify.md` quoting the old text.
- Blueprint diff for the re-check sheet: parsed `blueprint.yaml` at `9e0ab15` vs HEAD, per case, fields that differ (script in the job scratchpad; output summarised in the sheet).
- `grep` for the old field/label names across `agents/prompts` and `docs/specs` after the edits: only the judge's own output key `required_points` remains (correct, it rates required points).
- `gitnexus_detect_changes(repo="Tech-docs-RAG")` before each commit: see "detect_changes" below.

## Audit of pre-prompt work
Classification: **met** / **not met** / **n/a**; gaps → **must fix now** (a later task depends on it) / **accept and document** / **n/a**.

### CORPUS-001 (against master-plan §4 EPIC-01 + G1; `_common.md` did not exist yet)
| Requirement | Result | Evidence | Gap handling |
|---|---|---|---|
| Manifest: 24 IDs, none of 14/19/24/27, no #25 | met | tests `test_manifest_lists_exactly_the_24_accepted_sources`, `test_manifest_records_excluded_ids_and_the_missing_25` (19 passed above) | — |
| Checksums match `docs/snapshots/corpus/` | met | `test_sources_are_unchanged_since_the_premigration_snapshot`; also re-checked by the HOUSE-001 verifier (A3) | — |
| Section inventory covers all 24 docs, headings outside code fences | met | `test_inventory_matches_a_fresh_computation_for_all_24_documents`; `markdown_structure.py` tests | — |
| Topic map → `docs/knowledge/domain/` | met | `corpus-topic-map.md` (`a69a12a`) | — |
| README dataset draft | met | `README.md` (`a69a12a`) | — |
| Epic report → `docs/reports/epics/` | met | `EPIC-01-corpus-analysis.md` | — |
| pytest passes | met | 45 passed (above) | — |
| Prompt saved verbatim to prompt-log | not met | no file | accept and document (given in chat before the prompt set; not reconstructed, to avoid inventing a "verbatim" copy) |
| Execution report in `docs/reports/execution/` | not met | epic report serves as the claims file | accept and document |
| AI_WORKLOG entry | met | back-filled in HOUSE-001 | — |
| `gitnexus_detect_changes()` before commit | not met (not recorded) | — | accept and document |
| Independent `99-VERIFY` | not met | none | accept and document; optional verify, inputs named in the ledger. No README prompt lists CORPUS-001 as "Needs", so the new rule does not block on it. |
| Open difference: 498 vs 450 deduplicated sections (ADR-0003 vs inventory) | disclosed | EPIC-01 report | n/a (no decision depends on it) |

### HOUSE-001 (against `00-…` + `_common.md`)
Verified ACCEPT in `docs/reviews/code/HOUSE-001-verify.md` (A1–A12). Not redone.
| Requirement | Result | Gap handling |
|---|---|---|
| Do 1–6, pytest green | met (verifier A1–A10, A12) | — |
| Done when: `git status` clean | not met at commit time (verifier A11, disclosed) | accept and document; now clean except owner files, which this task commits |
| `_common` 1–3 (prompt log, report, worklog) | met (`HOUSE-001.md` in prompt-log, report, worklog entry) | — |
| `_common` 5: `detect_changes` before commit | not recorded | accept and document |
| No test guards `.gitattributes` (verifier note) | not met | accept and document (low risk; INGEST-001 normalizes `\r\n` anyway) |

### EVAL-001 (against `01-…`, its full prompt, the addendum, `_common.md` end steps)
Verified ACCEPT WITH FIXES in `docs/reviews/evaluation/EVAL-001-verify.md`. Not redone.
| Requirement | Result | Gap handling |
|---|---|---|
| Full prompt §22 gate, addendum 1–4 | met (verifier A1–A17, A23) | — |
| Two stale values (C FAILs), stale status lines (A20) | fixed in `629b931`, not re-verified | **must fix now** → re-verify (EVAL-002 depends). Mapping in the ledger. Not self-verified. |
| `831d5a0` (D1–D3: slots, tests, spec) came after the verify | never verified | **must fix now** → same re-verify must cover it |
| Owner re-check of changed ground truth | not done | **must fix now** → `EVAL-001-owner-recheck.md` created; owner fills it before EVAL-002 |
| `_common` 1 prompt saved | met (A18) | — |
| `_common` 2–3 report, worklog | met (A19) | — |
| `_common` 4 status in plan/epic | met after `629b931` | — |
| `_common` 5 `detect_changes` (A21) | not recorded | accept and document (ledger + AI_WORKLOG) |
| `_common` 6 chat report (A22) | not checkable | accept and document |
| Downstream prompts carry D1/D2 | partly (`8d04044`), and the field schema in 02/09a was still flat | **must fix now** → C3 below |

## Spec ↔ prompt conflicts (prompts 02–14 vs `docs/specs/*`, ADR-0003/0004)
All four were shown to the owner with both texts (AskUserQuestion). The owner chose the recommended option each time. Each decision is recorded in `evaluation-spec.md` and in `agents/prompts/CHANGELOG.md`.
| # | Spec text | Prompt text | Decision |
|---|---|---|---|
| C1 | `evaluation-spec.md:40` "if the system marks the answer insufficient, the result is `correct_refusal` (no judge call)" | 09b (owner edit): insufficient + related note/citations → judge refusal check | Judge checks them; bare refusal = no call. Spec rewritten. |
| C2 | spec: `correct_evidence` / `correct_source_wrong_evidence` / `unsupported_citation` / `citation_missing` | 09b §4: `correct_evidence` / `right_source_wrong_evidence` / `unsupported` / `missing` | Spec names; 09b renamed. |
| C3 | design §18: `answer_points{required}`, sources/alternates with `slot`, `acceptable_variations`, `citation_criteria` | 02/09a: flat `expected_source_ids`, `expected_heading_paths`, `evidence_quotes`, `required_points`; 09b judge input without optional points/variations; 09b "every eval case has ≥ 1 span" vs spec (insufficient cases have no source) | Prompts follow §18; span test = answerable cases, per slot. |
| C4 | OD-5: points-covered score = required present ÷ required | 09b: score missing; `partial` undefined | yes = 1, partial = 0.5, optional ignored; added to spec and 09b (+ test). |

Checked without a conflict: 06a/06b vs ADR-0004 D10/D13 (retry schedule in the ADR is "e.g."; dimension and distance are ADR-0005 decisions); SQLite cache in 06a (CLAUDE.md rule 2 allows it for a concrete need, the prompt requires the reason in ADR-0005); 07 vs generation/citation/retrieval specs (D2 carried by `8d04044`; threshold is TBD in the spec, decided in RAG-002); 09a/09c/11/12 vs evaluation-spec (top-k 5, per-language breakdowns, retried calls separate, dev set for tuning only); 12 vs ADR-0003 failure-mode list.

## detect_changes
- Before `CHORE: …`: `risk_level: low`, 8 changed sections in 4 docs files, `affected_processes: []`. The GitNexus index is registered to the main checkout (last indexed `b58a50d`), so it reports that checkout's diff, which was identical to the owner's files copied here.
- Before the second and third commits: see AI_WORKLOG (same limitation; only Markdown sections can appear).
- `npx gitnexus analyze` was **not** run: it would rewrite the count lines just committed.

## Unverified
- Nothing here is independently verified. REORIENT-001 needs its own `99-VERIFY`.
- `99-VERIFY.md` edit (verifier may update the ledger) is Claude Code's inference from the owner's ledger rule: owner to confirm.
- Whether the owner's main checkout has further edits to `agents/prompts/` made after the copy (checked at hand-off, see final report).

## Deviations from the prompt
1. Work is on branch `reorient-001` in a worktree (background-session isolation), not directly on `main`. The owner merges.
2. Extra prompt edits beyond the conflict fixes: 02 entry condition, 99-VERIFY ledger rights. Both logged in the CHANGELOG.
3. The "CHORE" commit was made before the conflict questions (it is independent of them), which preserves the prompt's commit order.

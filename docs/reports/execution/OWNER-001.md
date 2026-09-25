# OWNER-001 execution report

Task: apply the owner's EVAL-001 re-check verdicts and accept the INGEST-003 AI decisions from the 2026-09-25 handoff. Prompt: [OWNER-001](../../prompt-log/claude-code/OWNER-001.md) (given in chat). Branch `owner-001` from `dev` `bccd888`. No pipeline code changed.

## Entry condition
- `dev` up to date with `origin/dev` (`bccd888`, after `git fetch`).
- INGEST-003 `verified` in `task-ledger.md` row 05; V-2 on Windows 3.13.3 recorded as passed (113 tests).
- Working tree: only the untracked `.claude/worktrees/` (not touched).

## Files changed
| File | Change |
|---|---|
| `docs/reviews/evaluation/EVAL-001-owner-recheck.md` | All 9 verdict lines filled verbatim, each marked "(owner, 2026-09-25)"; new block "Additional change: BP-EVAL-017" with the owner's verdict; header now says filled. |
| `data/evaluation/questions/blueprint.yaml` | 016: #20 "Familiar C# features" alternate removed (both #07 alternates kept). 024: P1 = owner's wording. 017: "IMiddleware" (expected) and #10 "Service lifetimes" (alternate) moved to slot S2; intro + "Additional resources" stay S1; citation rule = one citation per slot. No evidence quote changed. |
| `data/evaluation/questions/coverage-matrix.yaml` | Regenerated with `scripts/evaluation/build_coverage_matrix.py`: only change is BP-EVAL-016 removed from source #20's `alternate` list. |
| `tests/unit/test_evaluation_blueprints.py` | New `test_two_slot_single_source_cases_keep_their_slots`: 022 S1 = Redirects, S2 = ReExecute (expected and older-H2 alternates, by heading suffix); also guards 017's S1/S2 (see Deviations). |
| `docs/specs/evaluation-spec.md` | § Retrieval hit rule: 017 listed as multi-slot; citation line says "multi-slot"; new strict/lenient bullet with the example; MRR and slot fraction stay lenient; headline number TBD / DECISION REQUIRED. |
| `agents/prompts/09b-EVAL-003b-metrics-and-judge.md` | §1 strict + lenient hit, spans tagged `expected`/`alternate`, 017 multi-slot; §5 slot test: {04, 20} → lenient hit, strict miss; {04, 26} → hit both; {20, 26} → miss both, fraction 0.5. |
| `agents/prompts/CHANGELOG.md` | Row for the 09b change. |
| `docs/specs/evaluation-dataset-design.md` | §18 slot paragraph: 017 now two slots (was "the owner can split it"); §20 row: re-check filled. |
| `docs/architecture/decisions/0002-markitdown-and-header-chunking.md` | Amendment: "pending owner review" → "accepted by the owner 2026-09-25, OWNER-001". |
| `docs/architecture/ingestion-architecture.md`, `docs/plans/master-plan.md` (OD-6 row) | OD-6 and the related INGEST-003 decisions marked accepted by the owner. |
| `docs/plans/epics/EPIC-07-final-qc.md` | New "Known limitations" section (N1, N2) for the README. |
| `docs/plans/epics/EPIC-05-evaluation.md` | Status line: re-check filled and applied, pending verify. |
| `docs/plans/task-ledger.md` | New OWNER-001 row (`done`); row 02: waits for OWNER-001 `verified`; row 05: decisions accepted, N1/N2 = known limitations. |
| `AI_WORKLOG.md`, `docs/prompt-log/claude-code/OWNER-001.md`, this report | Close-out. |

Not changed: the handoff note, past reviews and past execution reports (point-in-time files, CLAUDE.md rule 10); the prompts README "Needs" column.

## Commands run (real output)
- `.venv/Scripts/python.exe scripts/evaluation/build_coverage_matrix.py` → `wrote data/evaluation/questions/coverage-matrix.yaml`; `git diff` = 1 line removed (`- BP-EVAL-016` under #20 `alternate`).
- `.venv/Scripts/python.exe -m pytest tests/unit/test_evaluation_blueprints.py -q` → `18 passed in 2.27s` (17 before + 1 new).
- Mutation checks of the new test (file restored from a backup afterwards, then 18 passed again):
  - 022 older-H2 ReExecute alternate slot S2 → S1: `1 failed`.
  - 017 #10 "Service lifetimes" alternate slot S2 → S1: `1 failed`.
- Full suite, Windows, `Python 3.13.3`: `.venv/Scripts/python.exe -m pytest -q` → `114 passed in 3.88s`.
- `gitnexus_detect_changes(scope=all)` before the commit: risk `low`, 15 files, 0 affected processes. Changed symbols: doc sections in the edited Markdown files, plus three existing test functions below the new test, flagged `touched` only because their line numbers shifted (their bodies are unchanged in `git diff`).

## Unverified / open
- Which hit value (strict or lenient) is the headline number: **TBD / DECISION REQUIRED** (EVAL-003c/EVAL-004). The owner's condition covers only source and section hit; this task did not extend strict to MRR or the slot fraction.
- 017 now needs both sections in the top 5, like 022, but its `retrieval_challenges` does not contain `two_sections_needed` (022's does). Not added: that is a label change the owner did not ask for, and it would change coverage-matrix counts. Suggest the verifier or owner decide.
- No GitNexus impact run: no existing function/class was edited (only a new test function added).

## Deviations from the prompt
- The new test also guards 017's two slots (the prompt asked for 022 only). Reason: the 017 split is an owner decision that nothing else checks.
- The 09b test case names roles (04 and 26 expected, 20 alternate) and adds the {04, 26} case; the prompt's example is kept exactly (`{04, 20}` → lenient hit, strict miss).
- "Limitations note for the final README": put in `EPIC-07-final-qc.md` (the epic that owns the README), because the root README has no Limitations section yet.

# GUI-001-pre — PySide6 window against a fake use case

Branch `gui-001-pre` (from origin/dev). Owner exception (2026-09-26) to the ledger prerequisite rule: needs only the
AnswerResult contract of prompt 07 §1, not the pipeline. Wiring to the real use case = GUI-001 proper.

## Files
- `src/knowledge_assistant/presentation/desktop/viewmodels/contracts.py` — the only file that knows the result shape
  (`AnswerResult`, `Citation`, `AskQuestionPort`, `AskQuestionError`); top comment "mirror of AnswerResult (prompt 07 §1) — reconcile in GUI-001".
- `viewmodels/fake_ask_question.py` — `FakeAskQuestion`: EN answer (2 citations), VI answer, insufficient EN/VI (one with a related-only citation), quota/503/no-index errors, 3 s "slow" delay.
- `viewmodels/ask_viewmodel.py` — state machine idle/busy/answer/insufficient/error; no Qt import.
- `workers.py` — `QtExecutor` (QThreadPool + QRunnable, result delivered to the GUI thread by a queued signal).
- `windows/main_window.py` — question box (Enter), arm selector, busy bar, answer area, citation list + detail (excerpt + URL), status line, Copy button; distinct amber/red banners.
- `app.py` — `--fake` launch (without it: message, exit 2).
- `tests/presentation/desktop/test_ask_viewmodel.py` (11 tests, sync executor, no Qt), `test_main_window_smoke.py` (2 tests, offscreen).
- `validation/generation/gui-check.md` — owner checklist. `requirements.txt` — added `PySide6>=6.6,<7.0` (already in pyproject).

## Commands and results (real output)
- `.venv\Scripts\python.exe -m pytest tests/presentation tests/unit/test_project_structure.py -q` → 22 passed.
- Full `pytest -q` (worktree root, main venv) → **201 passed, 1 deselected** (gemini).
- Mutation proof: in `AskViewModel._on_ok` replaced `INSUFFICIENT if result.insufficient else ANSWER` with `ANSWER` → 3 failed
  (`test_insufficient_result_gives_insufficient_state`, `test_insufficient_can_carry_related_only_citation_vi_and_en`, widget `test_insufficient_and_error_look_different`), 12 passed. Restored; full suite green again.
- `app.main([])` returns 2 with the message (no window).
- Structure test green: no chromadb / google.genai import in presentation.

## Unverified
- The window has never been looked at by a human, and `python -m …app --fake` was not run interactively (offscreen tests only). Owner checklist rows all unticked.
- Real thread-pool responsiveness during the 3 s delay is only indirectly tested (submit returns while BUSY; results arrive via events). Checklist row 9 is the real proof.
- GitNexus `detect_changes` returned "no changes" for the staged diff (index probably tracks the main checkout, not this worktree) — so it proved nothing. `impact(main)` on `app.py` was LOW (1 direct caller, 0 flows).

## Deviations
- PySide6 was missing from the shared `.venv`; I ran `pip install PySide6` (6.11.2) there. Harmless to RAG-001b but it is a change to a shared env.
- No `docs/prompt-log` file, ledger, AI_WORKLOG, CHANGELOG, master-plan edits (boundary said shared docs are off-limits) — see merge lines below.
- Launch from a worktree needs `PYTHONPATH=src` (the venv's editable install points at the main checkout). After merge to dev the plain command works.
- `AskQuestionError(kind, message)` is my invention for the error path; the real use case will raise other exceptions (`GenerationError`, `RetrievalError`, Gemini errors). Unknown exceptions already show "Something went wrong: …"; reconcile in GUI-001.
- UI strings are English only.

## Addendum — owner check of rows 7/8
Owner reported rows 7 and 8 showed the same red banner. Not reproduced in an offscreen run of the real window (each
message was different under the banner); the generic banner was however identical by design. Added per-kind banner
titles (`Quota used up` / `Model service unavailable` / `Search index not found`), extended the widget smoke test
(full suite 201 passed), tightened checklist rows 7/8. Owner then confirmed rows 7/8 are fine. Other rows: owner said
"other tests passed" (self-reported, not independently verified).

## Explain it back
- **Why a view-model with an injected executor?** Widgets stay dumb; the state machine is plain Python so it tests without Qt. Alternative: QObject/signals view-model — needs an event loop in tests and couples logic to Qt.
- **Why one contracts file?** Presentation depends on a mirror of the result shape in one place; when RAG-002/003 land, only `contracts.py` (or an adapter) changes. Alternative: import core `AnswerResult` now — impossible, it doesn't exist yet.
- **Why a worker thread?** Gemini calls take seconds; on the GUI thread the window would freeze. The result comes back through a queued signal so widgets are only touched on the GUI thread.
- **Why does "insufficient" look different?** A refusal must never be mistaken for an answer (grounding rule); related-only citations are labelled "related, not an answer" per owner decision D2.
- **What did the mutation test prove?** That the insufficient-vs-answer branch is actually asserted, not just executed.

## Lines for the owner to add at merge
- `docs/plans/task-ledger.md`: row `GUI-001-pre | done (fake use case) | PR gui-001-pre→dev | owner exception 2026-09-26; GUI-001 still open`.
- `AI_WORKLOG.md`: "GUI-001-pre: AI built the window/view-model/fake port; 22 GUI tests; mutation on insufficient state caught by 3 tests; AI got wrong: none observed (GitNexus detect_changes gave a false 'no changes' in the worktree — noticed, not trusted)."
- `CHANGELOG.md`: "Added: desktop window against a fake use case (`--fake`), PySide6 in requirements.txt."
- master-plan / EPIC (GUI): note "GUI-001-pre done; wiring + G4 pending RAG-003".

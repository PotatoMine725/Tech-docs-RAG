# GUI-001 — Minimal PySide6 desktop app (gate G4)

Read `agents/prompts/_common.md` first and follow it. Read `docs/architecture/gui-architecture.md`.
Entry: RAG-003 done (can run in parallel with EVAL-003/004).

## Step 0 — OD-14 (ask user). Recommended extras only: arm selector (A default), latency + model line, "copy answer".

## Do
1. Window: question input (Enter to send), answer area, citations list (doc, heading path; click → shows English excerpt + source URL), clear "insufficient information" state, busy indicator, error states (quota / 503 / no index) with a readable message.
2. Gemini calls run off the UI thread (QThread / QThreadPool worker); UI never freezes.
3. MVVM: view-model holds state and calls the application "ask question" use case only — no Chroma/Gemini/parsing imports in presentation (structure test).
4. Offline view-model tests with a fake use case (no Qt event loop needed).
5. One launch command documented, e.g. `.venv/Scripts/python.exe -m knowledge_assistant.presentation.desktop.app`; add PySide6 to `requirements.txt`.
6. Manual check (user does it, you prepare the checklist) → `validation/generation/gui-check.md`: 1 EN, 1 VI, 1 insufficient case, 1 simulated error. Screenshots are welcome for the README/video.

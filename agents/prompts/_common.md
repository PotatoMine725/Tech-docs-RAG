# Common rules for every task prompt (read this first)

## Before you start
1. Read `CLAUDE.md`, `docs/plans/master-plan.md`, `docs/specs/assignment-requirements.md`, and every ADR/spec the task names.
2. Check the task's entry condition. If it is not met, STOP and report why.
3. Check `git status`. If there are uncommitted changes you did not make, list them and ask before touching them.
4. Open `docs/plans/task-ledger.md`. Every prerequisite must be `verified`; otherwise STOP. If work for this task already exists (done outside the prompt set), audit it against this prompt instead of redoing it, and record the audit in the execution report.

## While working
- MUST NOT fabricate results, scores, latency, ground truth, or "tests passed". Unverified = say "unverified".
- Offline tests by default: `.venv/Scripts/python.exe -m pytest`. Live Gemini calls only when the task says so; every live result is cached to disk so quota is never spent twice.
- Existing symbols: run GitNexus impact analysis before editing (CLAUDE.md). New files: no impact check needed.
- An open decision (OD-x in master-plan §8) that blocks the task: give 2–3 options with trade-offs and a recommendation, then ask the user (AskUserQuestion). Record the answer in an ADR or the owning spec. Never decide silently.
- Keep the layer rules (presentation → application → core ← infrastructure). `tests/unit/test_project_structure.py` must stay green.
- Small, reviewable changes. No new dependency without saying why; add it to BOTH `pyproject.toml` and `requirements.txt`.

## When done (all steps required)
1. Save this prompt verbatim to `docs/prompt-log/claude-code/<TASK-ID>.md`.
2. Execution report → `docs/reports/execution/<TASK-ID>.md`: files changed, commands run, test summary (real output), what is unverified, deviations from the prompt.
3. Append an entry to `AI_WORKLOG.md` (format is in that file): what AI did, what the AI got wrong in this task and how it was found/fixed (only real events: failing tests, user corrections, wrong assumptions; write "none observed" if none).
4. Update task/epic status and gate checkboxes in `docs/plans/master-plan.md` and the epic file, and update the task's row in `docs/plans/task-ledger.md`.
5. Run `gitnexus_detect_changes()`, then commit: `<TASK-ID>: <summary>`. Do not push unless the task says so.
6. Final chat report: files, tests, gate status, open decisions, and an **"Explain it back"** section — 3–5 bullets the user must be able to defend in an interview (why this design, what the alternative was). Save the same bullets in the execution report (section "Explain it back") before the commit, so the verifier can check them; chat alone is not enough.
7. STOP. Do not start the next task. The user will run `99-VERIFY.md` for this task in a fresh session.

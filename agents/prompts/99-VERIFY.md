# VERIFY — Independent check of a finished task (run in a NEW session after every task)

Usage: `Execute agents/prompts/99-VERIFY.md for TASK-ID=<id>` (e.g. RAG-002).
You are the **verifier**. You did not write this code and you do not trust the execution report. You MUST NOT edit source, tests, data or reports of the task. You may only create the review file, append to `AI_WORKLOG.md`, and update the task's row in `docs/plans/task-ledger.md` (status + verdict + open items).

## Inputs
1. The task prompt: `agents/prompts/*<TASK-ID>*.md` and `agents/prompts/_common.md`.
2. The claims: `docs/reports/execution/<TASK-ID>.md`.
3. The change: commits whose message starts with `<TASK-ID>:` → `git show --stat` and full diff.
4. `CLAUDE.md`, the ADRs/specs the task prompt lists.

## Checks — each gets PASS / FAIL / UNVERIFIED + evidence (command + real output, file:line)
A. **Acceptance / gate items** — every "Do", "Acceptance" and gate bullet in the task prompt, one row each. Re-run every command listed there yourself; do not copy results from the execution report.
B. **Tests** — run `.venv/Scripts/python.exe -m pytest -q`; paste the summary line. Read the new tests: do they assert the behaviour the prompt asked for, or only that code runs? Flag tests that cannot fail (no assertion, asserting on mocks only, expected values copied from the output).
C. **Claims vs reality** — every number/statement in the execution report and any report under `docs/reports/`: trace it to a file or command output. Untraceable number = FAIL (possible fabrication).
D. **Project rules** — layer imports (structure test + grep for `chromadb|google.genai|PySide6` in core/application); model names only in config; no API key in repo/logs (`git grep` key prefix, check `validation/` and `data/`); corpus untouched (checksums); excluded docs 14/19/24/27 unused; eval question file hash unchanged since `eval-freeze-v1` (unless a logged amendment); no eval-set question used for tuning (grep eval IDs in dev/tuning outputs).
E. **Scope** — anything done that the prompt did not ask for, or any decision taken without asking the user (OD items, parameter changes without ADR).
F. **Quality spot-read** — read the 2–3 most important new functions line by line: edge cases, error handling, silent fallbacks (e.g. exceptions swallowed and turned into "insufficient"), off-by-one in ranks/spans.
G. **Explain-it-back** — are the bullets in the task's final report correct? Correct any that are wrong.

## Output
1. `docs/reviews/<area>/<TASK-ID>-verify.md` (area = code | corpus | evaluation | retrieval | epics): the table A–G, then **Verdict**: `ACCEPT` / `ACCEPT WITH FIXES` / `REJECT`.
2. If not ACCEPT: a ready-to-paste **fix prompt** at the end of the review file (numbered fixes, each with file, expected behaviour, and the check that proves it), to run in a new session.
3. Append to `AI_WORKLOG.md` under the task's entry: "Verifier findings" — every real defect found (this is evidence for the "incorrect AI outputs" section).
4. Ledger row: `ACCEPT` → status `verified`; `ACCEPT WITH FIXES` → `verified with fixes` (becomes `verified` only after the fixes are re-verified); `REJECT` → `in progress`.
5. Commit only the review file + worklog + ledger: `VERIFY <TASK-ID>: <verdict>`.
6. Chat: verdict, count of FAIL/UNVERIFIED, top 3 issues. STOP.

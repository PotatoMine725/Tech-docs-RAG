# HOUSE-001 execution report

**Date:** 2026-09-24 · **Prompt:** [`agents/prompts/00-HOUSE-001-repo-hygiene-and-submission.md`](../../prompt-log/claude-code/HOUSE-001.md) · **Model:** Claude Opus 5.5 (Claude Code)

## Files changed
| File | Change |
|---|---|
| `.gitattributes` (new) | `* text=auto eol=lf`; common binary types marked `binary` |
| `CLAUDE.md` | Removed the old unmarked GitNexus block; kept the one between `<!-- gitnexus:start/end -->` |
| `AGENTS.md`, `CLAUDE.md` | GitNexus re-index refreshed the symbol counts (tool-generated line) |
| `docs/specs/assignment-requirements.md` | New `## Submission` section; status table updated (incl. experiment now decided by ADR-0003) |
| `docs/plans/master-plan.md` | §9 submission rows; EPIC-07 deliverables + G7; "Never cut" list; OD-1 wording; §10 gap rows; EPIC-02 CRLF note; Thu 24 timeline row |
| `docs/plans/epics/EPIC-07-final-qc.md` | Scope includes the submission package |
| `AI_WORKLOG.md` (new) | Tools table, log back-filled from git history and reports, QC-001 placeholders |
| `docs/prompt-log/claude-code/HOUSE-001.md` (new), `docs/prompt-log/README.md` | Prompt copy (verbatim, checked with `cmp`) and index |

## Commands run and results (real output)
- `git ls-files --eol` before: 72 files `i/lf w/crlf`, 2 `w/mixed` (`.gitignore`, `CLAUDE.md`), 64 `w/lf`. **The repository already stored LF everywhere.** In this checkout `core.autocrlf=true` hid the difference, so `git status` showed no noise here. The "~72 modified files" show up in a git client without autocrlf.
- `git add --renormalize .` → staged nothing except the real edits listed above (the index was already LF).
- Working tree rewritten to LF from the index for 62 clean files (`git checkout-index -f` after bumping mtimes, which that command otherwise skips). Not rewritten: files under `agents/`, because the owner was editing there during this task. After: 133 `w/lf`, 8 `w/crlf` (all under `agents/`), 0 mixed.
- Corpus check: all 24 accepted sources hash to `docs/snapshots/corpus/source-checksums-premigration.sha256` → **content unchanged**. **The snapshot was computed on CRLF bytes** (24/24 match as CRLF, 0/24 as LF). The sources are now LF on disk; the test rebuilds CRLF before comparing, so it passes either way.
- `scripts/utilities/build_corpus_inventory.py` re-run on the LF files: manifest and inventory byte-identical (no git change).
- `.venv/Scripts/python.exe -m pytest`: **28 passed**.
- `origin/main` (`e82c922 Initial commit`) is an ancestor of local `main`, so a later push is a fast-forward. Nothing pushed (prompt: do not push).

## Note for EPIC-02
The in-memory normalizer MUST convert `\r\n` → `\n` before computing character offsets and hashes (added to master plan EPIC-02).

## Deviations from the prompt
- **Step 6 was already done** before this task, as commit `a69a12a` with the prefix `CORPUS-001:` (the EPIC-01 task ID) instead of `EPIC-01: corpus analysis outputs`.
- **"git status is clean" is not fully met, on purpose.** The owner was writing `agents/prompts/*` (new files keep appearing, e.g. 06a/06b, 09a–c, 99-VERIFY) and changed `agents/roles/verifier.md` during the task. `_common.md` says to ask before touching changes the AI did not make, so these files are left uncommitted and unmodified for the owner.
- The 72-file noise was not visible in this checkout (see above); the fix still applies to every client.

## Unverified
- How the owner's other git client behaves with the new `.gitattributes` (expected: no EOL-only changes).
- `AI_WORKLOG.md` items marked "to confirm by user" (the other tools used, and who spotted the ADR-0004 quota issue).

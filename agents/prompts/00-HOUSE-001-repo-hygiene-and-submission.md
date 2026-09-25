# HOUSE-001 — Repo hygiene + missing submission requirements

Read `agents/prompts/_common.md` first and follow it.

## Why
The brief's **submission package** is not in the specs or the master plan, and the working tree has line-ending noise that will pollute every future diff.

## Do
1. **Line endings.** ~72 files show as modified but `git diff --ignore-all-space` shows only ~3 real changes (working tree CRLF, repo LF).
   - Add `.gitattributes` (`* text=auto eol=lf`, binaries marked `binary`), run `git add --renormalize .`, confirm the remaining diff is only real content.
   - Verify corpus files are unchanged in content: compare against `docs/snapshots/corpus/source-checksums-premigration.sha256`. Report which line ending that checksum file was computed on. If content (not just EOL) differs → STOP and report.
   - Note for EPIC-02: the in-memory normalizer MUST convert `\r\n` → `\n` before computing offsets/hashes.
2. **CLAUDE.md**: remove the duplicated GitNexus block (keep only the one between `<!-- gitnexus:start/end -->`).
3. **Submission requirements** — add a "## Submission" section to `docs/specs/assignment-requirements.md` (verbatim in substance):
   - working product / prototype / demo link; GitHub repo;
   - README covering: problem, solution, architecture/workflow, AI usage, completed work, limitations (plus dataset description);
   - demo video ≤ 5 minutes;
   - `AI_WORKLOG.md`: AI tools used, how AI helped, incorrect AI outputs, how they were improved, what would be improved with 7 more days;
   - originality (must understand/explain everything, no fake functionality); quality (small working > large not understood).
   Update the status table at the bottom of that file.
4. **Master plan**: add these to §9 traceability and to EPIC-07 deliverables/G7 (README sections, AI_WORKLOG.md, demo video + script, push to GitHub `origin`). Add them to the "Never cut" list.
5. **Create `AI_WORKLOG.md`** at repo root with sections:
   - `## Tools used` (table: tool, model/version, used for)
   - `## Log` — one entry per task: `### <date> <TASK-ID>` → *AI did* / *AI got wrong* / *How found* / *Fix* / *Human decision*
   - `## Summary: how AI helped` (filled at QC-001)
   - `## Incorrect AI outputs and improvements` (filled at QC-001 from the log)
   - `## With 7 more days` (filled at QC-001)
   Back-fill the log ONLY from verifiable history: git log, `docs/prompt-log/`, `docs/reports/`, ADR amendments (e.g. ADR-0004 D11/D12 amended; NVIDIA NIM ruled out). Mark anything you cannot verify as "to confirm by user".
6. Commit the EPIC-01 outputs that are still untracked (manifest, section inventory, topic map, EPIC-01 report, `markdown_structure.py`, tests, root README draft) as a separate commit `EPIC-01: corpus analysis outputs` before the HOUSE-001 commit.

## Do not
Edit corpus content, write code for the pipeline, or push.

## Done when
`git status` is clean; `git diff HEAD~2 --stat` shows no EOL-only churn in `corpus/`; pytest green; AI_WORKLOG.md exists; §9 lists every submission item.

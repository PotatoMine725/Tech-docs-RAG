# VERIFY HOUSE-001

Verifier session, 2026-09-24. Reviewed commits `916b5bc` (main work) and `cdcdc67` (worklog follow-up) against `agents/prompts/00-HOUSE-001-repo-hygiene-and-submission.md`. Commands were re-run by the verifier; nothing was copied from the execution report.

## A. Acceptance / gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| A1 | `.gitattributes` with `* text=auto eol=lf`, binaries marked | PASS | `.gitattributes` lines 1-19 |
| A2 | Renormalize; remaining diff = real content only | PASS | `git ls-files --eol`: 164 `i/lf w/lf`, 8 `i/lf w/crlf`, 0 `i/crlf`, 0 mixed. `git grep -lI $'\r' HEAD~2` returns nothing, so no CR is stored in the repo. |
| A3 | Corpus content unchanged vs `source-checksums-premigration.sha256`; say which EOL the checksum used | PASS | Rebuilt CRLF from the LF files: 24/24 sources and 4/4 `corpus/excluded/` match the snapshot. Report's "computed on CRLF" is confirmed. Its "0/24 as LF" was not re-run (UNVERIFIED, low risk). |
| A4 | No EOL-only churn in `corpus/` | PASS | `git diff 916b5bc~1 916b5bc --stat -- corpus` is empty; all 31 corpus files are `i/lf w/lf`. |
| A5 | Note for EPIC-02: normalizer converts `\r\n`→`\n` before offsets/hashes | PASS | `master-plan.md` EPIC-02 deliverables, diff of `916b5bc` |
| A6 | `CLAUDE.md`: only the block between `gitnexus:start/end` remains | PASS | `CLAUDE.md:19` start, `:61` end, one block. |
| A7 | `## Submission` section in `assignment-requirements.md` with all 6 items + status table updated | PASS | Diff of `916b5bc`: demo/repo, README sections, video ≤ 5 min, AI_WORKLOG contents, originality, quality; 5 new status rows. |
| A8 | Master plan: §9 rows, EPIC-07 deliverables + G7, "Never cut" | PASS | Diff of `916b5bc` (6 §9 rows, 4 EPIC-07 bullets, 2 G7 boxes, "Never cut" extended). |
| A9 | `AI_WORKLOG.md` with the 5 required sections, back-filled only from verifiable history | PASS | All 5 headings present. Spot-checked: trailers Sonnet 5 on `3d5a606`, Opus 5.5 on `490068f`..`916b5bc` (git log); "300 vs 800" in the SETUP-001 EPIC-06 stub (`git show 3d5a606:docs/plans/epics/EPIC-06-experiment.md`). |
| A10 | EPIC-01 outputs committed separately before HOUSE-001 | PASS (deviation disclosed) | `a69a12a` "CORPUS-001: ..." instead of "EPIC-01: corpus analysis outputs". Same content, different prefix. |
| A11 | Done when: `git status` clean | PARTIAL | Not clean at the time (owner's `agents/` edits, disclosed). Now only `AGENTS.md`/`CLAUDE.md` show as modified (GitNexus symbol-count refresh), unrelated to HOUSE-001. |
| A12 | Done when: pytest green | PASS | See B. |
| A13 | Do not: edit corpus, write pipeline code, push | PASS | No corpus diff; only tests/docs touched; `origin/main` not advanced by the task. |

## B. Tests
`.venv/Scripts/python.exe -m pytest -q` → `45 passed in 2.21s` (includes later EVAL-001 tests; the report's "28 passed" belongs to the HOUSE-001 commit and was not re-run at that commit).
HOUSE-001 added no tests. `tests/unit/test_corpus_inventory.py:65` rebuilds CRLF before comparing, so it passes with either working-tree EOL. It therefore cannot detect an EOL regression, and nothing tests that `.gitattributes` or `AI_WORKLOG.md` exists. Acceptable for a hygiene task, but noted.

## C. Claims vs reality
| Claim | Result |
|---|---|
| Repo already stored LF everywhere | PASS (no CR in `HEAD~2` blobs) |
| 24/24 sources match the CRLF snapshot | PASS |
| Working tree after: 133 w/lf, 8 w/crlf under `agents/`, 0 mixed | PASS in kind (now 164/8/0 because later tasks added files; the 8 CRLF files are the same `agents/` set) |
| Before: 72 `i/lf w/crlf`, 2 mixed | UNVERIFIED: the pre-task working tree no longer exists |
| `core.autocrlf=true` hid the noise in this checkout | PASS (`git config core.autocrlf` → `true`) |
| Manifest/inventory byte-identical after re-run | UNVERIFIED (not re-run) |
| `origin/main` is an ancestor of local `main` | not re-run; low risk, nothing depends on it |
| Worklog "first two attempts silently did nothing" | UNVERIFIED (session events, no artifact) |
| Worklog "owner said these items may be removed" (`cdcdc67`) | UNVERIFIED (user statement; consistent with the removals) |
No untraceable numeric claim was found.

## D. Project rules
- Layers: `grep` for `chromadb|google.genai|PySide6` in `src` matches only `presentation/desktop/app.py` → PASS. Structure test is in the 45 passing.
- Model names / keys: `git grep -E "AIza[0-9A-Za-z_-]{30}"` → no hits; `.env` is git-ignored and untracked → PASS.
- Corpus untouched, excluded docs 14/19/24/27 unused: PASS (A3, A4; no code reads them).
- Eval freeze / tuning leakage: N/A (`eval-freeze-v1` does not exist yet; EVAL-002 is later).

## E. Scope
Beyond the prompt, in `916b5bc`: rewording of OD-1, three rows in master-plan §10, a Thu 24 Sep timeline row, an "experiment approach decided (ADR-0003 D7)" status update, GitNexus count refresh in `AGENTS.md`/`CLAUDE.md`. All are small, consistent with the task, and disclosed in the report except the timeline row and §10 rows are only in the file list. No decision was taken silently: OD-1 was narrowed, not decided. `cdcdc67` (worklog cleanup) came after the task on the owner's word (UNVERIFIED, see C); it is a docs-only change.

## F. Quality spot-read
No functions were added. Read instead: `.gitattributes` (correct precedence: `eol=lf` overrides autocrlf; binary list omits nothing the repo currently contains) and the Submission section (matches the six items in the prompt, no invented requirements; it states it comes from "the owner's record of the brief", which is honest). One wording issue: the `916b5bc` commit message says "the working tree is now LF too" while 8 `agents/` files are still CRLF; the same message says `agents/` was left untouched, so it is not misleading.

## G. Explain-it-back
The execution report itself had no "Explain it back" section (it belongs to the final chat report, which the verifier cannot see). The report's stated facts are correct, with two exceptions of wording only: "git status is clean" is listed as unmet on purpose (true then, resolved now), and "28 passed" is historical.

## Verdict
**ACCEPT.** 0 FAIL, 4 UNVERIFIED (all historical session claims, none load-bearing), 1 PARTIAL (A11, disclosed by the author). No fix prompt needed.

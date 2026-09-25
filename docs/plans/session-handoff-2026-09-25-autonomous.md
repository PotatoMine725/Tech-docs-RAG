# Session handoff — 2026-09-25 (autonomous run, owner away)

Point-in-time note. The owner authorized this session to run the next prompts, verify, and manage git/PRs, and to decide alone when blocked, writing the decisions here. Task status is in [task-ledger.md](task-ledger.md).

## 🚩 For the owner — review these first
1. **You are the only blocker now.** Fill every `owner verdict:` line in [EVAL-001-owner-recheck.md](../reviews/evaluation/EVAL-001-owner-recheck.md) (8 case blocks + the 18-case table line). EVAL-001 and REORIENT-001 are now `verified`, so this is the last entry condition of EVAL-002 (→ M1 → RAG-001a). The AI did not fill them (a human step).
2. **AI decisions to confirm or overrule** (INGEST-003, all recorded in the docs):
   - **OD-6:** one shared `MarkItDownParser` for `.pdf .html .htm .docx .txt`; the `pdf_parser.py` / `html_parser.py` stubs were deleted. Overruling means restoring per-format wrapper files (no behaviour change).
   - **Converted files skip the ADR-0003 D1 normalizer.** D1 needs the web-export page frame and raises on PDF/DOCX. Recorded as an amendment line under ADR-0002 D1, "pending owner review".
   - **Per-format MarkItDown converters instead of the `MarkItDown` front end.** The front end guesses the format from the content and returned broken files as plain text.
   - **Dependency** `markitdown[pdf,docx]>=0.1.8,<0.2` added to `pyproject.toml` and `requirements.txt`. Its `onnxruntime` need is already required by `chromadb`, so the app gets no new ML runtime.
3. **Your Windows venv:** run `.venv\Scripts\pip install -r requirements.txt`. Until you do, the new MarkItDown tests fail with `ModuleNotFoundError`. V-2 (MarkItDown on Python 3.13) was checked on Linux 3.13.12, not on your 3.13.3.
4. **PR to `dev`:** see "Git" below. It is not merged into `main` (your call, CLAUDE.md rule 11).
5. **Optional reviewer notes** (non-blocking, from the verifiers): EVAL-001 case 022 has no test guarding its two slots; the re-check sheet does not ask about splitting case 017's slot; 19 heading-only Arm A chunks (INGEST-002, needs an ADR-0003 amendment to change).

## What ran
| Step | Result |
|---|---|
| INGEST-002 verify (other session) | Already finished at start: ACCEPT, merged into `dev` (PR #4). G2 passed. |
| EVAL-001 re-verify (sub-agent, fresh context) | [EVAL-001-reverify](../reviews/evaluation/EVAL-001-reverify.md) → **ACCEPT** (0 FAIL, 3 UNVERIFIED that cannot be checked after the fact). Ledger → `verified`. |
| INGEST-003 (this session) | MarkItDown adapter, V-2, OD-6. [Report](../reports/execution/INGEST-003.md). Run because the project is not behind schedule, so OD-15 (cut) did not apply. |
| INGEST-003 verify (sub-agent) | [INGEST-003-verify](../reviews/code/INGEST-003-verify.md) → **ACCEPT WITH FIXES** (3 FAIL: silent drop of empty conversions, incomplete signature check, non-hermetic lazy-import test). |
| INGEST-003 fixes (this session) | All 6 fixes applied, each proven by a mutation; 113 tests pass (Python 3.13 and 3.11); corpus outputs byte-identical; G2 11/11. |
| INGEST-003 re-verify (sub-agent) | _see Git / ledger row 05_ |

Not run, and why:
- **EVAL-002** is blocked by item 1 above.
- **RAG-001a and later** need M1 (EVAL-002). Indexing before the ground truth is frozen is on the never-cut list.
- `/compact` was not run: slash commands are not available to the agent in this environment.

## Git
- Work branch: `claude/workflows-ingest-002-review-svn2dq` (from `dev` `443582a`), pushed. It contains the EVAL-001 re-verify, INGEST-003, its verify, its fixes and the re-verify.
- Local-only helpers (git-excluded, not committed): `.venv313/` (Python 3.13 venv), `.gitnexus/`.

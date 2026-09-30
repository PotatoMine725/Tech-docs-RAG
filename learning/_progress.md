# DISTILL-001 progress

Pinned commit: 762b754ecb6c8aae21e005246649252c8bfd0762 (tag v1.0-submission)
Worktree: .claude/worktrees/learning · branch learning/distill · no commits yet (owner approval required)

## Phases
- [x] Phase 0 — worktree + progress file
- [x] Phase 1 — inventory (`_inventory.md`, draft; source bodies partly read)
- [x] Phase 2 — discovery pass (imports, idioms, incidents, seed list; term sweep still partial)
- [x] Phase 3 — outline approved by the owner (2026-09-29): core first, Anki deferred, plus the Python code-reading guide (01b)
- [x] Phase 4 — writing DONE for all files except `anki-cards.tsv` (deferred by the owner): 00, 01, 01b, 02–16, glossary, interview-bank
- [x] Phase 5 — self-verification: check_refs 0 problems (20 files), structure check (levels/exercises/self-check/interview/further reading/pin), key-pattern grep clean, test suite re-run once (866 passed), stale refs fixed
- [ ] Phase 6 — final report (pending advisor + chat report; **commit only after the owner says so**)

## Files (Phase 4, after approval)
00-README · 01 · 01b · 02–16 · glossary · interview-bank — written; anki-cards.tsv — deferred (owner)


## Batch log
- Batch 1 (core, owner-approved 2026-09-29 17:05): DONE — 00-README (interim), 01, 01b (added: Python code-reading guide, owner request), 03, 05, 06, 07, 09. check_refs.py: 0 problems (snippets verbatim + line refs in range).
- Tools: `_tools/expand_snippets.py` (drafts in `_src/*.md` -> final files), `_tools/check_refs.py`, `_tools/exercises/llm_retry_scenarios.py`.
- Deviations from the approved outline: added `01b`; `02-python-tooling` deferred (not in core list); anki skipped (owner).
- Pending: 02, 04, 08, 10, 11, 12, 13, 14, 15, 16, glossary, interview-bank; Phase 5 full verification (re-run tests count, re-check numbers); Phase 6 report.
- Batch 2 (owner said 'continue on the rest documents', 2026-09-30): DONE so far — 08, 10, 11, 12, 13 (check_refs: 0 problems, 13 files). New offline scripts: `_tools/exercises/{generation,eval_metrics,judge_stats}_scenarios.py`.
- Batch 2 (rest): DONE — 02, 04, 14, 15, 16, glossary, interview-bank, full 00-README; stale refs fixed; pytest re-run once (866 passed); advisor review applied (file 12 §2.3 latency reason, README hour total and mutation wording, home note in 04 §2.4).
- Full offline suite run once (2026-09-30, worktree, `-p no:cacheprovider`, PYTHONDONTWRITEBYTECODE=1, OPENBLAS_NUM_THREADS=1): `866 passed, 1 deselected in 13.27s`, exit 0 — matches the README claim at the pin. Output kept in scratchpad, not in repo.

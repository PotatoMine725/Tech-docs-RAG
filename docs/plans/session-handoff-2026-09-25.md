# Session handoff — 2026-09-25

Point-in-time note for the next Claude Code session. Task status is in [task-ledger.md](task-ledger.md); this note only says where to pick up.

## State at handoff
- `dev` = `5667e14` (PR #1 merged). [PR #2](https://github.com/PotatoMine725/Tech-docs-RAG/pull/2) `dev` → `main` is open (owner's release; no CI failures, no conflicts).
- Tests: 63 passed (`.venv/bin/python -m pytest -q` on Linux; `.venv/Scripts/python.exe -m pytest` on Windows).

| Task | Status | Evidence |
|---|---|---|
| 00R REORIENT-001 | verified | fixes `47b9c4e`; [re-verify](../reviews/code/REORIENT-001-reverify.md) → ACCEPT |
| 03 INGEST-001 | verified | `1858e27`, fixes `98fdb5a`; [re-verify](../reviews/code/INGEST-001-reverify.md) → ACCEPT; output `data/processed/documents/normalized.jsonl` (sha256 `a6db2f26…9ae95`) |
| 01 EVAL-001 | verified with fixes | re-verify still needed (covers `629b931` + `831d5a0`) |
| 02 EVAL-002 | blocked | owner verdicts + EVAL-001 re-verify (REORIENT-001 prerequisite now met) |
| 04 INGEST-002 | **ready** | needs 03 = verified ✔ |
| 05 INGEST-003 | ready (cuttable, OD-15) | needs 03 = verified ✔ |

## Open owner decisions (ask before building on them)
- ~~Footer removal~~ and ~~known residue~~: decided by the owner 2026-09-25 (keep footer removed, keep residue). Recorded in `ingestion-spec.md` and the ledger.
1. **EVAL-001 owner re-check** — fill every `owner verdict:` line in [EVAL-001-owner-recheck.md](../reviews/evaluation/EVAL-001-owner-recheck.md) (8 case blocks + 1 line for the 18-case table).

## Next prompts, in order
1. Owner: fill the EVAL-001 re-check verdicts (decision 1 above).
2. `Execute agents/prompts/99-VERIFY.md for TASK-ID=EVAL-001` (fresh session; re-verify covering `629b931` and `831d5a0`).
3. `Execute agents/prompts/04-INGEST-002-chunkers-and-stats.md` (can start now; parallel with steps 1–2). Then `99-VERIFY` for INGEST-002 → G2 (the Arm A half of the heading-path gate item is still open).
4. After 1 + 2: `Execute agents/prompts/02-EVAL-002-write-and-freeze.md` → tag `eval-freeze-v1` (M1).
5. Optional: `05-INGEST-003` (MarkItDown, cuttable).
6. Then `06a-RAG-001a` (needs M1 + INGEST-002 verified).

## Practical notes for a cloud (Linux) session
- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/pip install -e .`
- GitNexus MCP tools may be missing; the CLI works: `npx -y gitnexus analyze`, `npx -y gitnexus impact <Symbol> --direction upstream`, `npx -y gitnexus detect-changes -s compare -b <base-commit>`. Add `.gitnexus/` to `.git/info/exclude`. `analyze` rewrites the counts in `CLAUDE.md`/`AGENTS.md` and creates `.claude/skills/gitnexus-*`: revert/delete those before committing.
- `detect-changes` with the default scope ignores new untracked files; use `-s compare -b <base>` for the claim in commit messages and reports (INGEST-001 verify finding).
- Mutation checks: `git checkout` does not restore an untracked file; back it up first (INGEST-001 worklog).
- Branches (CLAUDE.md rule 11): work on a branch from `dev`, PR into `dev`; `main` only by the owner.

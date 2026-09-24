# Task prompts for Claude Code (run in order)

Each file = one Claude Code session. Paste: `Execute agents/prompts/<file>.`
Every prompt reads `_common.md` first (shared rules + end-of-task steps: prompt-log, execution report, AI_WORKLOG entry, commit, "Explain it back", STOP).
**After every task:** open a NEW session and run `Execute agents/prompts/99-VERIFY.md for TASK-ID=<id>`. Only start the next task when the verdict is ACCEPT (or the fixes are done and re-verified).

| # | Task | Target date | Needs | Gemini quota | Output / gate |
|---|---|---|---|---|---|
| 00 | HOUSE-001 repo hygiene + submission reqs | Thu 24 | — | none | clean git, AI_WORKLOG.md |
| 01 | EVAL-001 design dataset | Thu 24–Fri 25 | 00 | none | blueprints, OD-4/5 |
| 02 | EVAL-002 write + freeze | Fri 25 | 01 + **your review** | none | tag `eval-freeze-v1` (M1) |
| 03 | INGEST-001 models, parser, normalize | Fri 25 | 00 (parallel with 01/02) | none | normalized.jsonl |
| 04 | INGEST-002 chunkers + stats | Sat 26 | 03 | none | G2 |
| 05 | INGEST-003 MarkItDown (cuttable) | Sat 26 | 03 | none | — |
| 06a | RAG-001a embedder + cache + ADR-0005 | Sat 26 | **M1** + 04 | probe only | V-1 answered |
| 06b | RAG-001b Chroma + index both arms | Sat 26–Sun 27 | 06a | **embeddings** | collections = chunks |
| 07 | RAG-002 retrieval, generation, citation | Sun 27 | 06b | dev set only | prompt v1, threshold |
| 08 | RAG-003 retry/fallback, CLI, smoke | Sun 27 | 07 | light | G3 / M2 |
| 09a | EVAL-003a runner | Mon 28 | 08 | dev dry run | resumable records |
| 09b | EVAL-003b metrics + judge | Mon 28 | 09a | 1 call | metric defs tested |
| 09c | EVAL-003c tables + spot-check tools | Mon 28 | 09b | none | generated reports |
| 10 | GUI-001 desktop app | Mon 28 | 08 (parallel) | light | G4 |
| 11 | EVAL-004 run + report | Mon 28–Tue 29 | 09c | **heavy** | G5B |
| 12 | EXP-001 experiment + failure analysis | Tue 29 | 11 | none | G6 |
| 13 | BONUS-001 hybrid / query rewrite (optional) | Tue 29–Wed 30 | 12 | light | — |
| 14 | QC-001 README, worklog, checks, push, video script | Wed 30 | 12 | none | G7 |
| 99 | VERIFY (after every task) | — | the task | none | review + verdict |
| — | Record video, submit | Wed 30–**Thu 1 Oct** | 14 | — | 🔴 deadline |

Human-only steps: answer OD questions, review ground truth (02), fill the judge spot-check (11), manual GUI check (10), confirm "7 more days" (14), record the video.

## Suggested CLI usage (PowerShell, repo root)
- Interactive (default for all tasks): `claude` → `Execute agents/prompts/<file>.` → review → `/clear`.
- Plan first for big tasks (06a, 06b, 07, 09a, 09b, 12): `claude --permission-mode plan`.
- VERIFY can run headless, read-only:
  `claude -p "Execute agents/prompts/99-VERIFY.md for TASK-ID=RAG-002" --allowedTools "Read" "Grep" "Glob" "Bash(.venv/Scripts/python.exe -m pytest:*)" "Bash(git:*)" "Write(docs/reviews/**)" "Edit(AI_WORKLOG.md)"`

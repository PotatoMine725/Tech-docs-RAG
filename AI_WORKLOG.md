# AI worklog

A record of how AI tools were used in this project, required by the submission (`docs/specs/assignment-requirements.md` § Submission). The log is honest. Mistakes are recorded when they were real: a failing test, a user correction, or a wrong assumption. Anything that cannot be checked from the repository is marked **to confirm by user**.

## Tools used

| Tool | Model / version | Used for |
|---|---|---|
| Claude Code (CLI) | Claude Sonnet 5 (commit `3d5a606`, co-author trailer) | SETUP-001: project skeleton, specs, corpus migration |
| Claude Code (CLI) | Claude Opus 5.5 (`claude-opus-5-5`; commits `490068f` onward) | ADR drafting, master plan, corpus analysis, repo hygiene, evaluation design |
| GitNexus (`npx gitnexus`) | local code index | Impact analysis before edits, change detection before commits |
| Other agent for the chunking consultation (`docs/plans/chunking-consultation-handoff.md`) | to confirm by user | Advice on chunking strategy before ADR-0003 |
| Tool that wrote `agents/prompts/*.md` | to confirm by user | Task prompts 00–14 |
| Google Gemini API | not used yet (planned: `gemini-embedding-001`, `gemini-3.5-flash-lite`, `gemini-3.5-flash`, ADR-0004) | Embeddings, answers, LLM judge (from EPIC-03) |

## Log

Format per entry: *AI did* / *AI got wrong* / *How found* / *Fix* / *Human decision*.

### 2026-09-24 SETUP-001 (commit `3d5a606`)
- *AI did:* layered project skeleton, specs, ADR-0001, 9 offline tests, corpus moved into `corpus/sources` and `corpus/excluded` with SHA-256 before/after ([report](docs/reports/execution/SETUP-001-project-structure.md)).
- *AI got wrong:* (1) The old, unmarked GitNexus block was kept in `CLAUDE.md` while `gitnexus analyze` maintains its own marked block, so `CLAUDE.md` ended up with two GitNexus blocks with different counts. (2) The EPIC-06 stub proposed "300 vs 800" chunk sizes, which later conflicted with ADR-0003 D7.
- *How found:* (1) the owner's HOUSE-001 prompt; (2) the master-plan review (`278e14e`).
- *Fix:* (1) duplicate block removed in HOUSE-001; (2) EPIC-06 aligned to D7 in `278e14e`.
- *Human decision:* #25 never existed (skipped during conversion), so the counts are 28 original, 24 accepted and 4 excluded. Build at repo root.

### 2026-09-24 ADR-0003 / ADR-0004 (commits `490068f`, `6f9e1d5`)
- *AI did:* drafted the chunking ADR (D1–D9) from corpus measurements and the consultation handoff, and the model-selection ADR (D10–D13); aligned `CLAUDE.md` and the specs.
- *AI got wrong:* (1) The first D11 choice (`gemini-3.5-flash` as answer model, 20 requests/day) did not fit the evaluation budget (about 120+ answer calls per full run, so 6+ days per run). (2) ADR-0003 says 498 H1–H3 sections remain after removing repeats; the reproducible EPIC-01 inventory finds 450 (other figures match). The measurement code was not saved.
- *How found:* (1) quota arithmetic recorded in ADR-0004 "Resolved issue" (who spotted it: to confirm by user); (2) EPIC-01 recomputation.
- *Fix:* (1) D11/D12 amended: Flash-Lite answers and judges, Flash is the fallback; (2) recorded as unexplained in the [EPIC-01 report](docs/reports/epics/EPIC-01-corpus-analysis.md); no decision depends on it.
- *Human decision:* accepted D1–D13; chose to support English and Vietnamese questions (D9). Other providers considered and ruled out (e.g. NVIDIA NIM): to confirm by user, since the repository does not record this.

### 2026-09-24 Master plan (commits `278e14e`, `128cd72`)
- *AI did:* master plan with phases, dependencies, exit gates, quota plan, cut line and open decisions; epic stubs.
- *AI got wrong:* (1) The plan first gave EVAL-001 the whole job of writing questions and ground truth, but the owner's EVAL-001 prompt is design only. (2) The repo-structure table said "EVAL-001 prompt file is empty" while the same commit added the 17.7K prompt (possibly written after the plan was drafted: to confirm by user).
- *How found:* the AI reading the EVAL-001 prompt after the first commit.
- *Fix:* `128cd72` split stage A into EVAL-001 (design) and EVAL-002 (write + freeze) and removed the stale row.
- *Human decision:* everything is due 2026-10-01.

### 2026-09-24 CORPUS-001 / EPIC-01 (commit `a69a12a`)
- *AI did:* corpus manifest, 636-section inventory, shared heading rules (`markdown_structure.py`), topic map, README dataset section, 19 offline tests.
- *AI got wrong:* none observed in the committed output. One open difference is logged under ADR-0003 above.
- *How found:* n/a.
- *Fix:* n/a.
- *Human decision:* manifest at `corpus/manifest.json` (OD-2). Excluded docs 14, 19, 24, 27 are index pages with no useful content (OD-3). The owner suggested cleaning page boilerplate from the source files with a subagent; not done, because the rules forbid editing sources (cleanup is in-memory, ADR-0003 D1).

### 2026-09-24 HOUSE-001
- *AI did:* `.gitattributes` (LF everywhere), checked that the corpus content is unchanged, removed the duplicate GitNexus block, added the submission requirements to the specs and master plan, created this worklog.
- *AI got wrong:* none observed.
- *How found:* n/a.
- *Fix:* n/a.
- *Human decision:* run HOUSE-001 before EVAL-001.

## Summary: how AI helped

To be filled at QC-001.

## Incorrect AI outputs and improvements

To be filled at QC-001, from the log above.

## With 7 more days

To be filled at QC-001.

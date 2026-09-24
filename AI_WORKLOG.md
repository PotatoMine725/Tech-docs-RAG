# AI worklog

A record of how AI tools were used in this project, required by the submission (`docs/specs/assignment-requirements.md` § Submission). The log is honest. Mistakes are recorded when they were real: a failing test, a user correction, or a wrong assumption. Only facts recorded in the repository (commits, prompts, reports, ADRs) or stated by the owner are logged; anything else is left out rather than guessed.

## Tools used

| Tool | Model / version | Used for |
|---|---|---|
| Claude Code (CLI) | Claude Sonnet 5 (commit `3d5a606`, co-author trailer) | SETUP-001: project skeleton, specs, corpus migration |
| Claude Code (CLI) | Claude Opus 5.5 (`claude-opus-5-5`; commits `490068f` onward) | ADR drafting, master plan, corpus analysis, repo hygiene, evaluation design |
| GitNexus (`npx gitnexus`) | local code index | Impact analysis before edits, change detection before commits |
| Chunking consultation (`docs/plans/chunking-consultation-handoff.md`, cited as context by ADR-0003) | — | A handoff written by Claude Code so another agent could advise on chunking before ADR-0003 |
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
- *How found:* (1) quota arithmetic recorded in ADR-0004 "Resolved issue"; (2) EPIC-01 recomputation.
- *Fix:* (1) D11/D12 amended: Flash-Lite answers and judges, Flash is the fallback; (2) recorded as unexplained in the [EPIC-01 report](docs/reports/epics/EPIC-01-corpus-analysis.md); no decision depends on it.
- *Human decision:* accepted D1–D13; chose to support English and Vietnamese questions (D9). NVIDIA NIM was considered and ruled out (stated in the owner's HOUSE-001 prompt, `docs/prompt-log/claude-code/HOUSE-001.md`).

### 2026-09-24 Master plan (commits `278e14e`, `128cd72`)
- *AI did:* master plan with phases, dependencies, exit gates, quota plan, cut line and open decisions; epic stubs.
- *AI got wrong:* (1) The plan first gave EVAL-001 the whole job of writing questions and ground truth, but the owner's EVAL-001 prompt is design only. (2) The repo-structure table said "EVAL-001 prompt file is empty" while the same commit added the 17.7K prompt.
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
- *AI got wrong:* the first two attempts to rewrite the working tree with LF silently did nothing. The first split file paths on spaces, and non-ASCII names such as the `—` in the EVAL-001 prompt file got quoted. The second ran `git checkout-index -f`, which skips files whose timestamps match the index.
- *How found:* re-checking `git ls-files --eol` after each attempt (the counts had not changed).
- *Fix:* NUL-separated paths (`-z`) in Python, and file times bumped before the checkout. Verified 0 CRLF files outside `agents/`, and the corpus hashes unchanged.
- *Human decision:* run HOUSE-001 before EVAL-001.
- *Verifier findings (99-VERIFY, [review](docs/reviews/code/HOUSE-001-verify.md)):* verdict ACCEPT. No incorrect output found: the corpus checksums, LF storage, CLAUDE.md single block and Submission items were all reproduced. Minor gaps only: the "72 files w/crlf" starting state and the "first two attempts did nothing" story cannot be re-checked; the "git status clean" done-criterion was not met at commit time (owner's `agents/` edits, disclosed); no test guards `.gitattributes` or catches an EOL regression.

### 2026-09-24 EVAL-001
- *AI did:* evaluation dataset design: 36 evaluation + 6 dev blueprints with verbatim evidence quotes, absence proofs for the "not in the documents" cases, a generated coverage matrix, the design document, and 13 offline tests ([report](docs/reports/execution/EVAL-001.md)).
- *AI got wrong:* (1) The design draft said the hub pages #05/#08 were read completely and "made of links"; only part of #08 had been read and #05 not at all. (2) It said huge documents are the expected source in 25% of cases, ignoring one cross-document case (actually 8 only-source + 1 shared). (3) The master plan (written earlier by the AI) said EVAL-001 decides the rubric, but the owner's prompt says to only propose metrics. (4) Five evidence quotes were trimmed (to avoid link markup) so far that they no longer contained the fact they were meant to prove, e.g. the ValidationProblemDetails quote without the word ValidationProblemDetails; the verbatim-quote test could not catch that.
- *How found:* (1)(2) the AI's own check of every claim against the data before committing; (3) reading the prompt; (4) a second AI review of the finished work.
- *Fix:* (1) measured the link share (#08: 48 of 50 content lines are links; #09: 13 of 15; #05 links + captions) and rewrote the text to say exactly what was read; (2) corrected the figure; (3) followed the prompt and fixed the plan wording. (4) full-sentence quotes, 17 added quotes, and a `supports` link from every quote to answer points, with a test that fails if a required point has no quote.
- *Human decision:* order HOUSE-001 → EVAL-001; OD-4 = 32 answerable + 4 insufficient, 18/18, 7 parallel groups, 6 dev; OD-5 = 6 labels + points-covered score.

### 2026-09-24 EVAL-001 independent blueprint review (commits `9e0ab15`, `ce04909`)
- *AI did:* after the owner's own review, a separate Claude Code agent (fresh context, read-only) checked all 42 blueprints against the corpus ([review + response](docs/reviews/evaluation/EVAL-001-blueprint-review.md)). The authoring session verified every finding against the corpus, then fixed them.
- *AI got wrong:*
  - (1) Case 023 claimed that only variant 1 of #13 "IExceptionHandler" states the .NET 10 diagnostics change, and marked citations of variants 2–3 as wrong evidence. All 3 variants state it, in different words. The same claim was in the evidence map and the design doc.
  - (2) 32 prose values in `blueprint.yaml` were silently cut off: in YAML, " #" starts a comment, so "The introduction of #22 (…)" was read as "The introduction of". One variation (`{ "shadowCopy": false }`) was read as a mapping. The tests only checked quotes, headings and counts, so they passed.
  - (3) The other 23 review findings:
    - missing alternate sources in 11 cases;
    - required points that go beyond the planned question or the corpus wording (009/010, 016, 022, 024, 025, 031);
    - a `must_not_claim` in 036 that would punish a correct remark about `Mock<T>`/`.Setup(`, which #03 does show;
    - a question plan in 030 that let one document answer a cross-document case;
    - a parent-section alternate in 018 with none of the answer;
    - smaller label and wording fixes.
- *How found:* (1)(3) the independent review; (2) the authoring session while checking the review's findings against the YAML.
- *Fix:* all 24 findings addressed (23 accepted, 1 partly accepted: 023 keeps `mixed_version`, because the answer still depends on the version). A new `stands_in_for` field lets an alternate count in cross-document cases. Three new tests: no inline YAML comments and prose fields are strings (both failed before the YAML fix), and cross-document alternates name the source they replace (written after the field existed; shown to fail with the field removed). 45 tests pass.
- *Human decision:* the owner reviewed the blueprints and asked for an independent agent review. No case was added, dropped or re-scoped, so the OD-4 mix is unchanged.

## Summary: how AI helped

To be filled at QC-001.

## Incorrect AI outputs and improvements

To be filled at QC-001, from the log above.

## With 7 more days

To be filled at QC-001.

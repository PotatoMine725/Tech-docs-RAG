# AI worklog

A record of how AI tools were used in this project, required by the submission (`docs/specs/assignment-requirements.md` § Submission). The log is honest. Mistakes are recorded when they were real: a failing test, a user correction, or a wrong assumption. Only facts recorded in the repository (commits, prompts, reports, ADRs) or stated by the owner are logged; anything else is left out rather than guessed.

## Tools used

| Tool | Model / version | Used for |
|---|---|---|
| Claude Code (CLI) | Claude Sonnet 5 (commit `3d5a606`, co-author trailer) | SETUP-001: project skeleton, specs, corpus migration |
| Claude Code (CLI) | Claude Opus 5.5 (`claude-opus-5-5`; commits `490068f` onward) | ADR drafting, master plan, corpus analysis, repo hygiene, evaluation design |
| Claude Code (CLI) | Claude Sonnet 5 (`claude-sonnet-5`; RAG-003 commits, co-author trailer) | RAG-003: retry/fallback adapter, error classification, CLI, smoke checks |
| GitNexus (`npx gitnexus`) | local code index | Impact analysis before edits, change detection before commits |
| Chunking consultation (`docs/plans/chunking-consultation-handoff.md`, cited as context by ADR-0003) | — | A handoff written by Claude Code so another agent could advise on chunking before ADR-0003 |
| Google Gemini API | `gemini-embedding-001` (from RAG-001a, 2026-09-26); `gemini-3.5-flash-lite` (answers, from RAG-002, 2026-09-26); `gemini-3.5-flash` fallback (RAG-003 smoke check: 1 direct call; ADR-0004) | Embeddings, answers (2 dev answers in RAG-002, 3 in the RAG-003 smoke checks), LLM judge (from EPIC-05) |

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
- *Fix:* all 24 findings addressed (22 accepted; 1 partly accepted: 023 keeps `mixed_version`, because the answer still depends on the version; 1 decided by the author: the DEV-006 scoring rule, since confirmed by the owner as D2). A new `stands_in_for` field let an alternate count in cross-document cases (replaced by `slot` after owner decision D1). Three new tests: no inline YAML comments and prose fields are strings (both failed before the YAML fix), and cross-document alternates name the source they replace (written after the field existed; shown to fail with the field removed). 45 tests pass.
- *Human decision:* the owner reviewed the blueprints and asked for an independent agent review. No case was added, dropped or re-scoped, so the OD-4 mix is unchanged. After asking for a plain explanation and consulting, the owner decided (2026-09-24):
  - D1: evidence slots, all slots needed, any source within a slot. 031's citation accepts #20 for the #26 slot.
  - D2: a refusal may mention related content if it says the topic isn't covered and doesn't present that content as the answer. RAG-002 must keep `missing_information` and optional related citations when an answer is insufficient; EVAL-003b must judge, not auto-label, unanswerable cases the system answered.
  - D3: 030 stays cross-document (question wording changed, not the scope).
- *Verifier findings (99-VERIFY, [review](docs/reviews/evaluation/EVAL-001-verify.md)):* verdict ACCEPT WITH FIXES. The ground truth reproduces: all 107 evidence quotes are in their named sections, the absence proofs hold (a broader synonym search also gave 0 relevant hits), dev and eval are disjoint (including alternates), and the matrix is deterministic. Real defects, all stale values left after later edits:
  - (1) Design §19 says plain semantic matches are 6%; the matrix says 9.4% since review fix #22.
  - (2) The report's file table says "14 offline checks"; there are 17.
  - (3) The master plan, EPIC-05 and design line 3 still say "awaiting owner review", while the report says the owner reviewed.
  - (4) "23 accepted" findings is really 22 accepted, 1 partly accepted and 1 decided by the author (the DEV-006 scoring rule, not confirmed by the owner).
  - Not evidenced: `gitnexus_detect_changes()` before the task commits.
  - *Accepted process gap (REORIENT-001, 2026-09-24):* `gitnexus_detect_changes()` was not recorded for any EVAL-001 commit (also CORPUS-001, HOUSE-001). It cannot be recreated after the fact; it is recorded in `docs/plans/task-ledger.md` and run before every commit from REORIENT-001 on.
- *Verifier findings (re-verify, [review](docs/reviews/evaluation/EVAL-001-reverify.md)):* verdict ACCEPT. Scope: the fix commit `629b931` and the owner-decision commit `831d5a0`, which had never been verified.
  - Fixes 1–5 pass. The design says 9% and the matrix 0.094. There are 17 tests and 85 `quote:` lines. The status lines are corrected. The tally matches review §5 (22 accepted, 1 partly accepted, 1 decided). The DEV-006 open item is superseded by D2.
  - `831d5a0` reproduces:
    - every answerable source has a slot;
    - the multi-slot cases are exactly 022 and 029–032;
    - the new slot test fails on the old file and on 5 of 6 verifier mutations;
    - the coverage matrix re-generates byte-identical (`bf9109d5…1481`);
    - tests pass: 45 at each commit, 92 at HEAD;
    - `gitnexus detect-changes` (compare, run after the fact): 0 processes, risk low for each commit.
  - Real defects:
    - (1) No test pins BP-EVAL-022's two slots: merging them into S1 still passes (low).
    - (2) As committed in `831d5a0`, the D2 routing auto-labelled every insufficient answer `correct_refusal`, so a related note presented as the answer would never be checked. It was already fixed by the owner's REORIENT-001 C1 amendment (`evaluation-spec.md:40-44`).
    - (3) Design §18 offers the owner a split of 017's slot, but the re-check sheet does not ask (low).
  - Not evidenced: the owner's D1–D3 decision event; pytest and `detect_changes` before the two commits; the fix sessions' chat reports.
  - EVAL-002 stays blocked until the owner fills the re-check sheet's verdict lines.

### 2026-09-24 REORIENT-001 (branch `reorient-001`)
- *AI did:* task ledger (`docs/plans/task-ledger.md`); audit of CORPUS-001, HOUSE-001 and EVAL-001 against the current prompts ([report](docs/reports/execution/REORIENT-001.md)); prompt CHANGELOG; the EVAL-001 verify-fix → commit mapping; the owner re-check sheet for the 9 changed cases; ledger guard in `_common.md`; master plan synced to the prompt files. Docs only; 45 tests pass unchanged.
- *AI got wrong:* (1) When the AI carried owner decision D1 into the prompts (`8d04044`), it added evidence slots to 09b's metrics but left the flat `expected_source_ids` field lists in the EVAL-002 and EVAL-003a prompts (owner-written), although the design already had slots. EVAL-002 would have frozen a question file that can't score D1. (2) 09b and `evaluation-spec.md` used different citation label names, and 09b left out the points-covered score from OD-5. (3) `831d5a0` (D1–D3 blueprint and test changes) was committed after the EVAL-001 verification without a re-verify being scheduled.
- *How found:* the REORIENT-001 spec↔prompt comparison and the ledger build (commit dates vs the verify commit `e5e27b1`).
- *Fix:* C1–C4 settled by the owner and applied to the spec and prompts (CHANGELOG); the EVAL-001 re-verify now covers `831d5a0` too (ledger).
- *Human decision:* C1 judge checks refusals that carry related content; C2 spec label names; C3 prompts follow design §18; C4 partial = 0.5 in the points-covered score.
- *Verifier findings (99-VERIFY, [review](docs/reviews/code/REORIENT-001-verify.md)):* verdict ACCEPT WITH FIXES. The ledger, CHANGELOG, `_common.md` guard, EVAL-001 fix mapping and master plan reproduce; 45 tests pass; no code or ground truth changed. Real defects:
  - (1) The owner re-check sheet says "the only change to every case is the new `slot` field" and covers 9 cases. A parsed diff of `blueprint.yaml` (`9e0ab15` → HEAD, ignoring `slot`) shows 27 changed blueprints; alternate sources (005/006, 013/014, 017, 018, 027), an added evidence quote (003/004), citation criteria and acceptable variations (019, 027, 029, 034), 030's question notes and 4 dev cases changed without appearing on the sheet. The task copied the list from review §5 although the prompt said to verify it.
  - (2) The spec↔prompt sweep missed a conflict: `evaluation-dataset-design.md` §18 result-file names (`generated_answer`, `retries`, …) vs the 09a record (`answer`, `retry_count`, `latency_ms.total`) and 09c CSV columns, although the task added "schema = §18" to 09a.
  - (3) The `99-VERIFY.md` ledger-rights edit was not carried into the README's headless VERIFY `--allowedTools`, and still awaits owner confirmation.
- *Fixes (2026-09-25, "REORIENT-001: fixes from verification"):* (1) re-check sheet line 6 corrected and a table of the other 18 changed cases added with one `owner verdict:` line (a script diff of parsed YAML ignoring `slot` lists 27 changed blueprints, all now on the sheet; the verifier's list missed BP-EVAL-002 `retrieval_challenges`, also added); (2) C5: design §18 result file now uses the 09a names, 09c maps the brief's CSV columns explicitly; (3) README headless VERIFY gets ledger edit rights; (4) report "Deviations" 4–5; (5) EPIC-05 "EVAL-003a/b/c". Docs only.
  - *AI got wrong (in the fix):* deviation 4 named the files c867943 corrected as "ledger, CHANGELOG, report"; it was AI_WORKLOG, ledger, report and the owner re-check sheet. Found by the re-verify (FAIL, minor); corrected in the report.
  - *Human decision:* C5 prompt names win (spec updated); verifier may edit the ledger (confirmed 2026-09-25).
  - Not evidenced: `gitnexus_detect_changes()` covering the committed diff (the report says the tool saw the main checkout, not the worktree); the AskUserQuestion events for C1–C4.
- *Verifier findings (re-verify, [review](docs/reviews/code/REORIENT-001-reverify.md)):* verdict ACCEPT. Fixes 1–5 pass their checks: a parsed-YAML diff (ignoring `slot`) gives exactly the 27 cases on the re-check sheet, and every `owner verdict:` line is still empty; §18 field names match 09a, and 09c/§18 map the CSV columns the same way; README grants ledger edit rights; EPIC-05 is updated. 45 tests pass; docs only. `gitnexus detect-changes` (compare, run after the fact) → 0 processes, risk low for both the fix commit and the whole task range. Real defects:
  - (1) `docs/reports/execution/REORIENT-001.md` Deviation 4 says `c867943` corrected "ledger, CHANGELOG, report". `git show --stat c867943` shows AI_WORKLOG, ledger, report and the owner re-check sheet; CHANGELOG is not touched. So the fix's "AI got wrong (in the fix): none observed" is also inaccurate. Minor, non-blocking.
  - Still not evidenced: the AskUserQuestion events for C1–C4; owner authorship of the pre-commit edits.

### 2026-09-25 INGEST-001 (branch `claude/sleepy-wright-vj962y`)
- *AI did:* core models (`Document`, `SectionSpan`, `ParsedDocument`, D6 `DocumentChunk`, `Citation` defaulting to `heading`), Markdown parser + registry, the ADR-0003 D1 normalizer (CRLF first, preamble to metadata with unknown lines raising, boilerplate list from EPIC-01 + ADR-0003 plus a page-footer rule added in this task, blank-line collapse, section spans), the `NormalizeCorpus` use case and script, `normalized.jsonl`, 18 offline tests ([report](docs/reports/execution/INGEST-001.md)). 636/636 inventory heading paths located; all 107 evidence quotes survive normalization; 63 tests pass.
- *AI got wrong:* during the mutation check (breaking code on purpose to prove tests fail), the AI restored the mutated use-case file with `git checkout`, which does nothing for an untracked file, so the excluded-document guard stayed replaced by `if False:`.
- *How found:* the AI grepped the file after the restore step and saw the mutation still there, before any commit.
- *Fix:* the line was restored by hand; the full suite (63 passed) and the script were re-run after the restore.
- *Human decision:* owner (2026-09-25): keep the page-footer removal (extension of ADR-0003 D1) and keep the known residue (`---` before "Additional resources", #15 Q&A text).
- *Verifier findings (99-VERIFY, [review](docs/reviews/code/INGEST-001-verify.md)):* verdict ACCEPT WITH FIXES. The code reproduces: 63 tests pass (45 + 18); the script gives 636/636 and a re-run leaves `normalized.jsonl` byte-identical; a raw-vs-normalized line diff over all 24 docs shows 0 added lines and only the intended boilerplate removed (no false positives for the byline pattern); spans are contiguous and the last one ends at `len(text)`; mutation checks make the new tests fail. Real defects (documentation/claims only):
  - (1) The boilerplate list is attributed to the EPIC-01 report (worklog) / "EPIC-01 report and ADR-0003" (report). The `- Last updated on` + date footer and its `---` rule (19 docs) are in neither source: an unrecorded extension of the ADR-0003 D1 list, and the removal rules are spread over several constants although the prompt asked for one. ADR-0003's "version-selector lines" are not mentioned (none exist in the corpus).
  - (2) Commit message "gitnexus detect-changes: 0 processes, risk low": a compare-scope run against the parent gives 22 files, 5 affected processes, risk medium (all in new code). The default unstaged scope does not see new untracked files.
  - Not evidenced: the "3 tests fail" mutation count (the verifier's variant gave 7 failed + 4 errors); the pre-edit `gitnexus impact` results; the chat "Explain it back".
  - Observations (no fix required): a `---` before "## Additional resources" (20 docs) and #15's Q&A chrome stay in the text; the byline regex is broad enough to hit prose in a future corpus.
- *Fixes (2026-09-25, "INGEST-001: fixes from verification"):* removal list gathered in one documented block with a source per item; the footer extension of D1 and the absent version-selector lines recorded in `ingestion-spec.md` and report Deviation 6; provenance wording corrected; the GitNexus claim replaced with the compare-scope result; known residue listed. `normalized.jsonl` unchanged (sha256 `a6db2f26…9ae95`), 63 tests pass.
  - *AI got wrong (found by the verify):* (1) the removal list was credited to EPIC-01 although the footer rule is in neither EPIC-01 nor ADR-0003; (2) the commit message claimed "detect-changes: 0 processes, risk low" from the default scope, which ignores new untracked files (compare scope: 5 flows, risk medium, all new code).
- *Verifier findings (re-verify, [review](docs/reviews/code/INGEST-001-reverify.md)):* verdict ACCEPT. Fixes 1–4 pass their checks; fix 5 (optional) is handled as intended: the residue is listed and left to the owner. The code change in the fix commit is comments and constant order only: every top-level statement is AST-identical and the regexes are unchanged. The script re-run leaves `normalized.jsonl` byte-identical (sha256 `a6db2f26…9ae95`, 636/636) and 63 tests pass. The author's named boilerplate mutation reproduces (3 failed), so the earlier UNVERIFIED count is now evidenced. Compare-scope GitNexus: 23 files, 5 flows, risk medium, all new code; the report says 137 symbols, the verifier got 139, which is not material. Real defects:
  - (1) Code comment `markdown_normalizer.py:28` and `ingestion-spec.md:19` place the tab-selector lists in "#12/#13". They occur only in #12 (`grep "tabpanel\|?tabs="`). Trivial, non-blocking.
  - Open for the owner: the footer-removal extension of ADR-0003 D1 has not been confirmed (no AskUserQuestion recorded) and the optional residue removal has not been decided. Still not evidenced: pre-edit `gitnexus impact`, chat "Explain it back".

### 2026-09-25 INGEST-002 (branch `claude/inspiring-cray-fspsdh`)
- *AI did:* Arm A header-aware and Arm B fixed-size chunkers sharing one span→chunk builder (D5 embed text, D6 IDs, per-document duplicate drop), parameters in `config/chunking.json`, D8 stats, chunk files for both arms, G2 check script (11/11 PASS), spot-check of 10 chunks, 29 offline tests ([report](docs/reports/execution/INGEST-002.md)). Arm A 752 chunks (447 duplicates dropped), Arm B 859; 92 tests pass.
- *AI got wrong:* (1) the first "code block up to max is never cut" test used a 1,343-char block, which fits the 1,400-char sub-split limit anyway, so breaking atomicity did not make it fail; (2) four new tests first failed because they did not expect the separate `# Page` H1 chunk and the table test read the wrong chunk index; (3) the first overlap rule started table-continuation pieces mid-row (`|\n| row23`).
- *How found:* (1) mutation check (atomicity threshold set to 500: 0 failures); (2) first pytest run; (3) printing the table pieces while debugging (2).
- *Fix:* (1) test block made 1,400–1,600 chars, mutation now fails 1 test; (2) tests filter by heading path; (3) overlap inside a table starts at the next row, tested. The chunk files were regenerated after (3); the committed-file test caught the stale file.
- *Human decision:* table split: header row repeated in `embed_text` only, so `display_text` stays the exact slice (owner, 2026-09-25). Open: 19 heading-only Arm A chunks (D3 merges only siblings).
- *Verifier findings (99-VERIFY, [review](docs/reviews/code/INGEST-002-verify.md)):* verdict ACCEPT. All stats, G2 checks (11/11) and spot-check numbers reproduced from a fresh run; chunk files byte-identical; corpus checksums unchanged. Real defect found: (1) one Markdown link with a doubly nested `((…))` URL is not reduced to its text in `embed_text` of `23:header-1600:0085` (`_LINK` handles one nesting level; only occurrence in the corpus; minor). Mutation counts in the report (1/2/2 fails) differ from the verifier's own mutations (3/3) because the edits differ; the claim that tests can fail holds. GitNexus detect-changes output not re-checkable.

### 2026-09-25 INGEST-003 (branch `claude/workflows-ingest-002-review-svn2dq`)
- *AI did:* MarkItDown adapter (`markitdown_parser.py`) for `.pdf .html .htm .docx .txt` behind `ParserRegistry`, lazy import, signature check for `.pdf`/`.docx`; V-2 answered (0.1.8 on Python 3.13.12, Linux); OD-6 resolved (one adapter, stubs deleted); 12 offline tests with PDF/DOCX fixtures built in the test; dependency added to `pyproject.toml` + `requirements.txt` ([report](docs/reports/execution/INGEST-003.md)). Corpus outputs unchanged (`normalized.jsonl` sha256 `a6db2f26…9ae95`, chunk files byte-identical, G2 11/11).
- *AI got wrong:* the first "broken file raises" test expected MarkItDown to fail on a damaged `.docx`; it did not — MarkItDown guessed plain text from the content and returned the bytes as the document text.
- *How found:* first pytest run (1 failed, `DID NOT RAISE DocumentParseError`), then converting the file by hand.
- *Fix:* the adapter checks the `.pdf`/`.docx` file signature before converting; the test covers `.docx`, `.pdf` and a missing file; a mutation (check removed) makes it fail.
- *Human decision:* none (owner away). AI decisions flagged for the owner: OD-6 (one adapter, stubs deleted); converted files skip the D1 normalizer; transitive `onnxruntime` via MarkItDown's `magika` ([autonomous-session note](docs/plans/session-handoff-2026-09-25-autonomous.md)).
- *Verifier findings (99-VERIFY, [review](docs/reviews/code/INGEST-003-verify.md)):* verdict ACCEPT WITH FIXES (Linux verifier; 104 passed on 3.13.12 and 3.11.15; normalize/chunk/G2 outputs byte-identical, G2 11/11; corpus checksums unchanged). Real defects: (1) empty or textless conversions (empty txt/html, textless PDF, DOCX without paragraphs) return `text=""` → 0 chunks, no error, against `ingestion-spec.md` "MUST NOT silently drop"; (2) the signature check is incomplete: a header-only `%PDF-1.4` file and a non-Word zip named `.docx` are still returned as text by MarkItDown's content guess, and a missing `.docx` is reported as "not a valid .docx"; (3) `test_markitdown_is_imported_lazily` is not hermetic (subprocess imports the editable install, here the main checkout): an eager-import mutation in the worktree passed, and failed only with `PYTHONPATH=<worktree>/src`. Minor: UTF-8 BOM hides the first heading; `<title>` inner newlines kept in `document_name`; `text_content` is soft-deprecated; the CRLF test cannot fail on the adapter's own line; ADR-0002 D1 / architecture diagram still say converted files are D1-normalized; `onnxruntime` was already required by `chromadb`; the autonomous note's "For the owner" section is still empty. Detect-changes counts (15 files/19 symbols claimed, 19/24 at the commit) not reproducible; 0 processes / low reproduced.
- *Fixes (2026-09-25, "INGEST-003: fixes from verification"):* empty conversion raises; each extension goes to its own MarkItDown converter (no content guessing), replacing the signature check; hermetic lazy-import test; BOM/title/`markdown` minor fixes; stub test for the adapter's CRLF/BOM handling; docs (flow diagram, ADR-0002 amendment line). 113 tests pass (3.13 and 3.11); corpus outputs byte-identical; every fix proven by a mutation.
  - *AI got wrong (found by the verify):* (1) the signature check was only a partial fix for the silent-fallback problem the AI itself had found (header-only PDF and non-Word zip still became text); (2) empty conversions returned `""` and would vanish from the index; (3) the lazy-import subprocess test used the installed package, so it could not fail in another checkout; (4) the report called `onnxruntime` new although `chromadb` already needs it.
  - *AI got wrong (during the fix):* the first BOM mutation "survived" because the source held a literal invisible BOM character, so the `sed` mutation never matched; found by `cat -A`, replaced with the `\ufeff` escape, mutation then failed 1 test.
- *Verifier findings (re-verify, [review](docs/reviews/code/INGEST-003-reverify.md)):* verdict ACCEPT (Linux verifier, worktree whose editable install points at the main checkout). Fixes 1\u20136 pass their proofs; mutations reproduced (empty-text guard removed \u2192 4 failed; `MarkItDown` front end restored \u2192 5 failed; `is_file` check removed \u2192 1; eager `import markitdown` \u2192 1, so the lazy-import test is now hermetic; BOM strip, CRLF replace, title collapse \u2192 1 each). 113 passed on 3.13.12 and 3.11.15; normalize/chunk/G2 outputs byte-identical (11/11 checksums, G2 11/11). Real defects found: (1) minor, undisclosed behaviour change: calling the converters directly also skips the front end's per-line `rstrip` and 3+-newline collapse, so converted HTML keeps `<br>` hard-break spaces, `.txt` keeps extra blank lines/trailing spaces and PDF text ends with a form-feed line (corpus unaffected; chunk offsets still exact); (2) pre-existing: binary content in a `.txt` is still returned as text. Cosmetic: a literal BOM character in the report's fix-5 row; empty `PYTHONPATH` entry in the lazy-import test. Still open for the owner: OD-6, "converted files skip D1" (ADR-0002 amendment), V-2 on Windows, the empty "For the owner" section of the autonomous note.
- *Windows verification (2026-09-25, "INGEST-003: EOL-safe test helper (Windows)"):* V-2 = passed on Windows 3.13.3, 113 tests, after one fix.
  - *AI got wrong:* `_write()` in `test_markitdown_parser.py` used `Path.write_text` without `newline="
"`, so on Windows the Markdown side of `test_converted_formats_chunk_like_the_same_markdown` was CRLF while the MarkItDown HTML path yields LF: a platform-dependent test, missed because all verification ran only on Linux.
  - *How found:* owner ran the suite on Windows 3.13.3.
  - *Fix:* helper writes `newline="
  - *Lesson 1 (owner):* tests must be independent of the OS; writing an OS-dependent test causes problems like this one (EOL, path separators, encodings: be explicit).
  - *Lesson 2 (owner):* verify on the exact environment and OS of the owner's machine (Windows, Python 3.13.3 venv), not only on the AI's Linux sandbox.
"`; `MarkdownParser` untouched (keeps line endings, ADR-0003 D1); other `write_text`/`write_bytes` calls in `tests/` checked (single-line or bytes), none needed changes.

### 2026-09-25 OWNER-001 (commit `4ef58ed`, branch `owner-001`, PR #6)
- *AI did:* filled the EVAL-001 owner re-check sheet with the owner's verdicts, verbatim; applied the three blueprint changes (016 alternate removed, 024 P1 reworded, 017 split into slots S1 intro / S2 IMiddleware); added a slot test for 022 (and 017), shown to catch slot flips by two mutations; wrote the strict/lenient hit rule into `evaluation-spec.md` and 09b; marked the INGEST-003 AI decisions as owner-accepted; recorded N1/N2 as known limitations ([report](docs/reports/execution/OWNER-001.md)). 114 tests pass on Windows 3.13.3.
- *AI got wrong:* `gitnexus_detect_changes` was first run on a stale index (CLAUDE.md says to run `npx gitnexus analyze` first); found by the post-commit hook warning; re-run after `analyze`, report corrected in a follow-up commit.
- *Human decision:* all re-check verdicts, the 017 slot split, the strict + lenient reporting condition, and acceptance of OD-6 / D1-skip / per-format converters / `markitdown[pdf,docx]` (owner, 2026-09-25). Left open: which hit value is the headline number.
- *Verifier findings* (99-VERIFY, 2026-09-25, Windows 3.13.3, [OWNER-001-verify](docs/reviews/evaluation/OWNER-001-verify.md) → ACCEPT): no defect in the owner's decisions as applied (parsed-YAML diff: only 016/017/024 changed; all quotes verbatim under their headings; new slot test fails on 4/4 mutations; 114 passed). Stale text: the line above ("Left open: which hit value is the headline number") was not updated when the owner decided it in `7aeb783`: headline = lenient, strict alongside (`evaluation-spec.md` § Retrieval hit rule). Unverified: the report's `detect_changes` result for the OWNER-001 range (the CLI reads the indexed main checkout, which is on `dev`). Observation: 017's #10 "Service lifetimes" alternate note still says "P1 and P2" although it now sits in slot S2 (P1).

### 2026-09-25 INGEST-004 (branch `ingest-004`, PR into `dev`)
- *AI did:* wrote the ADR-0003 **D3a** amendment and put it behind `drop_heading_only` in `config/chunking.json` (Arm A only). Before changing code, it measured the exact rule on the committed file: 19 chunks, the same set as the old stat. It rebuilt both arms: Arm A 752 → 733, Arm B byte-identical by SHA-256. It re-ran G2 (11/11) and wrote a re-runnable blueprint coverage check: all 54 expected/alternate sections keep ≥ 1 Arm A chunk, and the counts are identical to before D3a. It added 6 tests; 120 pass on Windows 3.13.3 ([report](docs/reports/execution/INGEST-004.md)).
- *AI got wrong:*
  - (1) The first fence test could not fail. A whole fenced block always contains its ``` lines, so a detector that ignores fences also passed it. Found by a mutation (fence-unaware detector → 0 failures). Fixed with a test where an oversized code block is split so that one piece holds only `# …` comment lines. The first version of that test still passed under the mutation because the piece kept one `echo` line; the block was made longer, and now the mutation fails it.
  - (2) A shell heredoc mangled `\n` escapes while the test file was edited. That caused a SyntaxError at collection. The file was restored with `git checkout` and the edits were redone with the Edit tool.
  - (4) It ran `gitnexus_detect_changes` before the commit on a **stale index**, repeating the OWNER-001 slip. CLAUDE.md says to run `npx gitnexus analyze` when the index is stale. Found by the post-commit hook warning. Fixed by re-indexing and re-running as `compare` against `dev` (4 Arm A chunk flows, risk medium, as intended), with the report corrected in a follow-up commit.
  - (3) The first draft of the INGEST-002 addendum gave the size range of the dropped chunks as "13–40 chars" without measuring it. It was checked before the commit (13–24) and corrected.
- *Human decision:* D3a itself: drop heading-only Arm A chunks, decided 2026-09-25 before any index or result (owner).
- *Verifier findings* (99-VERIFY, 2026-09-25, Windows 3.13.3, [INGEST-004-verify](docs/reviews/code/INGEST-004-verify.md) → ACCEPT): no defect in the D3a implementation. Evidence: 19 dropped chunks, each heading-only; 0 content characters lost by D3a in 24/24 docs; Arm B SHA-256 unchanged; fresh Arm A = committed; IDs contiguous; G2 11/11; blueprint coverage 54/54 with unchanged counts; the drop-disabled mutation fails 5 tests, the fence-unaware mutation fails 1; 120 passed. Minor: (1) the execution report's Files-changed table says "5 new tests", but there are 6 (stale after the sixth was added); (2) the `heading_only_chunks` stat is still a single-line `#` proxy, not the D3a predicate; (3) `test_hash_lines_inside_a_code_fence_are_body_not_headings` cannot fail under a fence-unaware detector (disclosed; the split-piece test covers it). Unverified: the chat-only "Explain it back" bullets. Note: the corpus has no ATX-like `#` line inside a fence, so the fence rule is proven only by unit test + mutation. The literal "no content lost" invariant has gaps on #11/#13/#17/#23, caused only by the pre-existing D1 duplicate drop.

### 2026-09-25 INGEST-004 follow-up: fixes from verify (branch `ingest-004`, PR #7)
- *AI did:* fixed the four non-blocking notes of [INGEST-004-verify](docs/reviews/code/INGEST-004-verify.md).
  - One shared helper, `HeadingLines.heading_only` (`markdown_structure.py`), is now used by both the Arm A filter and the `heading_only_chunks` stat. A new test covers the case where the old proxy and D3a disagree.
  - The fence test was rewritten so it can fail. Mutations: stat proxy → 1 failed; fence-unaware heading set → 2 failed. Restored by SHA-256.
  - Both arms rebuilt: all four chunk/stats files are byte-identical to the verified versions.
  - The report's test count was corrected. The content claim is now precise: 0 characters lost by D3a in 24/24 docs; the gaps in #11/#13/#17/#23 come from D1 duplicates. I re-measured this myself and it matches review X3.
  - The Explain-it-back bullets are saved in the report. `_common.md` step 6 now requires that.
  - 121 passed ([report](docs/reports/execution/INGEST-004.md#follow-up-after-verify-2026-09-25-ingest-004-follow-up-fixes-from-verify)).
- *AI got wrong* (all found by 99-VERIFY, not by the AI):
  - (1) "5 new tests" in the report table; there were 6.
  - (2) The stat kept a single-line proxy instead of the D3a predicate, so filter and stat used two definitions.
  - (3) A fence test that could never fail was kept, only disclosed.
  - (4) The Explain-it-back bullets lived only in chat, so they could not be verified.
  - During the fix itself, a `sed`-based mutation wrote a real newline into a string literal, causing a collection error rather than a test result. Found in the pytest output, restored from backup, and redone with a Python replacement.
- *Human decision:* none new (the owner's follow-up prompt scoped the fixes).

### 2026-09-25 EVAL-002: questions + ground truth, freeze pending (branch `eval-002`, unattended cloud run)
- *AI did:* Step 0 housekeeping (ledger row 02; 017 alternate note trimmed to "P1", owner-approved). Wrote the wording of 42 questions (18 EN / 18 VI eval + 6 dev) in `question-wording-v1.yaml`; built `eval-v1.jsonl` / `dev-v1.jsonl` by script from the approved blueprints; validator (`validate_questions.py`) + 19 offline tests including mutation cases; review sheet `eval-v1-review.md` with a checklist and a "look at these first" list. 140 passed on Linux 3.11.15 ([report](docs/reports/execution/EVAL-002.md)). No tag, no final snapshot, M1 not reached: owner review first.
- *AI got wrong:* (1) One new mutation test assumed that removing the first evidence quote of 003 leaves P1 unsupported; 003 has three P1 quotes, so the validator (correctly) found no error and the test failed. (2) The first review-sheet generator left bare `List<int>` in table cells, which Markdown renders as an HTML tag.
- *How found:* (1) the first pytest run of the new file (1 failed); (2) reading the generated sheet.
- *Fix:* (1) mutation uses 015 with its evidence emptied; (2) `<` escaped outside code spans.
- *Human decision:* none yet. AI decisions to confirm and one ground-truth proposal (G1, not applied) are in the [review sheet](docs/reviews/evaluation/eval-v1-review.md) and the [handoff](docs/plans/session-handoff-2026-09-25-eval-002.md). GitNexus was unavailable in this container, so `detect_changes` was not run (no existing symbol edited).
- *Verifier findings (99-VERIFY, 2026-09-25, [EVAL-002-verify](docs/reviews/evaluation/EVAL-002-verify.md) → ACCEPT):* no defect that fails a requirement. Ground truth in the JSONL equals `blueprint.yaml` except the owner-approved 017 note; rebuild byte-identical; 107/107 quotes re-found independently; 140 passed. Non-blocking: (1) test gap: disabling the eval/dev expected-section overlap check leaves all 19 new tests green; (2) Q-EVAL-024 (vi) also states the cause ("test không chạy trong thư mục output"), a bigger leak than the sheet flags; (3) Q-EVAL-028 quote matches only via whitespace collapse (source has a no-break space), undisclosed; (4) G5A box 1 ticked before the freeze (with a "not frozen" note); (5) blueprints still `status: proposed`. Unverified: Windows run, GitNexus.

### 2026-09-26 RAG-001a: Gemini embedder + embedding cache, V-1 probe (branch `rag-001a`)
- *AI did:* core `EmbeddingTask` + `Embedder.model_id` + `EmbeddingError`; `GeminiEmbedder` (batching, sliding-window throttle, retry/backoff, L2 normalization, dimension check); SQLite `CachingEmbedder` (per-batch commit, resume, in-call dedup); `FakeEmbedder`; 32 offline tests + 1 live test; V-1 probe script; ADR-0005 ([report](docs/reports/execution/RAG-001a.md)). Asked the owner for dim / OD-7 / OD-8 (768, `data/chroma/`, cosine) and guided the before/after AI Studio reading. Live calls: probe (1 call, 3 texts) and the live test (1 call, 3 texts), each run once. 173 passed offline (after the owner check below); live test passed (cos EN–VI 0.9055 > EN–unrelated 0.6606).
- *AI got wrong:*
  - (1) The first code (commit `a8e4a2d`, written before the V-1 reading) charged the throttle 1 request per HTTP call. V-1 showed each text counts as a request, so a 40-text batch would have looked like 1 of 90 requests/min and run into 429s during indexing.
  - (2) One new throttle test expected a wait where 600 + 400 tokens exactly meets the 1,000 limit, so no wait is correct.
  - (3) The first draft of the execution report said the embedder test file has 24 tests; it has 21.
  - (4) A shell command meant to measure the pre-task test count included `git checkout origin/dev -- .`, which would have overwritten uncommitted doc edits.
  - (5) Found by the verifier (C1): the cache committed per 45-text slice while the embedder re-split slices into several HTTP calls, so a later failure could drop paid vectors; ADR-0005 D18 and the report claimed "never loses paid vectors".
  - (6) Found by the verifier (C2): the throughput simulation modelled `GeminiEmbedder` alone, not the `CachingEmbedder(GeminiEmbedder)` pipeline, so the 12.0-min Arm B figure did not hold for indexing (real: 18.0 min).
  - (7) In the fix session, the first version of the other-cwd path test compared the child process's paths only with the parent's; with cwd-relative paths both were equal, so the test could not fail.
- *How found:* (1) the owner's V-1 reading (AI Studio RPM 0 → 3 for one 3-text call); (2) the first pytest run (1 failed); (3) counting with `pytest --collect-only` before the commit; (4) blocked by the Claude Code auto-mode permission check before it ran. Nothing changed.
- *Fix:* (1) commit `05ec4d6`: throttle charges `len(batch)` requests, batches are capped at the per-minute request limit, a test pins the V-1 behaviour, and a mutation (per-call counting) fails it. (2) The test now asks for 500 tokens. (3) Corrected to 21 before the commit. (4) The command was dropped. The baseline count was not needed, so the report states only the tests this task adds.
- *Human decision:* dimension 768, OD-7 `data/chroma/`, OD-8 cosine (owner, AskUserQuestion). The owner read the AI Studio usage page for V-1, confirmed batch size 45, and set the quota plan (Arm A before today's 14:00 UTC+7 reset, Arm B after it).
- *Owner check → fix:* the owner asked for proof that the token budget holds over the sliding window and expected token-bound throughput. Re-checking showed a throughput gap the AI had missed: the throttle admits whole calls, so two 45-text Arm B calls (≈ 32K) could not share one 25K window, and Arm B would run at ≈ 45 texts/min. A simulation with the real texts put it at 18 min. Fix: each call is capped at half the per-minute token budget (simulated 12 min), and two tests were added: two worst-case calls in one window, and the real defaults on worst-case chunks. 173 passed.
- *Verifier findings (99-VERIFY, 2026-09-26, Windows 3.13.3, 0 Gemini requests, [RAG-001a-verify](docs/reviews/code/RAG-001a-verify.md) → ACCEPT WITH FIXES):*
  - (1) MEDIUM: paid vectors can be lost inside a cache slice. `CachingEmbedder` commits per 45-text slice, but `GeminiEmbedder` re-splits a slice over 12.5K est. tokens into several HTTP calls. If a later call fails, the earlier calls' paid vectors are dropped (repro: 85 quota requests charged, 0 rows stored). This contradicts ADR-0005 D18. Arm A: 4 of 16 slices split; Arm B: 19 of 20.
  - (2) MEDIUM: the half-budget cap does not reach the production pipeline. Through `CachingEmbedder(GeminiEmbedder)` Arm B still takes 39 calls and its last call starts at 18.0 min, not the 12.0 min in ADR-0005 D15. The simulation modelled `GeminiEmbedder` alone. Arm A is unchanged at 7.0 min.
  - (3) LOW: this entry's "30 offline tests" and "171 passed" are stale; the real numbers are 32 and 173.
  - Confirmed risks, rated, not fixed (owner): uncapped server retry-after (a 36,000 s `retryDelay` → 40 h of silent sleeps, MEDIUM); relative default paths (running outside the repo root creates an empty cache there, and it is **not** git-ignored, MEDIUM).
  - Checks that passed: mutations on the token check, the half-budget cap and the per-batch commit are each killed; live cosines recomputed from the cache (0.9055 / 0.6606 / 0.6172); no key in the repo, cache or reports; 173 passed.
- *Fixes from verify (2026-09-26, 0 Gemini requests, commit "RAG-001a: fixes from verify"; [report addendum](docs/reports/execution/RAG-001a.md#addendum-2026-09-26-fixes-from-99-verify)):*
  - F1: `Embedder.plan_calls` in the core protocol; the cache sends misses in the embedder's planned groups and commits each before the next call. Pipeline test: 2nd call always 503 → the 1st call's 35 rows are stored and a re-run pays only for the other 10.
  - F2: re-simulated through `CachingEmbedder(GeminiEmbedder)` with all chunk texts: Arm A 16 calls / 7.0 min, Arm B 25 calls / 12.0 min (was 39 / 18.0); ADR-0005 D15/D18/D19 updated.
  - Retry: daily-quota 429 → `QuotaExhaustedError` at once ("resume after the 14:00 UTC+7 reset"); other waits capped at 120 s and logged. The classifier is built from the documented error shape, not a real daily 429.
  - Paths: data paths resolve from the repo root (relative env values too); `.gitignore` uses `**/data/...`.
  - 186 passed. Mutations killed: count-only cache slicing (6 failed), no cap (1), daily retried (2), no log (1), cwd-relative paths (4, after fixing (7)).
  - *How (7) was found:* the MP1 mutation left that test green. *Fix:* it now also asserts the absolute paths under the repo root.
- *Verifier findings (re-verify)* (99-VERIFY of commit `94fdef2`, 2026-09-26, Windows, Python 3.13.3, 0 Gemini requests; [RAG-001a-verify § Re-verify](docs/reviews/code/RAG-001a-verify.md#re-verify-of-the-fix-commit-2026-09-26-0845-0900-utc7) → **ACCEPT**): no defect remains in F1, F2, retry or paths.
  - F1: the first verify's repro now stores 35 of 45 rows (it stored 0 before the fix). Both the count-only slicing mutation and the deferred-commit mutation are killed.
  - F2: my own simulation of the cached pipeline gives Arm A 16 calls / 7.0 min and Arm B 25 calls / 12.0 min, which matches the report.
  - Retry: the 36000 s retry delay is now capped at 4 × 120 s. A daily 429 fails at once with no retry.
  - Paths: files resolve from the repo root even when the process starts in another directory, and `**/data/...` ignore rules match there too.
  - Tests: 186 passed.
  - Non-blocking, all LOW: (1) `CachingEmbedder` has no `plan_calls`, so it no longer satisfies the core `Embedder` protocol; (2) the daily-429 classifier has not been tested on a real daily-quota response (disclosed); (3) `httpx.ConnectError` is still not wrapped; (4) the throttle's state lives in one process only.

### 2026-09-26 RAG-001b: ChromaDB vector store + index both arms (branch `rag-001b`, PR #10)
- *AI did:*
  - Step 0: moved `plan_calls` out of the core `Embedder` into the infrastructure `PlannedEmbedder`, and added a conformance test for `CachingEmbedder`. The first 429 of a run now logs its raw body, key redacted, before the daily-quota check.
  - Core: `RetrievedChunk` and the new `VectorStore` (`upsert`/`search`/`count`/`get_ids`).
  - `ChromaVectorStore`: one cosine collection per arm, named from the chunker config and the model id, metadata checked on open.
  - `IndexCorpus`: resume by chunk id, one `embed()` call, batched upserts.
  - Scripts `build_index.py` (with `--dry-run`) and `peek_retrieval.py`.
  - 25 offline tests (211 passed); 5 mutations, each killed. ADR-0005 amendment 2 ([report](docs/reports/execution/RAG-001b.md)).
  - Live:
    - Arm A: 733 = 733, 709 requests, 16 calls, 0 retries, 7.1 min. The re-run showed 0 new and 0 API requests.
    - One sanity query: 1 request.
    - Arm B (after the 14:00 UTC+7 reset, started by hand at 14:09 because the background waiter had been stopped for low memory): 859 = 859, 859 requests, 25 calls, 0 retries, 12.1 min (12.0 simulated), throttle wait 669 s. Re-run: 0 new, 0 API requests, 0.148 s. Arm A still 733 = 733.
    - Both collections were first written to `D:\ChromaDB` (the owner's `.env`), not `data/chroma/` (ADR-0005 D16); see (4).
    - Owner decision 14:37: the index moves to `data/chroma/` (D16 stands); the owner edited `.env`. Rebuilt both arms there from the embedding cache: A 733 = 733 and B 859 = 859, both cosine, **0 API requests** (709 + 859 cache hits); re-runs 0 new. The sanity query on the rebuilt store gave the same top-5 and scores. This is live evidence that the cache works.
- *AI got wrong:*
  - (1) The first ledger edit named a commit hash, `33c5e3b`, that does not exist; I wrote it before looking up the real hash.
  - (2) My first plan had `IndexCorpus` embed in 100-chunk slices. The embedder would then have planned calls per slice (e.g. 45 + 45 + 10), which breaks ADR-0005 D15's call plan and the 7.0 / 12.0 min figures the verifier accepted.
  - (3) My first planned score test, "identical vector → score ≈ 1", could not tell cosine from inner product or squared L2.
  - (4) I took the store path from ADR-0005 D16 and the code default (`data/chroma/`) without checking `.env`. The owner's `.env` still sets the old `CHROMA_PATH=D:\ChromaDB`, so both arms were indexed there. My morning key scan of `data/chroma/` therefore checked an empty folder, and the report named the wrong location.
- *How found:*
  - (1) my own `git log` check right after the edit, before any commit;
  - (2) and (3) the advisor's review of the plan, before any code was written;
  - (4) my own count check at 14:22: it skipped `load_dotenv` and saw 0 items, and a second check with `.env` loaded saw 733 and 859.
- *Fix:*
  - (1) Replaced it with the real `efc11e3` before committing.
  - (2) One `embed()` call for all pending texts, with only the upsert batched. The dry-run and the live Arm A call counts (16) match D15.
  - (3) An extra test: a query `[2,0,0]` against a stored `[1,0,0]` must score 1.0 (inner product would give 2, squared L2 would give 0). The `DISTANCE = "ip"` mutation fails it.
  - (4) Re-ran the key scan on the real store (`D:\ChromaDB`, raw bytes): 0 matches. The report now gives the real path, with the morning scan marked as a correction. I did not edit `.env` or move the store myself. The owner chose `data/chroma/` and edited `.env`; I rebuilt there from the cache (0 requests) and re-scanned `data/chroma/` (0 matches). `D:\ChromaDB` is left for the owner to clean up.
- *Human decision:* index location `data/chroma/` (owner, 14:37; ADR-0005 D16 stands); the owner edited `.env`. The quota plan (Arm A before 14:00, Arm B after) and the accepted open items come from the owner's prompt (ADR-0005 D19).
- *Verifier findings* (99-VERIFY, 2026-09-26, Windows 3.13.3, 0 Gemini requests, [RAG-001b-verify](docs/reviews/code/RAG-001b-verify.md) → ACCEPT): no defect fails a requirement. Reproduced: store 733 = 733 and 859 = 859 with cosine and all stored IDs, documents and metadata equal to the JSONL; unit-norm 768-dim vectors; cache 1,568 document + 1 query rows; quota 716 / 859 / 0; 211 passed vs 186 on dev (+25). Findings: (1) stale narrative: report line 149 said the store was not re-indexed into `data/chroma/`, superseded by the rebuild (note added, original kept); (2) Arm A has 11 duplicated texts / 24 extra copies (doc 17 source repetition, plus docs 23 and 13) that can fill several top-k slots: RAG-002 must dedupe by `content_hash`; (3) full-key/prefix scan not reproducible by the verifier without opening `.env` (`AIza+35` scan: 0 matches); (4) the first-429 log is proven only against fakes.

### 2026-09-26 EVAL-003b-pre: verifier findings (branch `eval-003b-pre`, PR #12)
- *Verifier findings (99-VERIFY, 2026-09-26, Windows 3.13.3, 0 Gemini requests, no ChromaDB, [EVAL-003b-pre-verify](docs/reviews/evaluation/EVAL-003b-pre-verify.md) -> ACCEPT WITH FIXES):*
  - (1) MEDIUM (report / spec wording, not code): the report says no case can be evidence-hit from alternate-section retrieval and calls evidence_hit "strict-like"; the owner is told to paste that into `evaluation-spec.md`. False for 4 of 32 cases: Q-EVAL-003 and 004 (their quotes also occur in `#12 ... Developer Exception Page`, an approved alternate) and Q-EVAL-007 and 008 (also in `#23 ... Route constraint reference`). With real Arm A and Arm B chunks that overlap no expected span, the real functions give evidence@5 = 1, lenient section = 1, strict section = 0. The report's check covered only the 3 quotes whose sole location is an alternate section, which is narrower than the sentence.
  - (2) LOW: the M5 mutation transcript shows "1 failed"; running the whole retrieval test file gives 3 failures.
  - (3) LOW: the report writes the float `(1-0.95)/2*100` as `2.5000000000000022`; Python prints `2.500000000000002`.
  - Observed, cause unverified: one pytest subprocess in the verifier's mutation harness died with Windows exit 3221225773 (commit limit reached, about 875 MB virtual memory free); it passed on every re-run. Consistent with the earlier truncated run being environmental. Both full runs here: 272 passed, 1 deselected.
  - Checks that passed: scope (14 added files only); 51 metric values on Q-EVAL-017, 022 and 031 equal my hand calculations on real Arm A records; McNemar / bootstrap (pairs together, independent reimplementation) / Wilcoxon equal hand-computed exact p; `expected-spans-v1.json` rebuilds byte-identical with correct input hashes; frozen hashes unchanged; mutations M1-M5 all caught (scratch copy); all report numbers traced.
- *AI got wrong (owner entry, 2026-09-26):* Same false assumption appeared twice (owner-side assistant, then this report): that evidence quotes exist only in expected sections. Caught by verify on real Arm A/B chunks.
- *Fix:* commit `943f063` and the follow-up report commit. The report and the proposed spec/CHANGELOG lines now say evidence_hit is content-level (aligns with lenient section hit, not strict; strict reported alongside). A new per-case diagnostic `evidence_hit_via_alternate_only` has 1 unit test and gives 4 / 32 on both arms with simulated alternate-only retrieval (003, 004, 007, 008). M5 was re-run on the whole retrieval test file: 5 failed, 25 passed. The verifier reported 3; the reason for the difference was not checked, and the 5 failing tests are listed in the report. The float is now written as Python prints it. Full suite: `273 passed, 1 deselected`.
- *Human decision:* owner chose option (a): keep the per-required-point rule, change only the wording, and add the diagnostic (2026-09-26).
- *Verifier findings (re-verify)* (limited re-verify of `943f063`, `281acb8`, `536e2e1`, merge `bebf486`, `001ec17`; 2026-09-26, 0 Gemini requests, no ChromaDB, [EVAL-003b-pre-verify § Re-verify](docs/reviews/evaluation/EVAL-003b-pre-verify.md) -> **ACCEPT**, 13 PASS / 0 FAIL / 1 UNVERIFIED):
  - Reproduced:
    - No strict or strict-like claim is left: every mention is a quote or is withdrawn. The owner's sentence is in the report, the proposed spec and CHANGELOG lines, and the PR body.
    - Matching code unchanged since `fd59109` (numstat 23/1 docstring + new function, 1/1 comment).
    - Own independent recount of alternate-only evidence hits: 4 / 32 on Arm A and Arm B (Q-EVAL-003, 004, 007, 008), with evidence 1, lenient 1, strict 0. The quotes sit only in approved alternates (#12/#13 Developer Exception Page, #23 Route constraint reference). The branch's function gives the same set.
    - The diagnostic's test fails under 4 scratch mutations.
    - Merge `bebf486`: 2 parents, 1 conflict (AI_WORKLOG only), no parent line lost or reordered, ledger = dev + the 09b note, 17-file scope.
    - Tests: dev `226 passed`, merged `313 passed, 1 deselected` (x2) = 226 + 87 collected, pre-merge `273`.
    - Frozen hashes unchanged; no key.
  - *AI got wrong (first verifier):* the first verify reported 3 failures for mutation M5. The report's M5 diff gives 5 failures on the `fd59109` tree (the same 5 tests as now), so later tests do not explain the gap. The first verifier either undercounted or ran an unrecorded variant; its exact diff was not saved. The owner's follow-up repeated the 3; the author's measured 5 is right for the report's M5. This answers the "reason for the difference was not checked" line above.
  - Non-blocking notes for 09b proper:
    - The diagnostic splits top-k chunks, not quote locations, into inside and outside, so it can under-count at section boundaries.
    - "Outside" also covers non-approved sections. On the current data there are none.
    - Only the "evidence_hit = 1" reading of "every hit point" gives the owner's 4 cases; the literal reading gives 7.
  - UNVERIFIED: the report's point-in-time memory figure (~1.5 GB free) and the historical truncated runs (not reproducible). None of my 4 full-suite runs was truncated.

### 2026-09-26 RAG-002: retrieval, grounded generation, citations, "insufficient information" (branch `rag-002`, PR into `dev`)
- *AI did:*
  - Built the question path: `detect_language`, `Retriever` (over-fetch + dedup), `answer_v1` prompt builder, marker/citation resolution, `AnswerQuestion` with the retrieval gate and the LLM `insufficient` layer, and a basic `GeminiLLM` in JSON mode (`response_json_schema`).
  - Core contracts: `LLMRequest`/`LLMResponse`, `AnswerResult`, `Citation` fields, `RetrievalError`/`GenerationError`.
  - 56 offline tests (369 passed); 4 mutations, each killed.
  - Dev-only live checks: 6 embed + 2 LLM requests, 0 × 429.
  - OD-9 threshold 0.686 (dev set, Arm A); OD-10 prompt file. Specs filled.
  - Checked compatibility with the EVAL-003b-pre metrics and the GUI-001-pre contract; mismatches listed ([report](docs/reports/execution/RAG-002.md)).
- *AI got wrong:*
  - (1) I first implemented dedup by `content_hash`, as the addendum said, and wrote in the docstring that the duplicates dropped at query time are "copies of one text in two documents". Both were wrong for this corpus. By `content_hash`, Arm A has only 2 extra copies. The verify note's 24 were identical `embed_text`: same-document repeats in doc 17/23/13 that differ only in link URLs.
  - (2) A test sentence meant to count as an uncited fact had 4 words, below the 5-word rule.
  - (3) A heredoc edit turned `\n` escapes into real newlines in `dev_check.py` (SyntaxError).
  - (4) The GitNexus index was stale, so the first impact queries returned "not found".
- *How found:*
  - (1) the offline duplicate analysis run before any live call (2 groups vs the 24 expected), then a diff of the duplicate chunks;
  - (2) the failing test;
  - (3) the script run;
  - (4) `npx gitnexus status`.
- *Fix:*
  - (1) the owner chose `passage_hash` (hash of the link-stripped body): Arm A 26 extra copies, Arm B 0. The kept hit carries `duplicate_chunk_ids`; the docstring was rewritten; a link-only-difference test was added (mutation M1 kills it).
  - (2) the sentence was lengthened.
  - (3) fixed with an exact edit.
  - (4) `npx gitnexus analyze` (counts in CLAUDE.md/AGENTS.md committed as a chore).
- *Human decision:*
  - Dedup key `passage_hash`, `duplicate_chunk_ids`, and the eval-span overlap check: two eval cases touch a duplicate group, both on the doc 12/13 pair (list in the report). The proposed 09b overlap rule was recorded, not implemented.
  - `answer_v1` approved with 2 LLM calls; rule 2 is the owner's text. Two small wording additions (rules 3 and 4) were flagged and approved.
  - Threshold rule and live budget from the owner's addendum.
- *Verifier findings* (99-VERIFY, 2026-09-26, Windows 3.13, 0 Gemini requests, [RAG-002-verify](docs/reviews/code/RAG-002-verify.md) → ACCEPT WITH FIXES):
  - **F1 (defect):** the citation-marker regex `\[(\d+)\]` also matches code.
    - Probe: `args[0]` → `args`, `values[7]` → `values`, both recorded in `dropped_markers`; `items[2]` in a fenced block → an invented citation to passage 2.
    - It changes code shown to the user and the hallucination diagnostic. The prompt's "extract `[n]`" did not address code. Fix prompt in the review.
  - Reproduced:
    - 313 (dev `dfcfbd4`) vs 369 (+56);
    - Arm A 13 groups / 26 extra copies, Arm B 0 (from Chroma);
    - the eval-overlap list (Q-EVAL-003/004 S1 only);
    - all 12 dev top-1 scores from the cache (0 misses), so threshold 0.686;
    - the M1 and M3 mutations each fail 1 test.
  - Firewall: 0 question texts; 0 eval IDs in `validation/generation` + `data/logs`. `AIza+35`: 0 in the diff and `validation/`.
  - Notes:
    - doc 15 bodies keep data-URI SVG links (chunker, pre-existing);
    - GUI-pre fake inlines the messages;
    - gate equality is only implied by `<`.
- *Fix F1* (2026-09-26, branch `rag-002`, 0 Gemini requests, [report addendum 7](docs/reports/execution/RAG-002.md)):
  - `[n]` inside inline code or fenced blocks, and `[0]` anywhere, are no longer markers (owner decision): left
    byte-identical, not cited, not in `dropped_markers`; code-only sentences count as uncited. Verifier probe now
    returns the answer unchanged, citations [1], dropped ().
  - Prompt `answer_v2` (v1 + "Wrap code, identifiers and expressions in backticks.") is the configured default;
    `answer_v1.md` unchanged. Spec sentence: score == threshold passes the gate (N3).
  - 369 → 384 passed (+15). Mutations: code skipping off → 7 fail; `[0]` rule off → 3 fail. Awaiting re-verify.
  - Backlog (not fixed): GUI fake hard-codes the insufficient messages → GUI-001 wiring (N2); doc 15 SVG links in
    chunks → QC-001 (N1).

### 2026-09-26 RAG-003: retry/fallback, error classification, accounting, CLI, smoke checks (branch `rag-003`, PR into `dev`)
- *AI did:*
  - Recorded OD-11 (owner's addendum) as an ADR-0004 amendment; moved the embedder's retry / retry-after / quota / key-redaction helpers into `infrastructure/gemini_retry.py` and used them from both adapters.
  - `GeminiLLM`: per-model throttle (13 / 4 RPM from config), 3 attempts with backoff + jitter + retry-after (cap 120 s), one fallback attempt, `ALLOW_FALLBACK`, classification into core `LLMQuotaError` / `LLMUnavailableError` / `LLMRequestError` (`kind` = the GUI's kinds), accounting (`model_used`, `retry_count`, `fallback_used`, tokens incl. thoughts, `retry_wait`, `throttle_wait`).
  - `scripts/ask.py` (`--json`, `--gate-off` diagnostic), `composition.py`, `scripts/generation/smoke_check.py` (dev-only, budget of 5, stops at the first provider error).
  - 162 new offline tests (546 passed); 10 mutations, all killed (one only after a new test).
  - Live smoke checks on dev questions: 4 LLM requests, 0 embedding requests, 0 × 429 ([smoke file](validation/generation/smoke-2026-09-26.md)); `-m gemini` 1 passed on cached vectors.
- *AI got wrong:*
  - **Embedder behaviour.** The first commit made the embedder retry connection errors as a side effect of the shared classifier, against an owner-accepted item in ADR-0005 amendment 2 (no connection-error retry in the embedder).
  - **Untested guard.** Mutation M9 (drop the key redaction from the error message) survived: the message never held provider text, so no test could see the guard.
  - **Wrong CLI assumption.** I added an `--excerpt-chars` option; a failing test showed the citation builder already bounds excerpts at 300 characters.
  - **Evidence written last.** The smoke script wrote its evidence file only at the end, so a killed process would have lost what was spent.
  - **Quoting slip.** A patch script written through a shell heredoc turned `\n` inside f-strings into real newlines and broke `smoke_check.py`.
  - **Eval-style ID in a test.** A test fixture used an eval-style ID, which the firewall scan flagged.
  - **Overstated test-first.** The first version of the report said the CLI and smoke tests were seen failing before the code; their first run was in the same step that wrote the code, and the composition tests (which were seen failing) were described the other way round.
- *How found:*
  - Embedder: grepping the docs for RAG-003 before writing them (ADR-0005 line 127).
  - M9: the mutation run.
  - Excerpt: a failing test.
  - Evidence file: the first live attempt was cut off by an OpenBLAS memory error at process start (0 requests sent, low free virtual memory).
  - Quoting slip: `SyntaxError` at test collection.
  - Fixture: the firewall scan.
  - Test-first claim: the advisor review compared the report with the session transcript.
- *Fix:*
  - Embedder: connection errors are wrapped into `EmbeddingError` but not retried (a `connection_error` flag on the shared `Failure`), tests changed, ADR notes added (`6b05922`).
  - M9: a test where the key is echoed inside the quota id.
  - Excerpt option removed.
  - The smoke script appends line by line, and the real-process CLI check runs last.
  - The block was rewritten through the file tool.
  - The fixture uses made-up values.
  - The report now lists what was seen failing and what was only seen passing; no red run was staged after the fact.
  - The first live attempt was re-run once with one BLAS thread, and one hung full `pytest` run (10 minutes, no CPU) was killed and re-run once (546 passed in 16 s); both logged in the report.
- *Human decision:* the whole addendum: OD-11 policy, the 13 / 4 RPM throttle and limits, `ALLOW_FALLBACK` and the eval runner's use of it (ledger note for 09a), the smoke design and its budget (at most 5 LLM and 0 embedding requests), `--gate-off` as a diagnostic. Open for the owner at `99-VERIFY`: the choices listed in the [report](docs/reports/execution/RAG-003.md) ("Decisions and open choices").
- *Verifier findings* (99-VERIFY, 2026-09-26, Windows 3.13.3, 0 Gemini requests, [RAG-003-verify](docs/reviews/code/RAG-003-verify.md) → ACCEPT WITH FIXES): 546 offline tests pass (dev 383); the embedder's RAG-001a tests pass unchanged against the branch; no test assertion was deleted or loosened; three mutations (retry count, daily-quota fast path, `ALLOW_FALLBACK` guard) each fail tests (9, 3, 5) and the files were restored byte for byte. Defects: (1) **502 is not retried**: `RETRYABLE_STATUS` is the embedder's `{429, 500, 503, 504}`, but the owner's list includes 502; a probe showed a 502 skips the retries and spends one of the fallback's 20 daily requests, and the ADR note that lists the embedder's set does not mention the omission. (2) The `--json` output schema is documented only in code and one test, not in the spec, `--help` or the docstring. (3) The parametrized error-boundary test lacks the persistent 500 and 400 cases (500 and 400 behave correctly in a probe and in other tests). Unverified: whether thinking tokens count against `max_output_tokens` (the installed google-genai 1.75.0 does not say; the adapter sets no `thinking_config`; default `max_output_tokens` is 1024; the fallback used 370 thinking tokens in the smoke check).

## Summary: how AI helped

To be filled at QC-001.

## Incorrect AI outputs and improvements

To be filled at QC-001, from the log above.

## With 7 more days

To be filled at QC-001.

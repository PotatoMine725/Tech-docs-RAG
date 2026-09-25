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
"`; `MarkdownParser` untouched (keeps line endings, ADR-0003 D1); other `write_text`/`write_bytes` calls in `tests/` checked (single-line or bytes), none needed changes.

## Summary: how AI helped

To be filled at QC-001.

## Incorrect AI outputs and improvements

To be filled at QC-001, from the log above.

## With 7 more days

To be filled at QC-001.

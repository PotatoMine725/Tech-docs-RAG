# VERIFY INGEST-004

Verifier session, 2026-09-25, Windows 11, `.venv` Python 3.13.3. Reviewed branch `ingest-004` (`bdd43ba`, `4b0eee0`, `8265d18`; base `dev` `712f028`; PR #7 into `dev`, open) against the task prompt `docs/prompt-log/claude-code/INGEST-004.md` (present, so A0 passes), `agents/prompts/_common.md`, ADR-0003 and the owner's extra checks 1–13.
I judged whether the implementation matches the owner's decision (ADR-0003 D3a). I did not re-argue the decision.

Method: all numbers below come from my own commands. Chunk files were rebuilt **in memory** by a scratch script (`build()` from `scripts/ingestion/build_chunks.py`, no repo writes). `check_g2.py` rewrites its report on every run; I ran it and `git status` stayed clean. Mutations used a scratch backup of `header_aware.py`. After each restore, SHA-256 was `10a41956…ab043`, the same as before, and `git status` was clean.

## A. Acceptance / gate items (prompt steps + owner's extra checks)

| # | Item | Result | Evidence |
|---|---|---|---|
| A0 | Task prompt exists | PASS | `docs/prompt-log/claude-code/INGEST-004.md` present; it matches the chat prompt quoted in the execution report. |
| Entry | OWNER-001 `verified`; no ChromaDB index | PASS | Ledger row 01o `verified`. `git ls-files data/chroma` → only `data/chroma/.gitkeep`; the directory holds only `.gitkeep`. |
| Step 0 / X12 | Ledger row 02 says it waits for INGEST-004 (verified) and that OWNER-001 was verified 2026-09-25 | PASS | `task-ledger.md:20`: "**Waits for INGEST-004 (verified) — OWNER-001 verified 2026-09-25.**" The *Needs* column also gained "+ INGEST-004 verified" (disclosed, Deviation 1; mirrored in `agents/prompts/README.md` + CHANGELOG). The prompt's literal old text was already gone (`712f028`), as disclosed. |
| Step 1 / X1 | ADR-0003 D3a: rule, reason, Arm B unchanged, decided before any index/result | PASS | `0003-…md:27-33`. **Rule:** "drops every chunk whose display text is empty once heading lines (outside code fences) and blank lines are removed". **Reason:** 3 bullets: no content (path already in every child's D5 header), crowds top-k, false section hit in Arm A's favour. "Arm B is unchanged." **When:** "decided before any index, retrieval run or evaluation result existed. No result informed it." The status line (`:4`) notes the amendment. |
| Step 2 | Implemented in the header-aware chunker, config-driven, offline tests | PASS | `header_aware.py:72-74` (filter in `spans()`, before `build_chunks` assigns IDs), `:240-243` (`_heading_only`), `HeaderAwareConfig.drop_heading_only: bool = False` (`:35`); `config/chunking.json` Arm A `"drop_heading_only": true`. Tests `test_chunkers.py:73-115`. |
| X2 | "Heading line" ignores `#` lines inside code fences; a chunk whose only body is a code fence is kept | PASS (proof by test + mutation; no real `#`-in-fence case exists) | The detector is `find_headings` (`markdown_structure.py:42-60`). It tracks fence state from the start of the document and skips fenced lines. **Real-corpus probe:** 12,758 fenced lines in the normalized corpus, and only **1** starts with `#`: `#!/usr/bin/env dotnet`, which is not ATX. **0** fenced lines match the ATX pattern, so the corpus cannot show the `# comment` case (C# uses `//`). A probe that builds a one-line span on every fenced ATX-like line judged 0 lines heading-only (vacuous: 0 candidates). **Proof for fenced `#` lines:** `test_a_split_code_piece_of_only_hash_comment_lines_is_kept` (`:99`). My mutation (heading set = `_HEADING` on every line, fence-unaware) → **1 failed**, that test. **Real chunks whose only non-heading content is a code fence:** 13 kept Arm A chunks (e.g. `03:header-1600:0019`, `17:header-1600:0010`, `0015`, `0029`, …), all present in the committed and fresh file. |
| Step 3 / X4 | Rebuild: Arm A 733, 19 dropped, each heading-only | PASS | Fresh in-memory build: 733 chunks. Old file (`712f028`) vs new, matched on (source, char_start, char_end): **19 dropped**. For each, the document lines of the span minus `find_headings` lines are empty (`rest-after-headings=[]` for all 19). List: `06:0007`, `08:0001/0004/0007/0009/0011/0013`, `09:0001/0003/0005`, `10:0041`, `12:0026`, `13:0103`, `16:0010`, `17:0132`, `18:0002`, `20:0014`, `26:0008`, `28:0009` (all `header-1600`). Display texts: 10 × `## Additional resources`; #08 `Choose your path`/`Fundamentals`/`What's new`/`Key concepts`/`C# language reference`/`Stay in touch`; #09 `C# language reference`/`What's new`/`Stay in touch`. The count is 19, as expected. The other 733 old chunks equal the new ones in every field except `chunk_id`, in the same order: **True**. |
| X3 | No content lost: every non-whitespace character not on a heading line lies in ≥ 1 kept chunk | PASS for INGEST-004. Literal statement: 20/24 | Script over all 24 docs (heading lines = `find_headings`; see table below). **D3a-attributable loss: 0 characters in every doc.** Uncovered counts are identical before and after D3a. Taken literally, the invariant fails on #11/#13/#17/#23. There, D1 (ADR-0003, pre-existing) drops chunks whose text duplicates an earlier chunk of the same document (4/135/118/190 drops; D1 is not part of this task). Over all D3a spans *before* the D1 duplicate drop, the invariant holds on **24/24** docs. So every gap lies in a span dropped as an exact copy of a kept chunk. |
| X5 | Arm B byte-identical | PASS | SHA-256 `arm-b.jsonl`: `712f028` = HEAD = disk = fresh = `2bde1a0e3b42374f03d725f3a7c2b31225c0d6115aa5dc510f49c49a7edb7f2c`. `stats-arm-b.json`: all four = `01395880a947bb46ebfc4b77f51f1e83009dd57d93f2d78510049001cb77fa8b`. |
| X6 | IDs deterministic and contiguous; no stale old IDs in `data/evaluation/` or `docs/` | PASS | Two in-memory Arm A builds are byte-equal (records and stats), and fresh = committed (`9c3bcc6c…`). All 24 docs match `{sid}:header-1600:{i:04d}` for i = 0..n−1 (0 non-contiguous). 11 renumbered, all in #08/#09 (the other drops were the last chunk of their doc). `git grep header-1600 -- data/evaluation` → 0 hits. `docs/`/`validation/` references to affected IDs: only the INGEST-002 addendum and the INGEST-004 report (historical, intended) and `spot-check.md:10`, which carries a D3a note. |
| X7 | Stats: `heading_only_chunks` = 0; totals updated and equal to a fresh run | PASS | Fresh: total 733, `chunks_under_small_chunk_chars` 60, `heading_only_chunks` 0, dups 447. Committed `stats-arm-a.json` SHA `26fab6bf…` = fresh. Old: 752 / 79 / 19 / 447; size min/p50/p90 13/1157/1526 → 89/1178/1527. See F2 on the stat definition. |
| Step 4 / X8 | G2 re-run; blueprint coverage ≥ 1 Arm A chunk for every expected/alternate path incl. 017 | PASS | `check_g2.py` → `**Overall: PASS** (11/11)`, and `g2-check.md` is unchanged by the re-run. `check_blueprint_coverage.py --no-write` on the committed file and on my fresh build: `Distinct (source, heading path) pairs: 54; with 0 overlapping chunks or not a section: 0 — PASS`, exit 0. My own overlap computation: 80 rows, 54 pairs, 0 zero or missing, and **0 pairs whose count changed** vs the pre-D3a file. BP-EVAL-017 (4 slots): `#11 Factory-based…` 1, `> IMiddleware` 7, `> Additional resources` 5, `#10 DI > Service lifetimes` 1. |
| X9 | Test strength: disable the filter → new tests fail; restore exactly | PASS | `if False and self.config.drop_heading_only:` → **5 failed, 115 passed**: `…h2_followed_by_its_h3_is_dropped`, `…sibling_headings…dropped_together`, `…ids_stay_deterministic…`, `…oversized_section_splits…`, `test_committed_chunk_and_stats_files_equal_a_fresh_run[A]`. Fence-unaware mutation → 1 failed (see X2). The file was restored byte for byte (SHA-256 equal, `git status` clean). |
| X10 | Config-driven; no Gemini/Chroma import; structure test green | PASS | Flag in `config/chunking.json` → `factory.load_arm` → `HeaderAwareConfig(**settings)`; default `False`. Arm B config has no key. The added imports are `find_headings` and, in the script, stdlib, `yaml`, and project modules only. `grep -rnE "chromadb\|google\.genai\|PySide6" src/…/core src/…/application` → none. `test_project_structure.py` → 7 passed. |
| X11 | Out of scope untouched | PASS | `git diff 712f028..HEAD --stat -- data/chroma data/evaluation corpus` → empty. `git tag -l "eval-freeze*"` and `git ls-remote --tags origin "eval-freeze*"` → none. No EVAL-002 file in the diff. `blueprint.yaml` blob `40c0f5a7…` is the same at `712f028` and HEAD. |
| Step 5 | Addendum, stats, ledger, worklog; branch `ingest-004`, pushed, PR into `dev` | PASS | `INGEST-002.md` addendum present. Ledger row 04a `done`. AI_WORKLOG entry present. `origin/ingest-004` = HEAD `8265d18`. `gh pr view 7` → OPEN, `ingest-004` → `dev`. |
| X13 | Full suite on this machine | PASS | `.venv/Scripts/python.exe -m pytest -q` → **`120 passed in 4.12s`** (Python 3.13.3). |

### X3 per-document table (non-whitespace, non-heading-line characters)

| Doc | Content chars | Uncovered by kept chunks (after D3a) | Uncovered before D3a | Lost by D3a | Uncovered by D3a spans before D1 dedup | D1 duplicates dropped |
|---|---|---|---|---|---|---|
| 01 | 26,872 | 0 | 0 | 0 | 0 | 0 |
| 02 | 22,752 | 0 | 0 | 0 | 0 | 0 |
| 03 | 17,666 | 0 | 0 | 0 | 0 | 0 |
| 04 | 8,472 | 0 | 0 | 0 | 0 | 0 |
| 05 | 6,617 | 0 | 0 | 0 | 0 | 0 |
| 06 | 5,943 | 0 | 0 | 0 | 0 | 0 |
| 07 | 6,503 | 0 | 0 | 0 | 0 | 0 |
| 08 | 2,694 | 0 | 0 | 0 | 0 | 0 |
| 09 | 755 | 0 | 0 | 0 | 0 | 0 |
| 10 | 36,322 | 0 | 0 | 0 | 0 | 0 |
| 11 | 14,423 | 2,739 | 2,739 | 0 | 0 | 4 |
| 12 | 21,132 | 0 | 0 | 0 | 0 | 0 |
| 13 | 193,646 | 108,542 | 108,542 | 0 | 0 | 135 |
| 15 | 13,923 | 0 | 0 | 0 | 0 | 0 |
| 16 | 8,765 | 0 | 0 | 0 | 0 | 0 |
| 17 | 210,923 | 92,179 | 92,179 | 0 | 0 | 118 |
| 18 | 2,036 | 0 | 0 | 0 | 0 | 0 |
| 20 | 13,756 | 0 | 0 | 0 | 0 | 0 |
| 21 | 30,225 | 0 | 0 | 0 | 0 | 0 |
| 22 | 1,240 | 0 | 0 | 0 | 0 | 0 |
| 23 | 321,466 | 166,666 | 166,666 | 0 | 0 | 190 |
| 26 | 6,631 | 0 | 0 | 0 | 0 | 0 |
| 28 | 7,063 | 0 | 0 | 0 | 0 | 0 |
| 29 | 942 | 0 | 0 | 0 | 0 | 0 |
| **Total lost by D3a** | | | | **0** | | |

## B. Tests

| Item | Result | Evidence |
|---|---|---|
| Suite | PASS | `120 passed in 4.12s` (114 before + 6 new). |
| New tests assert behaviour | PASS | Each drop test compares flag on vs off (`ARM_A` vs `ARM_A_KEEP_HEADINGS`), so it checks the drop itself, not only that code runs. The ID test asserts two equal runs, the exact `07:header-1600:{i:04d}` sequence, and 2 fewer chunks. The keep tests assert exact display text. |
| Tests that cannot fail | Minor | `test_hash_lines_inside_a_code_fence_are_body_not_headings` (`:93`) passes under the fence-unaware mutation. A whole fenced block always contains its ``` lines, so it can never be all-heading. The execution report admits this, and `test_a_split_code_piece_of_only_hash_comment_lines_is_kept` covers the real risk (killed the mutation). |
| Changed existing assertion | PASS | `:131` `len(chunks) == len(long_pieces)`. The removed "+1" was the fixture's bodiless `# Page` chunk, which D3a drops by design. What the test checks (splits within max at paragraph/sentence boundaries) is unchanged. |

## C. Claims vs reality

| Claim (execution report / addendum / PR) | Result | Evidence |
|---|---|---|
| 752 → 733; 19 dropped, same set as old stat; list of 19 | PASS | X4. |
| Size 13/1157/1526 → 89/1178/1527; <400 79 → 60; fence cuts 24 (3.19 → 3.27 %); dups 447 → 447; per-doc −1 ×10, −6 #08, −3 #09 | PASS | Old/new stats read directly; drop list per doc. |
| 11 renumbered IDs (list) | PASS | Same 11 pairs from my old/new comparison. |
| Arm B hashes | PASS | X5 (full hashes equal). |
| 733 remaining equal except `chunk_id`, same order | PASS | X4. |
| G2 11/11; coverage 54 pairs, 0 failing, counts identical pre-D3a | PASS | X8. |
| 120 passed; drop-disabled mutation 5 failed; fence-unaware 1 failed | PASS | X9, X2 (same failing tests). |
| detect_changes (compare vs dev): medium, 20 files, 4 processes `Chunk → Line_index`, `Chunk → Line_end`, `Spans → _cut`, `Chunk → Trim` | PASS | `gitnexus detect_changes(scope=compare, base_ref=712f028)` → `risk_level: medium`, `changed_files: 20`, the same 4 processes. |
| "5 new tests (below)" (Files-changed table, `INGEST-004.md:17`) | Minor (stale) | The same report later lists six, and 114 + 6 = 120. The table was not updated when the sixth test was added. Stale number, not fabrication. |

## D. Project rules

| Item | Result | Evidence |
|---|---|---|
| Layers / imports | PASS | X10. |
| Model names / API key | PASS | No model names touched. `git diff 712f028..HEAD \| grep -c AIza` → 0. The repo-wide `AIza` hits are earlier reviews quoting the grep command. |
| Corpus untouched; excluded docs unused | PASS | `git diff … -- corpus` empty. Chunk files cover the 24 accepted IDs only (no 14/19/24/27). |
| Eval freeze / no tuning on eval | PASS (N/A) | No `eval-freeze-*` tag exists (local or remote). No retrieval or evaluation was run. D3a was decided without results, as the ADR states. |

## E. Scope

| Item | Result | Evidence |
|---|---|---|
| Work beyond the prompt | PASS (disclosed, small) | (1) Row 02 *Needs* column plus the README/CHANGELOG mirror: this follows directly from step 0 and is disclosed. (2) `check_blueprint_coverage.py` + report: step 4 requires this check. (3) `spot-check.md` note: keeps a doc from citing a stale ID. No parameter changed without the ADR. Arm B code and the builder are untouched. |

## F. Quality spot-read

| # | Item | Result | Evidence |
|---|---|---|---|
| F1 | `_heading_only` (`header_aware.py:240-243`) | PASS | Checks every document line from `line_index(start)` to `line_index(end−1)`. `max(span.start, span.end−1)` guards an empty span. A span that starts mid-line (sentence split) takes in the whole line, but that line is prose, not a heading line, so the result is still correct. The heading set comes from the whole document, so the fence state is right even for a span cut from the middle of a fence. The filter runs before `build_chunks`, so IDs are assigned after the drop, and D1 dedup never sees the dropped spans (no effect here: dups 447 = 447). No exceptions are swallowed. |
| F2 | `stats.py:40` `heading_only_chunks` definition | Minor, non-blocking | The stat still counts "one line starting with `#`". It does not use the D3a predicate. It would miss a multi-line all-heading chunk (`## A\n\n## B`) if the filter were off. With the filter on, it would count a kept one-line in-fence `# note` piece as heading-only. The corpus has neither case, so 0 is correct here. The execution report chose not to change the stats schema so that Arm B's stats stay byte-identical (Deviation 5). |

## G. Explain-it-back

| Item | Result | Evidence |
|---|---|---|
| Bullets in the final report | UNVERIFIED | The final chat report is not saved in the repo. The execution report and the PR #7 body (`gh pr view 7`) have no "Explain it back" section. What I could check in the report, PR body and ADR is correct: rule, reason, "before results", Arm B unchanged, IDs contiguous, config flag. The one exception is the stale "5 new tests" (C). |

## Verdict: **ACCEPT**

0 FAIL. 1 UNVERIFIED (G: the chat-only explain-it-back bullets are not in the repo). The implementation matches ADR-0003 D3a:
- Exactly the 19 heading-only chunks are dropped.
- D3a loses 0 content characters in all 24 documents.
- Arm B is byte-identical.
- IDs are deterministic and contiguous.
- G2 passes 11/11, and blueprint coverage is 54/54 with unchanged counts.
- The tests fail under both mutations.

Minor notes, non-blocking, no fix prompt needed:
1. Execution report `INGEST-004.md:17` says "5 new tests"; it is 6.
2. The `heading_only_chunks` stat uses a single-line proxy, not the D3a predicate (F2). If the stats schema is revised later, count with the same `find_headings` predicate.
3. `test_hash_lines_inside_a_code_fence_are_body_not_headings` cannot detect a fence-unaware detector. The split-piece test covers that case.
4. The owner's literal "no content lost" invariant does not hold on #11/#13/#17/#23 because of D1 duplicate drops. D1 predates this task and was unchanged by it (X3).

For the owner: row 02 (EVAL-002) still says "Waits for INGEST-004 (verified)". Under 99-VERIFY the verifier updates only the task's own row (04a), so unblocking row 02 is the owner's step.

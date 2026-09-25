# INGEST-004 execution report: ADR-0003 D3a, drop heading-only Arm A chunks

Date: 2026-09-25 · Branch: `ingest-004` (from `dev` `712f028`) · Prompt: [prompt-log](../../prompt-log/claude-code/INGEST-004.md) · Environment: Windows 11, `.venv` Python 3.13.3

## Entry check
- OWNER-001 `verified` (ledger row 01o; merged into `dev` in `3e60b59`).
- `data/chroma/` contains only `.gitkeep`, so no ChromaDB index exists.
- `git status`: only `.claude/worktrees/` was untracked. It is not mine and was left alone.
- `dev` had no unpushed commits, so the PR holds only this task.

## Files changed
| File | Change |
|---|---|
| `docs/architecture/decisions/0003-chunking-parameters-and-experiment.md` | New **D3a** amendment: rule, reason, "decided before results", effect. Status line notes the amendment. |
| `src/.../infrastructure/chunking/header_aware.py` | `HeaderAwareConfig.drop_heading_only: bool = False`. With the flag on, `spans()` drops spans whose non-blank lines are all heading lines. Headings are found with `find_headings`, the same fence-aware detector the section splitter uses, so `# comment` lines inside a code fence are body. The drop happens before `build_chunks` numbers the IDs. |
| `config/chunking.json` | Arm A: `"drop_heading_only": true`; `_comment` cites D3a. Arm B has no key and is unchanged. |
| `tests/unit/infrastructure/test_chunkers.py` | 6 new tests (below; corrected from "5" after verify). `test_arms_come_from_the_configuration_file` asserts that Arm A's flag is on. The `ARM_A` test config mirrors the real config (flag on), and `ARM_A_KEEP_HEADINGS` has it off. One existing assertion was changed (Deviation 2). |
| `scripts/ingestion/check_blueprint_coverage.py` (new) | Step 4 check. For every expected and alternate (source_id, heading_path) in `blueprint.yaml` it counts the Arm A chunks that overlap the section's span, over any variant. It exits 1 when a count is 0 or the path is not a section. |
| `validation/ingestion/blueprint-coverage-arm-a.md` (new) | Output of the step 4 check. |
| `data/processed/chunks/arm-a.jsonl`, `stats-arm-a.json` | Regenerated. |
| `validation/ingestion/g2-check.md` | Regenerated; only the Arm A chunk count changed (752 → 733). |
| `validation/ingestion/spot-check.md` | Note on row `09:header-1600:0001`: that chunk is dropped and its ID now names the former `0002`. |
| `docs/reports/execution/INGEST-002.md` | Addendum: before/after stats and the renumbered IDs. |
| `docs/specs/ingestion-spec.md` | D3 interpretation points to D3a; the open item on heading-only chunks is marked resolved. |
| `docs/plans/task-ledger.md` | Step 0 on row 02; row 04's open item marked decided; new row 04a (INGEST-004, `done`). |
| `docs/plans/master-plan.md`, `docs/plans/epics/EPIC-02-ingestion-pipeline.md` | G2 note (733/733) and INGEST-004 status. |
| `AI_WORKLOG.md` | INGEST-004 entry. |
| `docs/prompt-log/claude-code/INGEST-004.md` (new) | The prompt, verbatim. |

## Commands run and results (real output)
Pre-edit impact (GitNexus MCP):
- `impact(HeaderAwareConfig, upstream)`: risk **LOW**, 1 direct importer (`factory.py`), 0 processes.
- `impact(HeaderAwareChunker.spans, upstream)`: risk **LOW**, callers `chunk_with_report` → `chunk`, 1 module (Chunking).

**Measurement before the change.** I applied the exact D3a predicate to the committed `arm-a.jsonl`. The predicate: every non-blank line is a heading line per `find_headings`. It matched 19 chunks. That is the same set as the old `heading_only_chunks` stat, which only looks for "one line starting with `#`". No multi-line all-heading chunk exists, so the expected count is 752 − 19 = 733.

The 19 dropped chunks:
- `06:0007`, `10:0041`, `12:0026`, `13:0103`, `16:0010`, `17:0132`, `18:0002`, `20:0014`, `26:0008`, `28:0009`: all `## Additional resources`.
- `08:0001/0004/0007/0009/0011/0013`: #08 hub H2s.
- `09:0001/0003/0005`: #09 hub H2s.

**Rebuild.** `build_chunks.py --arm A` and `--arm B`:
```
arm A (header-1600): 733 chunks over 24 documents
size min/p50/p90/max: 89/1178/1527/1600
chunks cutting a code fence: 24 (3.27%)
duplicates dropped: 447; documents with one chunk: []
arm B (fixed-1600): 859 chunks over 24 documents
size min/p50/p90/max: 207/1600/1600/1600
chunks cutting a code fence: 387 (45.05%)
duplicates dropped: 0; documents with one chunk: ['09', '29']
```

SHA-256 before (committed `712f028`) → after:
```
arm-a.jsonl       fa54cd8e…a427b → 9c3bcc6c…f229f   (changed, intended)
stats-arm-a.json  83a9bd54…e805  → 26fab6bf…d3d2    (changed, intended)
arm-b.jsonl       2bde1a0e3b42374f03d725f3a7c2b31225c0d6115aa5dc510f49c49a7edb7f2c → identical
stats-arm-b.json  01395880a947bb46ebfc4b77f51f1e83009dd57d93f2d78510049001cb77fa8b → identical
```
`git diff --exit-code` on both Arm B files: clean.

**Arm A old vs new.** I compared the committed file with the new one in a scratch script. 19 chunks were removed, all of them heading-only. The remaining 733 are equal to the old chunks in every field except `chunk_id`, and in the same order. 11 IDs were renumbered (listed in the INGEST-002 addendum), all in #08/#09.

Other stat differences are all explained by the 19 drops:
- `heading_only_chunks` 19 → 0.
- Min size 13 → 89: the 19 were the 19 smallest chunks, 13–24 chars.
- p50 1,157 → 1,178 and p90 1,526 → 1,527: the size distribution lost its low end.
- `chunks_under_small_chunk_chars` 79 → 60.
- Code-fence cuts: 24 in both runs; the % moved from 3.19 to 3.27 only because the denominator shrank.
- `duplicates_dropped` 447 → 447: no dropped chunk had an earlier duplicate in its document.
- Per-document counts: each fell by exactly its number of drops.

**G2.** `check_g2.py` gives **11/11 PASS**.

**Step 4.** `check_blueprint_coverage.py` gives **PASS**:
- 80 expected/alternate rows, 54 distinct (source, heading path) pairs. **None has 0 overlapping Arm A chunks** and none is missing from the sections.
- On the old (pre-D3a) chunk file the per-row counts are identical. None of the 19 dropped chunks overlapped a blueprint section, so no blueprint case lost or gained a potential section hit.
- The script can fail. With all #22 chunks removed from a copy of the file, it prints FAIL for `#22 Querying Data` and `#22 Querying Data > Loading a single entity` and exits 1.

**Tests.** `.venv/Scripts/python.exe -m pytest` gives **120 passed**: 114 before plus 6 new. The six new tests:
- `test_heading_only_chunk_of_an_h2_followed_by_its_h3_is_dropped`: with the flag off the chunk is `## Parent`; with it on it is gone.
- `test_sibling_headings_without_body_are_dropped_together`: a merged `## A\n\n## B` chunk is dropped.
- `test_heading_with_body_is_kept`.
- `test_hash_lines_inside_a_code_fence_are_body_not_headings`: a whole fenced block with `# …` lines is kept. (This version could never fail; it was rewritten in the follow-up, see below.)
- `test_a_split_code_piece_of_only_hash_comment_lines_is_kept`: an oversized code block is split by lines so that one piece holds only `# note …` lines, and that piece is kept.
- `test_ids_stay_deterministic_and_contiguous_after_heading_only_drops`: IDs run 0000..n on two runs, with 2 fewer chunks than with the flag off.

**Mutation checks.** I backed up `header_aware.py`, edited it, ran the suite, restored it, and checked with `git diff` that the restore was exact:
- **Drop disabled** (`if False and …`): **5 failed**. The failures were the three drop/ID tests, the changed split test and the Arm A freshness test.
- **Fence-unaware heading detector** (`_HEADING` on every line instead of `find_headings`):
  - The first version of the fence tests still passed. A whole fenced block always contains its ``` lines, so it can never be all-heading.
  - I added `test_a_split_code_piece_of_only_hash_comment_lines_is_kept`. It targets the real risk: a piece cut from inside a long fence. Its first version still had one `echo` line in the comment piece and did not fail, so I made the block longer.
  - Final version: **1 failed**, the new test. Restored: 120 passed.

Before the rebuild, the full suite failed only `test_committed_chunk_and_stats_files_equal_a_fresh_run[A]`, as expected, because the committed file was stale. That shows the freshness test catches a stale Arm A file.

`gitnexus_detect_changes`: see the commit section.

## Unverified / not done
- No retrieval or evaluation was run. None exists yet, and D3a had to be decided without results.
- The tests were not run on Linux; only the owner's Windows 3.13.3 venv was used.

## Deviations and interpretations
1. **Step 0 text not found verbatim.** "waits for OWNER-001 to be verified" was no longer in the ledger: `712f028` had already replaced it with "**Unblocked: all entry conditions met.**". I replaced that sentence with the requested text, "Waits for INGEST-004 (verified) — OWNER-001 verified 2026-09-25", as the prompt intended. I also added "+ INGEST-004" to row 02's *Needs* column so the EVAL-002 entry check sees it. The same change is mirrored in `agents/prompts/README.md` row 02 and logged in `agents/prompts/CHANGELOG.md`. The OWNER-001 report's historical line was left as it is.
2. **One existing test assertion changed.** `test_oversized_section_splits_within_max_at_paragraph_or_sentence_boundaries` expected `len(chunks) == len(long_pieces) + 1`, where the "+ 1" was the fixture's bodiless `# Page` chunk. Under D3a that chunk is dropped by design, so the assertion is now `len(chunks) == len(long_pieces)` with a comment. What the test is about (split within max at paragraph/sentence boundaries) is unchanged.
3. **What "heading lines" means here.** A heading line is an ATX heading (H1–H6) outside a code fence, found with `find_headings`. Blank lines are also ignored. The rule applies to any Arm A span, whether merged or split. For this corpus only single-line chunks matched.
4. **Where the drop happens.** The drop is in `HeaderAwareChunker.spans()`, before the shared `build_chunks`, so the builder and Arm B code are untouched. Heading-only spans are filtered before the D1 duplicate check. That could lower `duplicates_dropped` if a heading-only chunk repeated an earlier one, but in this corpus it did not (447 → 447).
5. **No new stats key.** Adding a "dropped heading-only" count to the stats would also have changed Arm B's stats file. The count (19) is recorded here and in the addendum instead.
6. **Chunk IDs changed.** 11 Arm A IDs in #08/#09 were renumbered. No ground truth uses chunk IDs, since ground truth uses source + heading path (ADR-0003 D8). The only doc that cited an affected ID (`spot-check.md`) got a note.

## Commit / PR
Commit on branch `ingest-004`, pushed; PR into `dev` (link in the final chat report).

`gitnexus_detect_changes`:
- **First run, before the commit, on a stale index.** `scope=all` gave risk medium and 1 process (`Chunk → Trim`). The post-commit hook then reported the index was stale (last indexed `4ef58ed`), so that run is not valid evidence.
- **Re-run after `npx gitnexus analyze`**, as `compare` against `dev`:
  - Risk **medium**: 20 files, 4 affected processes, all of them Arm A header-aware chunk flows reached through `HeaderAwareChunker.spans`: `Chunk → Line_index`, `Chunk → Line_end`, `Spans → _cut`, `Chunk → Trim`.
  - Changed code symbols: `HeaderAwareConfig`, `HeaderAwareChunker.spans`, the new `_heading_only`, the new `check_blueprint_coverage.py`, and tests. `_size` is listed only because its lines moved.
  - No fixed-size, builder, stats or normalizer flow is affected. This matches the intended scope.
- `analyze` rewrote the index counts in `CLAUDE.md`/`AGENTS.md`. Those edits were reverted, not committed.

## Explain it back (from the INGEST-004 final chat report, saved here after verify)
- **Why the drop sits in the Arm A chunker (`spans()`), not in the shared builder.** The shared code that numbers and deduplicates chunks for both arms stays untouched. That is why Arm B can be proven unchanged by hash rather than only claimed.
- **Why it is a config flag, not hard-coded.** ADR-0003 keeps chunk parameters in configuration. The flag also lets one test run both behaviours side by side (on vs off).
- **Why "decided before any results" matters.** Nobody could pick the rule because it made Arm A score better. Heading-only chunks would have given Arm A free section hits, so dropping them makes the A/B comparison fairer.
- **Why no blueprint case lost coverage.** Section spans are flat (an H2's span ends at its first H3). The 19 dropped chunks were "Additional resources" headings and the hub headings of #08/#09, which no blueprint case points at.
- **Alternative not taken.** Letting a small parent merge into its first child would have changed the D3 merge rule and many other chunks, instead of removing only 19 empty ones.

## Follow-up after verify (2026-09-25, "INGEST-004: follow-up fixes from verify")
Prompt: [prompt-log](../../prompt-log/claude-code/INGEST-004-followup.md). Scope: the four non-blocking notes of [INGEST-004-verify](../../reviews/code/INGEST-004-verify.md) (verdict ACCEPT, commit `a142387`).

**Files changed**
| File | Change |
|---|---|
| `src/.../chunking/markdown_structure.py` | New `HeadingLines(text).heading_only(start, end)`: the one D3a definition. It is true when every non-blank line touching the span is a heading line, with headings from `find_headings` over the whole document, so `#` lines inside a fence are text. The diff only adds lines (0 removed). |
| `src/.../chunking/header_aware.py` | The filter uses `HeadingLines`. The private `_heading_only` is removed, and so is the now-unused `find_headings` import. The behaviour is the same (same line range, same heading set). |
| `src/.../chunking/stats.py` | `heading_only_chunks` counts `HeadingLines.heading_only(chunk.char_start, chunk.char_end)` instead of the old "one line starting with `#`" proxy. |
| `tests/unit/infrastructure/test_chunkers.py` | `test_hash_lines_inside_a_code_fence_are_body_not_headings` rewritten: a span strictly between the ``` lines (`# install`, `# run`) must not be heading-only, and `## A` + `## B` must be (control). New `test_heading_only_stat_uses_the_d3a_definition`: a merged `## A\n\n## B` chunk (flag off) gives stat 1, where the old proxy gave 0 because of the newline; the flag-on run gives 0. |
| This report, `agents/prompts/_common.md`, `agents/prompts/CHANGELOG.md`, ledger row 04a, `AI_WORKLOG.md`, prompt-log copy | Items 3–5. |

**Pre-edit impact** (after `npx gitnexus analyze`):
- `chunk_stats`: LOW. 0 indexed callers; the index misses its real callers, `scripts/ingestion/build_chunks.py` and one test.
- `HeaderAwareChunker.spans`: LOW. 1 direct caller (`chunk_with_report`), process `chunk`.
- `_heading_only`: LOW. 1 caller (`spans`).

**Item 1: stat definition.** Rebuilt with `build_chunks.py --arm A` and `--arm B` (same console summary as above: 733 and 859 chunks). SHA-256 after the rebuild, all four equal to the verified versions at `8265d18`:
```
arm-a.jsonl       9c3bcc6c9428d0746c6dddc5509eab79b84d9a2c4ba35bcbcf9dc45f5fcf229f
arm-b.jsonl       2bde1a0e3b42374f03d725f3a7c2b31225c0d6115aa5dc510f49c49a7edb7f2c
stats-arm-a.json  26fab6bfefd59161319a71942ed661ba9161e5f369c85804da0e65730564d3d2
stats-arm-b.json  01395880a947bb46ebfc4b77f51f1e83009dd57d93f2d78510049001cb77fa8b
```
`git diff --exit-code` on `data/processed/chunks`: clean, so the stats files did not change either. Under the D3a definition both arms still count 0 heading-only chunks, the same values the old proxy gave. A scratch run of Arm A with the flag off gives 19 under the new definition, the same 19 as before. Deviation 5 above still holds: Arm B's stats file stayed byte-identical and no key was added.

**Item 2: fence test.** The old version could never fail, because a whole fenced block always contains its ``` lines. The rewrite tests the shared helper on a span inside the fence.

**Mutations** (backup in the scratchpad, then restore; `sha256sum -c` OK for both source files):
- **M1: the old one-line proxy put back in `stats.py`.** Result: **1 failed, 120 passed**. The failing test is `test_heading_only_stat_uses_the_d3a_definition`.
- **M2: the `HeadingLines` heading set made fence-unaware** (ATX regex on every line). Result: **2 failed, 119 passed**. The failing tests are `test_hash_lines_inside_a_code_fence_are_body_not_headings` and `test_a_split_code_piece_of_only_hash_comment_lines_is_kept`.
- **A failed first M1 attempt.** Using `sed` wrote a real newline into the string, which only caused a collection error. The file was restored, and the mutation was redone with a Python replacement. That second run is the one reported.

**Item 3: "no content lost", precisely.** This report never said "no content lost" in those words; it said the remaining 733 chunks are unchanged. The loose form was the owner's check X3 in the verify. I re-measured it with a scratch script: non-whitespace characters on non-heading lines, with headings per `find_headings`. The numbers match review X3.
- **D3a removes 0 content characters in all 24 docs.** Uncovered characters are identical with the flag on and off.
- **Coverage gaps exist in #11, #13, #17 and #23**: 2,739, 108,542, 92,179 and 166,666 characters. They come from the pre-existing **D1 duplicate drop**, which removed 4, 135, 118 and 190 chunks as exact copies of an earlier chunk in the same document. The gaps are identical before and after D3a.
- **Every gap is duplicate text.** Over the Arm A spans before the D1 drop, 0 characters are uncovered in every doc.

**Item 4.** The "Explain it back" bullets are above. `_common.md` step 6 now requires them in the execution report as well as in chat, and a CHANGELOG row records the change.

**Checks (step 5)**
- **`npx gitnexus analyze`** → "Already up to date" (index at `a142387`). The CLAUDE.md/AGENTS.md count edits were reverted.
- **`gitnexus_detect_changes(scope=all)`** → **risk high**: 5 files, 7 processes.
  - Intended: four Arm A flows through `spans` (`Chunk → Line_index`, `Chunk → Line_end`, `Spans → _cut`, `Chunk → Trim`) and `Chunk_stats → _closes`.
  - Not real: `Parse → _closes` (via `split_sections`) and `Normalize → _closes` (via `read_page_frame`). They appear only because the new class was inserted above those functions and moved their lines. The `markdown_structure.py` diff removes 0 lines, so those functions are byte-unchanged.
  - Evidence that no behaviour moved: all four chunk/stats hashes are equal; `check_g2.py` → 11/11 PASS with `g2-check.md` unchanged; `check_blueprint_coverage.py --no-write` → PASS.
- **`.venv/Scripts/python.exe -m pytest`** → `121 passed in 4.32s`: 120 plus 1 new stat test. The fence test was rewritten, not added.

**Unverified:** the tests were not run on Linux.

**Explain it back (follow-up)**
- **One definition, one helper.** The filter and the stat call the same `HeadingLines.heading_only`, so they cannot drift apart again. A stat that disagreed with the filter would have hidden exactly the chunks D3a is about.
- **Why the stat needs whole-document fence state.** A chunk cut from the middle of a long code block has no ``` line of its own. Only the document-level `find_headings` knows its `# …` lines are code.
- **Why a test must be able to fail.** A test that passes even when the code is broken proves nothing. The mutation run (break the code on purpose, watch the test fail, restore) is the proof that the test guards the rule.
- **"0 characters lost by D3a" vs "every character covered".** These are different claims. D3a loses nothing. The gaps in four docs come from D1 dropping duplicate chunks, a separate and older rule.

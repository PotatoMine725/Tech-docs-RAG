# VERIFY INGEST-002

Verifier session, 2026-09-25. Reviewed commit `22c5c50` ("INGEST-002: header-aware + fixed-size chunkers, chunk files, stats, G2 checks", branch `claude/inspiring-cray-fspsdh`, base `dev` `8b38f2f`) against `agents/prompts/04-INGEST-002-chunkers-and-stats.md`, `_common.md`, ADR-0003 D1–D8 and `CLAUDE.md`. Commands ran in a Linux container (`.venv/bin/python`, fresh venv from `requirements.txt` + `pip install -e .` + pytest). Independent checks were scratchpad scripts reading the committed chunk files and `data/processed/documents/normalized.jsonl`; mutation checks edited a source file and restored it with `git checkout --`. `git status --short` was empty after every run.

## A. Acceptance / gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| Do 1 | Arm A: split H2/H3, H4+ in parent, root = page H1 | PASS | `header_aware.py:73-92` uses `document.sections` (H1–H3 spans). Verifier: 752/752 chunks have `heading_path` root == `document_name`, 0 empty paths, 0 paths outside the section inventory. Test `test_h4_stays_inside_its_h3_section`. |
| Do 1 | max 1,600 / min 400, merge small with next sibling under same parent | PASS | `_groups` `header_aware.py:84-90`: merges while < 400 with the next section of same level + same parent path, capped at 1,600. Verifier: Arm A max 1,600. Mutation: sibling check removed → `3 failed, 89 passed`. |
| Do 1 | Oversized → paragraph → sentence; code/tables atomic unless one block > max (code by lines, tables by rows + header) | PASS | `_units` `:128-145`, `_table_units` `:147-153`, `_sentences`/`_pack`/`_cut`. Verifier: Arm A fence cuts 24, **0 of them on fences ≤ 1,600 chars**. Table header repeated in `embed_text` only (owner decision, recorded in `ingestion-spec.md`). |
| Do 1 | 200-char overlap only inside one split section | PASS | Overlap only computed in `_split` `:113-125`. Verifier: 257 overlapping consecutive Arm A pairs, max overlap 200, 0 with different heading paths, 0 starting inside a fence. Mutation: overlap fence guard removed → `3 failed`. |
| Do 2 | Arm B: 1,600 chars, 200 overlap, heading = nearest before start | PASS | `fixed_size.py:416-429` (step 1,400; `section_path_at`). Verifier: size max 1,600, max overlap 200, coverage of non-whitespace text 100% for all 24 docs. |
| Do 3 | D5 embed text (path line + text, links → text; display keeps original) | PASS (1 minor miss) | `chunk_builder.py:362-375`. Verifier: 0 chunks where `embed_text` does not start with `heading_path + "\n\n"`; Arm B: 0 complete links left unstripped. One link in the corpus is missed: `23:header-1600:0085`, URL with two nesting levels of parentheses (`…system-nullable((system-int32))))`); `_LINK` handles one level. Only occurrence in the normalized corpus (verifier regex over all 24 docs → 1). Finding F1, not blocking. |
| Do 3 | D6 fields + ID `{source_id}:{chunker_config}:{index:04d}` | PASS | G2 check rows 2/8; field set = the 12 D6 fields (`CHUNK_FIELDS`, `build_chunks.py`). Verifier: IDs unique in both files. |
| Do 3 | Exact-duplicate drop per document after chunking | PASS | `build_chunks` `:353-361`. Verifier: 0 duplicate `(source_id, content_hash)` pairs remain; Arm A uncovered text only in #11/#13/#17/#23 (the docs with drops); re-running `spans()` without the drop covers 100% of every doc, so all uncovered text is dropped duplicates. |
| Do 3 | Chunker configs in configuration | PASS | `config/chunking.json`; `factory.load_arm`. `git grep -nE "1600|1,600|\b400\b|\b200\b" -- src` → no hits. |
| Do 4 | `build_chunks.py --arm A\|B` → 4 files with required stats | PASS | Re-ran both arms: output identical to the report (A 752, 13/1157/1526/1600, 24 cuts 3.19%, 447 dups; B 859, 207/1600/1600/1600, 387 cuts 45.05%, 0 dups, one-chunk ['09','29']). `sha256sum -c` of the 4 committed files after the re-run → all `OK`. Verifier recomputed min/p50/p90/max (nearest rank), per-doc counts, fence cuts, heading-only (19) and < 400 (A 79, B 4) from the JSONL: all equal the stats files. |
| Do 5 | Tests: size limits, atomic fences/tables, heading paths, overlap, IDs, fence-cut detection, identical field sets | PASS | 29 new tests collected (`--collect-only` → 29), one or more per listed item (names in `test_chunkers.py:44-260`). |
| Do 6 | G2 script → `validation/ingestion/g2-check.md` (identical IDs+hashes; Arm A paths in inventory; slice == text) | PASS | Re-ran `scripts/ingestion/check_g2.py` → `**Overall: PASS** (11/11)`; file content unchanged by the re-run. |
| Do 7 | Spot-check 5 chunks per arm incl. #13/#17/#23 and #09/#22/#29 | PASS | `validation/ingestion/spot-check.md`: A covers #13, #09, #22; B covers #17, #29, #13, #22. All 10 quoted sizes and heading paths match the chunk file (verifier script). |
| Do not | No embedding/indexing; D2–D7 parameters unchanged | PASS | No `chromadb`/`genai` import in the diff; config values = ADR-0003 (1,600/400/200; 1,600/200). |
| Gate G2 | master-plan §G2 items | PASS | Items 1–3 reproduced above. |

## B. Tests

`.venv/bin/python -m pytest -q` → `92 passed in 4.13s`.
The tests assert behaviour, not just execution: two verifier mutations (sibling check removed; overlap-in-fence guard removed) each gave `3 failed, 89 passed`. `test_committed_chunk_and_stats_files_equal_a_fresh_run` guards the data files. No assertion-free tests or mock-only assertions found.

## C. Claims vs reality

| Claim (report / worklog) | Result | Evidence |
|---|---|---|
| All stats numbers (table "Results") | PASS | Recomputed from JSONL, see Do 4. |
| Duplicates per doc #11: 4, #13: 135, #17: 118, #23: 190 | PASS | `stats-arm-a.json`, reproduced by the re-run. |
| "24 cuts, all from code blocks > 1,600" | PASS | Verifier: 0 cuts of fences ≤ 1,600. |
| "src diff: 599 insertions, 0 deletions" | PASS | `git diff --shortstat 8b38f2f 22c5c50 -- src` → `7 files changed, 599 insertions(+)`. |
| "63 before + 29 new = 92" | PASS | 29 collected; 92 passed. |
| Mutation claims (dup drop → 1 fail, sibling → 2 fails, overlap → 2 fails) | PARTLY | Verifier ran sibling and overlap mutations with its own edits → 3 fails each (different edits, so counts differ; the claim "tests can fail" holds). Dup-drop mutation not re-run. |
| GitNexus `detect-changes` (21 files, 14 flows, high) | UNVERIFIED | `npx gitnexus detect-changes` printed only its banner in this container (no index); not re-checkable here. |
| Spot-check sizes/paths | PASS | 10/10 match. |

## D. Project rules

| Rule | Result | Evidence |
|---|---|---|
| Layer imports | PASS | `grep -rnE "chromadb\|google\.genai\|PySide6" src/knowledge_assistant/{core,application}` → none; structure tests green. |
| Model names only in config | PASS | No `gemini-` string in the commit. |
| No API key | PASS | `git grep -nE "AIza[0-9A-Za-z_-]{20,}"` → none. |
| Corpus untouched | PASS | `corpus/manifest.json` `sha256_lf` recomputed for 24 files → 0 mismatches; `git diff --stat 8b38f2f 22c5c50 -- corpus data/evaluation data/processed/documents` → empty. |
| Excluded 14/19/24/27 unused | PASS | 0 chunks with those `source_id`s in either file; 24 docs in `corpus/sources`. |
| Eval set unchanged / not used for tuning | PASS | `data/evaluation` untouched; no `eval-freeze-v1` tag exists yet (EVAL-002 not started); chunker parameters come from ADR-0003, not from eval questions. |

## E. Scope

No unrequested functionality beyond disclosed extras (extra stats fields, committed chunk files, `fenced_ranges` helper). Decisions: the table-header rule was asked (AskUserQuestion, recorded). The ≤ 1,600 cap on merging and "sibling = same level + same parent" are interpretations of D3 / the prompt's own "next sibling under same parent" wording, disclosed as Deviations 2–3 and left open for the owner. PASS.

## F. Quality spot-read

- `HeaderAwareChunker._split` (`header_aware.py:96-126`): piece budget `max − overlap` after the first piece plus `room = min(overlap, max − (content_end − previous_end))` keeps every piece ≤ 1,600 (confirmed on all 752 chunks). Heading-at-end carry-over is bounded by the same budget. OK.
- `_Layout.overlap_start` (`:216-231`): word boundary, table row start, never inside a fence; falls back to no overlap when the start would reach `previous_end`. OK.
- `build_chunks` (`chunk_builder.py:343-380`): IDs numbered after the drop → contiguous; empty spans skipped; `:` in config rejected. OK.
- `_LINK` (`chunk_builder.py:287`): one nesting level of parentheses in URLs → F1.
- No swallowed exceptions or silent fallbacks found.

## G. Explain-it-back

The report has no "Explain it back" section (the chat report is not visible to the verifier). The report's Deviations 1–9 were checked against the code and are accurate.

## Findings

- **F1 (minor, non-blocking):** one Markdown link not reduced to its text in `embed_text` of `23:header-1600:0085` (URL with nested `((…))`). Single occurrence; affects only embedding text of one chunk. Fix optional (extend `_LINK` to two nesting levels, regenerate chunk files).
- **Open owner item (carried):** 19 heading-only Arm A chunks from the D3 sibling-only merge (disclosed, needs an ADR-0003 amendment to change).
- **Not re-checkable:** GitNexus detect-changes output; Windows `.venv/Scripts/python.exe` run.

## Verdict

**ACCEPT** — 0 FAIL, 1 UNVERIFIED (GitNexus output). G2 passes.

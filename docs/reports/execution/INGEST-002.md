# INGEST-002 execution report

**Date:** 2026-09-25 · **Prompt:** [`agents/prompts/04-INGEST-002-chunkers-and-stats.md`](../../prompt-log/claude-code/INGEST-002.md) · **Agent:** Claude Code (cloud session, Linux) · **Branch:** `claude/inspiring-cray-fspsdh` (from `dev` `8b38f2f`)

## Entry condition
Ledger: INGEST-001 (03) `verified` (re-verify ACCEPT). No earlier INGEST-002 work existed (`data/processed/chunks/` held only `.gitkeep`).

## Files changed
| File | Change |
|---|---|
| `config/chunking.json` (new) | Arm A `header-1600` (max 1,600 / min 400 / overlap 200), Arm B `fixed-1600` (1,600 / 200), `stats_small_chunk_chars` 400. The arm name is the `chunker_config` in chunk IDs |
| `src/.../infrastructure/chunking/header_aware.py` (new) | Arm A: sections → sibling merge → block split (paragraph / code / table / heading) → overlap |
| `src/.../infrastructure/chunking/fixed_size.py` (new) | Arm B: 1,600-char windows every 1,400 chars; heading path of the section containing the start |
| `src/.../infrastructure/chunking/chunk_builder.py` (new) | Shared: `Span` → `DocumentChunk` (D5 embed text with links stripped outside code, D6 ID, SHA-256 of `display_text`, per-document duplicate drop before numbering) |
| `src/.../infrastructure/chunking/stats.py` (new) | D8 stats: counts, min/p50/p90/max (nearest rank), code-fence cuts, 1-chunk docs, duplicates, small and heading-only chunks |
| `src/.../infrastructure/chunking/factory.py` (new) | Builds an arm from `config/chunking.json` |
| `src/.../infrastructure/chunking/markdown_structure.py` | New `fenced_ranges()` only (existing functions unchanged) |
| `src/.../application/ingestion/build_chunks.py` (new) | `from_record` (inverse of `to_record`), `load_normalized_documents`, `chunk_to_record` (exactly the D6 fields) |
| `scripts/ingestion/build_chunks.py` (new) | `--arm A\|B` → `data/processed/chunks/arm-{a,b}.jsonl`, `stats-arm-{a,b}.json` |
| `scripts/ingestion/check_g2.py` (new) | G2 checks → `validation/ingestion/g2-check.md`, exit 1 on failure |
| `data/processed/chunks/*` (new, generated) | arm-a.jsonl 1,935,574 B (752 chunks), arm-b.jsonl 3,095,461 B (859 chunks), 2 stats files |
| `tests/unit/infrastructure/test_chunkers.py` (new) | 25 tests |
| `tests/unit/application/test_build_chunks.py` (new) | 4 tests (incl. committed chunk/stats files == fresh run) |
| `validation/ingestion/g2-check.md`, `validation/ingestion/spot-check.md` (new) | G2 output; 5 chunks per arm read by hand |
| `docs/specs/ingestion-spec.md`, `docs/architecture/ingestion-architecture.md`, `docs/architecture/data-model.md` | As-implemented rules, owner decision, open item |
| `docs/plans/*`, `AI_WORKLOG.md`, `docs/prompt-log/claude-code/INGEST-002.md` | Status, gate, log |

## Results (from the stats files)
| | Arm A `header-1600` | Arm B `fixed-1600` |
|---|---|---|
| Chunks | 752 | 859 |
| Size min / p50 / p90 / max | 13 / 1,157 / 1,526 / 1,600 | 207 / 1,600 / 1,600 / 1,600 |
| Chunks cutting a code fence | 24 (3.19%) — all from the code blocks > 1,600 chars (checked: 0 cuts of blocks ≤ 1,600) | 387 (45.05%) |
| Docs with 1 chunk | none | #09, #29 |
| Duplicates dropped | 447 (#11: 4, #13: 135, #17: 118, #23: 190) | 0 |
| Chunks < 400 chars / heading-only | 79 / 19 | 4 / 0 |

## Commands run (real output)
```
$ .venv/bin/python scripts/ingestion/build_chunks.py --arm A
arm A (header-1600): 752 chunks over 24 documents
size min/p50/p90/max: 13/1157/1526/1600
chunks cutting a code fence: 24 (3.19%)
duplicates dropped: 447; documents with one chunk: []
$ .venv/bin/python scripts/ingestion/build_chunks.py --arm B
arm B (fixed-1600): 859 chunks over 24 documents
size min/p50/p90/max: 207/1600/1600/1600
chunks cutting a code fence: 387 (45.05%)
duplicates dropped: 0; documents with one chunk: ['09', '29']

# both arms built twice: sha256sum of all 4 output files identical (BYTE-IDENTICAL)

$ .venv/bin/python scripts/ingestion/check_g2.py
**Overall: PASS** (11/11)

$ .venv/bin/python -m pytest -q
92 passed in 4.14s        (63 before this task + 29 new)

$ npx -y gitnexus detect-changes -s compare -b 8b38f2f   (after git add; base = dev before this task)
Changes: 21 files, 145 symbols
Affected processes: 14
Risk level: high
  All 14 flows start at the new Chunk entry points (HeaderAwareChunker / FixedSizeChunker / chunk_stats);
  pre-existing code appears only as unchanged callees (fence_mask → _closes). src diff vs base: 599 insertions, 0 deletions.
```
**Pre-edit impact:** no existing symbol was edited (only a new function appended to `markdown_structure.py`), so no `gitnexus impact` run was needed.

**Tests can fail (mutation checks, files restored from a backup and compared with `cmp`):** duplicate drop disabled → 1 failed; sibling check in the merge removed → 2 failed; overlap allowed to start inside a fence → 2 failed; blocks split above 500 chars instead of 1,600 → 1 failed (the first version of that test used a 1,343-char block and did **not** fail; the block was made 1,400–1,600 chars, see AI_WORKLOG).

## G2
All 11 checks pass (`validation/ingestion/g2-check.md`): two fresh runs = committed file (IDs + hashes) for both arms; ID format and contiguous numbering; `normalized_text[char_start:char_end] == display_text` for every chunk of both arms; 24 docs per arm; every Arm A heading path is in the section inventory; no Arm A chunk > 1,600; identical field sets. The inventory half of the heading-path item was already met by INGEST-001. Spot-check done (`validation/ingestion/spot-check.md`).

## Unverified / not done
- Not run on Windows (`.venv/Scripts/python.exe`); Linux `.venv/bin/python` only.
- GitNexus MCP tools unavailable; CLI used. `analyze` rewrote `CLAUDE.md`/`AGENTS.md` counts and created `.claude/skills/gitnexus-*`; both reverted/deleted, not committed.
- Spot-check covers 10 chunks of 1,611; everything else is checked only by the automated G2 checks.

## Deviations and interpretations
1. **Table split (owner decision 2026-09-25, AskUserQuestion):** D4 says repeat the header row; G2 says the chunk text is the exact slice. The header row is repeated in `embed_text` only. Recorded in `ingestion-spec.md`.
2. D3 merge reads "next section under the same parent" as the immediately following *sibling* (same parent path and level), and merges only while the result stays ≤ 1,600 (otherwise the next section's pieces would carry the small section's heading path). Effect: 19 heading-only chunks (an H2 directly followed by H3s). **Open for the owner** (ADR-0003 amendment needed to change it).
3. Oversized blocks are cut into sub-blocks of ≤ 1,400 chars (max − overlap) so a 200-char overlap fits; blocks ≤ 1,600 are never cut. When an atomic block of 1,401–1,600 chars starts a later piece, the overlap is shortened to keep the piece ≤ 1,600.
4. Overlap starts at a word boundary, at a row start inside a table, and never inside a code fence (it is dropped if the previous piece ends in a fence).
5. Heading lines are their own blocks; a heading at the end of a piece moves to the next piece.
6. `display_text` is trimmed of leading/trailing whitespace (offsets adjusted), for both arms.
7. The chunk file stores `heading_path` as the " > "-joined string (no heading contains " > "; checked over the 636 inventory rows).
8. Extra stats beyond the prompt: `chunks_under_small_chunk_chars`, `heading_only_chunks`, per-document duplicates.
9. Chunk files are committed (like `normalized.jsonl`); a test checks they equal a fresh run.

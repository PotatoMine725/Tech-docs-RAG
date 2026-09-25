# INGEST-002 — Header-aware + fixed-size chunkers, chunk files, stats (gate G2)

Read `agents/prompts/_common.md` first and follow it.
Read: ADR-0003 D1–D8 (the spec you implement — do not change parameters), INGEST-001 report.
Entry: INGEST-001 done.

## Do
1. `infrastructure/chunking/header_aware.py` (Arm A): split on H2/H3 (H4+ stays in parent), heading path root = page's own H1, max 1,600 / min 400 chars, merge small sections with next sibling under same parent, oversized → paragraph → sentence; code fences and tables atomic unless a single block > max (code by lines, tables by rows repeating header); 200-char overlap only inside one split section.
2. `infrastructure/chunking/fixed_size.py` (Arm B): 1,600 chars, 200 overlap, heading path = nearest heading before chunk start.
3. Both: D5 contextual header (`embed_text` = heading path line + text with `[text](url)` → `text`; `display_text` keeps original), D6 metadata and ID `{source_id}:{chunker_config}:{index:04d}`, exact-duplicate drop per document after chunking. Chunker configs in configuration, not hard-coded.
4. Script `scripts/ingestion/build_chunks.py --arm A|B` → `data/processed/chunks/arm-a.jsonl`, `arm-b.jsonl`, and `stats-arm-a.json`, `stats-arm-b.json`: chunk count total/per doc, size min/p50/p90/max, % chunks cutting a code fence, # docs with 1 chunk, duplicates dropped.
5. Tests (offline, small hand-made Markdown fixtures): size limits, atomic fences/tables, heading paths, overlap only where allowed, IDs deterministic, code fence cut detection, both arms emit identical field sets.
6. **G2 checks** (script, output saved to `validation/ingestion/g2-check.md`): second run gives identical IDs + hashes; every Arm A heading path exists in the section inventory; `char_start/char_end` slice of normalized text == chunk text.
7. Spot-check 5 chunks per arm (include one from #13/#17/#23 and one tiny doc #09/#22/#29) → `validation/ingestion/spot-check.md` with what you saw.

## Do not
Embed or index. Change D2–D7 parameters (that needs a new ADR).

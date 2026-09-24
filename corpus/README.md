# Corpus

**Purpose:** the curated document collection the Knowledge Assistant answers from.

| Item | Count |
|---|---|
| Original documents | 28 |
| Accepted | 24 |
| Excluded | 4 |

**Numbering note:** IDs run 1-29, but **#25 never existed** (skipped during Markdown conversion; confirmed by the project owner 2026-09-24). The original prompt's "29 / 25" figures therefore correspond to 28 / 24 in practice. `corpus/links.txt` still lists a #25 entry; it is not a corpus document.

- Accepted location: `corpus/sources/`
- Excluded location: `corpus/excluded/` - IDs **14, 19, 24, 27** (intentional gaps in `sources/`; never renumber).
- Provenance: `corpus/links.txt` (URL per original ID).
- Numbering and filenames preserved; contents unmodified (SHA-256 verified; see `docs/snapshots/corpus/`).

**Rationale (high level):** excluded documents were deliberately dropped from the accepted set; detailed per-document rationale: TBD.

**Source of truth:** files in `corpus/sources/` are read-only originals. No manifest exists yet (TBD).

The current dataset consists of 24 accepted Markdown documents (the original brief said 25; #25 never existed), but the ingestion architecture is designed to support additional document formats (PDF, HTML, others via parser adapters).

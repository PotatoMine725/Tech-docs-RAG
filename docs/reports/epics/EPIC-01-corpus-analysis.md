# EPIC-01 Corpus analysis — report

**Date:** 2026-09-24 (planned for 25 Sep, done a day early) · **Task:** CORPUS-001 · **Plan:** [master-plan.md](../../plans/master-plan.md#epic-01-corpus-analysis)

## What was built

| File | What it is |
|---|---|
| `src/knowledge_assistant/infrastructure/chunking/markdown_structure.py` | Shared heading rules: ATX headings outside code fences; sections at H1–H3 with H4+ inside the parent (ADR-0003 D2); reads the export wrapper (wrapper title, `Source:` URL, page H1). EPIC-02 chunkers will reuse it. |
| `scripts/utilities/build_corpus_inventory.py` | Builds the two data files below. Deterministic: a re-run on unchanged sources gives byte-identical output (checked). |
| `corpus/manifest.json` | 24 accepted documents plus the excluded IDs (by file name only) and the missing #25. Location = OD-2, decided by the owner. |
| `data/processed/documents/section-inventory.jsonl` | 636 sections: heading path, variant number, raw line range, size. Line numbers and sizes refer to the raw file text with LF line endings, not to normalized text (that is EPIC-02). |
| `docs/knowledge/domain/corpus-topic-map.md` | Topic groups, size classes, overlaps, low-value sections. |
| `README.md` (root, draft) | Dataset description required by the brief. |
| `tests/unit/infrastructure/test_markdown_structure.py`, `tests/unit/test_corpus_inventory.py` | 13 heading-rule tests + 6 data tests. |

Rebuild: `.venv/Scripts/python.exe scripts/utilities/build_corpus_inventory.py`.

## Numbers (from the script output, 2026-09-24)

- 24 documents, 1,197,929 characters, 636 H1–H3 sections (after each page's own H1).
- Largest: #23 381,188 · #17 258,392 · #13 238,805 characters = 73.3% of all text.
- Smallest: #09 1,126 · #29 1,728 · #22 1,945 · #18 2,846.
- Sections per document: 2 (#18) to 147 (#13).
- Most-repeated H2 heading path per document (version variants): #13 8×, #17 6×, #23 4×, #11 4×, #10 2×, #12 2×.
- Section size (all 636): p25 488, median 1,124, p75 2,554, p90 4,425, max 17,122 characters.
- After dropping sections whose text exactly repeats an earlier section of the same document: 450 sections, 856,308 characters.

## Cross-check against ADR-0003 (measured earlier in a separate session)

| Measure | ADR-0003 / handoff | This inventory | Match |
|---|---|---|---|
| Total size | ~1.20 M | 1,197,929 | yes |
| Huge docs share | ~74% | 73.3% | yes |
| Largest H2 repeats | #13 8×, #17 6×, #23 4× | same | yes |
| Headings per doc | 3 to 160 | 3 (#18) to 160 (#13), counting both H1s | yes |
| Docs with H4 | #02, #12, #13, #23 | same | yes |
| Size after removing repeated sections | ~0.86 M | 856,308 | yes |
| Max section | ~17,100 | 17,122 | yes |
| Sections after removing repeats | 498 | 450 | **no, unexplained** |
| Section size p25 / median | ~330 / ~990 | 441 / 1,141 (deduplicated) | **no** |

Heading detection matches the earlier measurement exactly: headings per document, where the H4s are, and the repeat counts all agree. What differs is how the earlier session counted deduplicated sections. Four variants were tried: with and without the wrapper section, dedup by text or by heading path plus text, splitting at H4. They gave 450–484 sections, not 498. The earlier measurement code was not saved, so the difference stays open. It does not change any decision: ADR-0003 limits were set from the overall distribution, which is similar. From now on this inventory is the reproducible source.

## Findings for later epics

- **Wrapper:** every file starts with `# <title> - Microsoft Learn` (or `| Microsoft Learn`), a `Source:` URL, one or two `---` lines, and often "Access to this page requires authorization…" lines before the page's own H1. That is 116–444 characters per file (`preamble_chars` in the manifest). This is D1 normalization work for EPIC-02.
- **#29** has a YAML front-matter block (`title:`, `author:`, `ms.date:`, `uid:` …) before its H1. It is boilerplate for D1. The inventory ignores it (it sits before the page H1).
- **#15** is a Microsoft Q&A thread, not official documentation (H2s "0 additional answers", "Your answer").
- **Formatting:** no setext (underlined) headings; code fences are only ```; no fence is indented 4+ spaces; no headings end in `#` (so "C#" titles are safe; also covered by a test); no BOM.
- **Line endings:** git stores the sources with LF; this Windows checkout has CRLF (`core.autocrlf=true`). The manifest therefore hashes LF text (`sha256_lf`). The test rebuilds CRLF bytes to check the older snapshot hashes, so checksum tests pass on any checkout. No `.gitattributes` was added.
- **Heading text is stored exactly as written.** 16 headings contain inline code (e.g. "`bool`, `char`, and `string`"); none contain links. EPIC-02 should keep heading paths as written and clean only the embedded text (ADR-0003 D5), so paths keep matching this inventory and the ground truth.
- **Low-value sections** ("Additional resources", "See also", "Related links", "Stay in touch") appear in most documents. EVAL-001/002 should not target them.

## Exit gate G1

- [x] Manifest has exactly 24 IDs, none of 14/19/24/27, no #25 (`test_manifest_lists_exactly_the_24_accepted_sources`, `test_manifest_records_excluded_ids_and_the_missing_25`).
- [x] Checksums match `docs/snapshots/corpus/`, so the sources are unmodified (`test_sources_are_unchanged_since_the_premigration_snapshot`, `test_manifest_hashes_match_the_files_on_disk`).
- [x] Section inventory covers all 24 docs and matches a fresh computation (`test_inventory_matches_a_fresh_computation_for_all_24_documents`).
- [x] README dataset-description draft exists (`README.md`).
- [x] `.venv/Scripts/python.exe -m pytest`: 27 passed at G1; 28 after the OD-3 test.

**OD-3 closed (2026-09-24):** the owner stated that documents 14, 19, 24 and 27 are index pages, links to other pages with no useful content. The reason is recorded per ID in `build_corpus_inventory.py` (so it lands in `corpus/manifest.json`) and in both READMEs. Test `test_every_excluded_document_has_a_reason` guards it. The excluded files were not opened. `.venv/Scripts/python.exe -m pytest`: 28 passed.

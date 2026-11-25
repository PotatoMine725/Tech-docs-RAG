# ADR-0008 Corpus 2: multi-domain study material (EN, VI, mixed) for benchmark v2

Date: 2026-11-25
Status: Accepted (owner decisions 2026-11-23: target users are students; multi-domain EN / VI / mixed documents, some
with images, no audio/video; >= 100 questions in v1 + v2; ground truth only from extracted text. Owner decisions
2026-11-25: file dispositions below, `.pptx` enabled, short quotes may be committed).
Refines: ADR-0002 (formats), ADR-0003 D5/D6 (heading-path citations). Plan Phase 0 item 3 of
`docs/plans/local-rag-upgrade-plan.md`. Numbered 0008 because 0007 is taken by the hybrid-search ADR (PR #28).

## Decision
- **Corpus 1 is unchanged.** `corpus/`, IDs `1`-`29` (no #25), 24 accepted, 4 excluded: CLAUDE.md rule 4 still holds.
- **Location.** `corpus2/manifest.json` is committed. `corpus2/incoming/` (raw files as given by the owner) and
  `corpus2/converted/` (text and section inventory) are git-ignored. A file can be committed only if the owner sets
  `redistributable: true` in the manifest; all are `false` today.
- **IDs `C2-NN`.** The prefix keeps them disjoint from corpus 1's bare numbers. They were given once, at intake
  (2026-11-25), in the order of the file names in `incoming/` (case-insensitive, as listed to the owner). They are never
  renumbered or reused; an excluded file keeps its ID; a new file gets the next free number (`convert_corpus2.py`).
- **Manifest, no text.** Per file: id, file name, status (`accepted` / `excluded` + reason), title, field, language
  (`en` / `vi` / `mixed`, rule in the manifest), redistributable, sha256, bytes, pages, image_count, has_images,
  chars, headings, image_only_facts. Measured fields come from `scripts/corpus2/convert_corpus2.py`; title, field,
  language, status and image facts are curated by hand. Pages: PDF page count, PPTX slide count, the `Pages` value
  Word saved in DOCX (`null` if absent), `null` for `.md` / `.txt`.
- **Conversion** uses the existing MarkItDown adapter, now with `.pptx` (owner, 2026-11-25; the `pptx` extra). The
  text is not normalized (the ADR-0003 D1 normalizer is specific to corpus 1's web exports).
- **Intake result (32 files): 24 accepted, 8 excluded.** Excluded: C2-02, C2-20, C2-23 (scanned PDFs, no text
  layer) and C2-14 (images only), all with OCR scope TBD; C2-09 (`.ppt`), C2-12 and C2-17 (`.doc`), which have no
  converter; C2-31 (`.txt` duplicate of C2-30 with extraction noise). C2-04 (`.docx`) and C2-22 (`.md`) are two
  versions of one report, both kept on purpose as a near-duplicate pair.
- **Sections.** H1-H3 headings as in corpus 1. Most PDFs have no Markdown headings. For those documents, and for
  text before the first heading, the section inventory has one span with heading path `""` (whole document).
- **Images.** Ground truth comes only from the extracted text. Facts seen only inside images are listed in
  `image_only_facts` and counted. They are never used as expected answers (OCR scope TBD).
- **Evidence quotes** (at most 300 characters, exact substrings of the converted text) are committed in the v2
  question files (owner OK, 2026-11-25). They are taken from prose lines only, not from table cells where the PDF
  extraction split words. Lines that identify the patient in C2-24 (a hospital case record) are never quoted.
- **No index is built here.** Whether corpus 2 shares a collection with corpus 1 or gets its own is **TBD**; it is
  decided in the indexing step, after `eval-freeze-v2`.

## Consequences
- In heading-less documents, section_hit is effectively document-level (heading path `""`). Span metrics are based
  on the evidence quotes and stay precise. Results for corpus 2 must be reported apart from corpus 1, not pooled
  without saying so.
- The v2 validator reads `corpus2/converted/sections.jsonl`, so validation needs a local conversion run first. The
  manifest pins both ends: `sha256` (raw file) and `converted_sha256` (converted text), plus the converter library
  versions. The validator fails if the local text differs; `convert_corpus2.py --check` fails if the converter no
  longer reproduces it (e.g. after a library upgrade), so frozen quotes cannot drift silently.
- `application/evaluation/metrics/spans.py` indexes sections from the parser's section list, which has no
  whole-document span for heading-less documents. Span metrics for corpus 2 therefore need the corpus-2 inventory
  (`sections.jsonl` rule above) in the indexing step: **TBD** there. Chunk heading paths already join to `""`.
- Words split across table cells in slide PDFs (C2-03, C2-05, C2-06, C2-32) and parts of C2-13 and C2-25 make keyword
  matching weaker on those documents. This is a property of the extraction, recorded here, not fixed.
- C2-08 (1549 combining marks) and C2-07 (26) are stored in decomposed Unicode (NFD); questions are typed in NFC,
  so exact keyword matching on those documents misses unless text is NFC-normalized. Quotes copy the stored form.
  Normalizing at ingestion is **DECISION REQUIRED** (indexing step); it would change chunk text, not this manifest.
- Image inspection (sampled, 2026-11-25) found 47 image-only facts in 17 of 18 documents with images; C2-26 keeps
  almost all formulas as WMF images and C2-27 has nearly all explanations in screenshots.

## Open items for the indexing step (owner, 2026-11-25; not done here)
1. **PDF lines starting with `#`.** MarkItDown keeps them, so the chunker reads them as Markdown headings (C2-21:
   heading paths such as `number Please answer # 7.`, cited by Q2-EVAL-048 / 049). Escape such lines in PDF
   conversion so they stay text. This changes C2-21's converted text, so its `converted_sha256` and the affected
   heading paths must be updated together.
2. **Heading-less and single-heading documents** (C2-07, whose only heading `*1.1.* Hoàn cảnh quốc tế…` is a
   conversion artifact, and most PDFs). There section_hit ≈ source_hit, so evidence_hit is the main corpus-2 metric;
   section-level results on these documents are reported as source-level.
3. **NFD Vietnamese text** (C2-07, C2-08). NFC normalization at ingestion is still **DECISION REQUIRED**. It affects
   keyword (FTS) search, which misses NFC queries on NFD text, and evidence matching, which must normalize both sides
   or keep copying the stored form.

## Resolutions (owner, 2026-11-25; indexing step)
1. **`#` lines:** PDF conversion escapes heading-shaped lines as `\#` (PDF only). Only C2-21 changed; its heading
   paths in Q2-EVAL-048 / 049 / 058 become `""`. See the erratum
   [`eval-v2.1-erratum.md`](../../reviews/evaluation/eval-v2.1-erratum.md) (tag `eval-freeze-v2.1`).
2. **Metric:** evidence_hit is the main corpus-2 metric; section_hit is reported but ≈ source_hit on heading-less
   documents.
3. **NFC:** all text is normalized to Unicode NFC at ingestion (indexed text and questions), after conversion, so the
   converted text and its `converted_sha256` stay as pinned. Evidence matching compares both sides in NFC.
   Correction to the note above: **C2-25** is NFD as well (found at indexing), besides C2-07 and C2-08.

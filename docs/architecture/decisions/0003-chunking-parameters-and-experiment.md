# ADR-0003 Chunking parameters and chunking experiment

Date: 2026-09-24
Status: Accepted (user decision, D1-D9). Amended 2026-09-25: D3a (owner decision, INGEST-004).
Refines: ADR-0002. Context: `docs/plans/chunking-consultation-handoff.md`.

## Measured corpus facts behind this decision (2026-09-24, `corpus/sources/`, regex outside code fences, approximate)
- #13, #17, #23 repeat the same article once per ASP.NET Core version (largest H2 repeat count: #13 8x, #17 6x, #23 4x; #10/#11/#12 2-4x, small). Variants carry no version heading; the first block of #23 says "This isn't the latest version" while its `Source:` URL says `aspnetcore-10.0`, so variants MUST NOT be labelled with guessed versions.
- Removing exactly identical H1-H3 sections reduces the corpus from ~1.20 M to ~0.86 M chars (~28%). After that, #13/#17/#23 are still ~63% of the text.
- H1-H3 section lengths after that deduplication (498 sections, chars): p25 ~330, median ~990, p75 ~2,400, p90 ~4,300, max ~17,100.
- Pages carry boilerplate: wrapper `# <title> - Microsoft Learn` + `Source:` + `---`, "Access to this page requires authorization", "This isn't the latest version...", "no longer supported", author bylines, version-selector lines.

## Decisions
**D1 Normalization (shared by both experiment arms).** An in-memory step between parsing and chunking. Sources are never edited.
- Move the wrapper H1 title and the `Source:` URL into metadata. Drop the wrapper H1, `Source:` and `---` lines.
- Remove known boilerplate lines.
- Keep all version variants and call them variant 1..n. Never infer version labels.
- After chunking, drop chunks whose normalized text hash exactly matches an earlier chunk of the same document.
- Near-duplicates are kept. A per-section/per-source result cap at retrieval is a possible later addition (not baseline).

**D2 Split levels.** Split on H2 and H3. H4+ stays inside its parent H3 section. Heading path root = the page's own H1 (the second H1), e.g. `Routing in ASP.NET Core > Route constraints > Regular expressions in constraints`.

**D3 Size unit and limits.** Characters (independent of the undecided embedding model; ~4 chars/token for English prose, fewer for code).
- Max chunk 1,600 chars (~400 tokens). Min 400 chars.
- Sections under the min merge with the next section under the same parent. The merged chunk records the first section's heading path.

**D3a Heading-only chunks, Arm A (amendment, owner decision 2026-09-25, INGEST-004).** After chunking, Arm A drops every chunk whose display text is empty once heading lines (outside code fences) and blank lines are removed. The drop happens before chunk IDs are assigned, so IDs stay contiguous (D6). Arm B is unchanged. Config: `drop_heading_only: true` on Arm A in `config/chunking.json`.
- *Why:* D3 merges a small section only with its next sibling, so an H2 followed directly by its H3 child stays alone as a chunk that holds only the heading line. INGEST-002 produced 19 such Arm A chunks.
  - They add no content, because every child chunk already carries the heading path in its D5 header.
  - They can crowd top-k.
  - Their span lies inside the expected section, so section hit@5 would count them as hits. That is a false hit in Arm A's favour.
- *When:* decided before any index, retrieval run or evaluation result existed. No result informed it.
- *Effect (INGEST-004):* Arm A goes from 752 to 733 chunks and `heading_only_chunks` from 19 to 0. The other 733 chunks are unchanged except for renumbered IDs. Every blueprint expected/alternate section still has at least one overlapping Arm A chunk (`validation/ingestion/blueprint-coverage-arm-a.md`).

**D4 Oversized sections.**
- Split at paragraph boundaries first, then at sentence boundaries.
- Fenced code blocks and tables are atomic. They are split only when a single block exceeds the max: code by lines, tables by rows, repeating the header row.
- 200-char overlap only between consecutive pieces of the same split section.

**D5 Contextual chunk header (both arms).**
- Embedded text = heading path line + chunk text. Fixed-size chunks use the nearest heading preceding the chunk start.
- In embedded text, Markdown links `[text](url)` become `text`. Display text keeps the original.
- The heading path is also stored separately as the citation location (`location_type = "heading"`).

**D6 Chunk metadata and ID.**
- ID: `{source_id}:{chunker_config}:{index:04d}`. Deterministic, because heading paths are not unique within a doc.
- Fields: `chunk_id`, `source_id`, `document_name`, `source_url`, `heading_path`, `location_type`, `char_start`, `char_end` (offsets into normalized text), `display_text`, `embed_text`, `content_hash`, `chunker_config`.

**D7 Experiment (2 arms).**
- Arm A: header-aware, D2-D5, max 1,600 chars.
- Arm B: fixed-size, 1,600 chars, 200 overlap, with the same D1 normalization and the same D5 header.
- One ChromaDB collection per arm. Held constant across arms: embedding model, distance metric, top-k = 5, prompt, Gemini model, question set.
- Optional follow-up experiment: fixed-size 1,200 vs 3,200 chars (~300 vs 800 tokens).

**D8 Metrics.**
- Retrieval: source hit@5, section hit@5 (retrieved chunk char span overlaps the expected section span; any variant counts), MRR.
- Answer quality: rubric.
- Citation quality: the cited chunk contains the supporting evidence.
- Latency: per stage (embed query, retrieve, generate).
- Descriptive per arm: chunk count, size distribution, % chunks cutting a code fence.
- Ground truth: expected `source_id` + heading path, written before indexes are built.

## Expected failure modes (for failure analysis)
- Mixed-version answers (#13/#17/#23).
- Near-duplicate chunks filling top-k.
- Fixed-size chunks separating code from its explanation.
- Link-list sections (#09, #08) retrieved as noise.
- Tiny docs (#09, #22, #29) as a single chunk.
- Large docs outranking small docs. The question set must also cover small docs.

## D9 Query language: English and Vietnamese (accepted 2026-09-24)
The brief does not state the user's language; the user chose to support both. The corpus is English. Chunking operates on the corpus, so D1-D4 and D6 are unaffected. Consequences:
- **D5:** heading-path prefix stays English, since it describes English text. No change.
- **D7:** the embedding model MUST be multilingual (cross-lingual retrieval, VI query -> EN chunk). This constrains the undecided embedding provider. The question language mix MUST be identical across arms.
- **D8:** each evaluation case gets a `language` field. Retrieval and answer metrics are reported per language as well as overall. A parallel subset (same question in EN and VI, same ground truth source) isolates the cross-lingual effect.
- **Outside chunking (generation/citation specs):** answer in the question's language. Citation excerpts stay in the original English. The "insufficient information" message is given in the question's language.
- **Optional:** translate/rewrite VI queries to English before retrieval (brief bonus "query rewriting"). This is a candidate second experiment and not part of the baseline.

## Consequences
- The normalization step is new pipeline code in infrastructure and must be deterministic and unit-tested offline.
- Both chunkers must emit identical metadata so evaluation code is arm-agnostic.
- Parameter values are initial choices justified by the measured distribution, not by retrieval results. Any change requires a new ADR or an amendment with evidence.

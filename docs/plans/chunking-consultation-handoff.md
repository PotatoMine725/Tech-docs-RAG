# Handoff: chunking strategy consultation

Date: 2026-09-24. Purpose: give another agent full context to advise on chunking. Nothing here is implemented. Numbers below were measured from `corpus/sources/` on 2026-09-24; no retrieval results exist.

## 1. Project context
Educational, individual, non-commercial grounded-RAG desktop assistant (Python, PySide6, ChromaDB, Gemini via `google-genai`, pytest). Pipeline: Documents -> Parsing -> Chunking -> Embedding -> ChromaDB -> Retrieval -> Gemini -> Answer + Citation. Layers: presentation -> application -> core <- infrastructure; chunkers live in infrastructure behind `core/interfaces/chunker.py` (Protocol). Core models: Document, ParsedDocument, DocumentChunk, Citation (source_id, document_name, location_type, location, excerpt).

## 2. Graded requirements that constrain chunking (`docs/specs/assignment-requirements.md`)
- >= 20 docs, >= 30 evaluation questions (question, ground truth, expected source, generated answer, result).
- Report answer quality, retrieval quality, citation quality, latency, with measurement method.
- Compare >= 2 approaches (brief suggests chunk size 300 vs 800) and prove the difference with evidence; failure analysis is emphasised.
- Answers grounded with citations; must say when information is insufficient. Citations must not assume page numbers.

## 3. Already decided (ADR-0002, accepted by user)
- MarkItDown (MIT, Microsoft) converts non-Markdown formats (PDF/HTML/txt) to Markdown, infrastructure adapter only. Python 3.13 compatibility unverified.
- Baseline: header-aware chunking with size limits (merge small, split oversized, fallback for header-less docs). Heading path = citation location.
- Comparison approach: fixed-size chunking.

## 4. Open questions for the consultant
1. Heading levels to split on (H2 only? H2+H3?) and how to handle each doc's duplicated H1 (see 5).
2. Min/max chunk size (chars vs tokens), overlap, and how to split oversized sections (paragraph, sentence, code-block-aware).
3. Whether to prepend the heading path / document title to chunk text before embedding (contextual chunk headers) and whether to store it separately for citations.
4. Handling of code blocks, tables and link-only lists (see 5): keep atomic, drop, or summarise?
5. Fixed-size comparison values: 300 vs 800 (units?), overlap, and whether to make the experiment a clean 2x2 or keep to 2 arms so the difference is attributable.
6. Chunk metadata schema and deterministic chunk IDs (e.g. source_id + heading path + index).
7. How chunk design interacts with the embedding model choice (max input tokens; provider TBD) and Gemini context budget / top-k.
8. What per-chunking retrieval metrics separate the two arms (hit@k / MRR against expected source, plus heading-level hit?) and how to avoid confounding from ChromaDB/embedding settings.
9. Impact of the huge docs (see 5) on the index balance and retrieval bias.

## 5. Corpus facts relevant to chunking (24 accepted Markdown docs, all English, Microsoft Learn / GitHub docs about C#, .NET, ASP.NET Core)
- Total ~1.2 M chars; median 13.9 K; min 1.1 K (#09); max 381 K (#23). Three docs are huge: #23 (381 K), #17 (258 K), #13 (239 K) = ~74% of all text. A per-document balance problem is likely.
- Every doc starts with `# <title> - Microsoft Learn`, a `Source: <url>` line and `---`, then a second H1 with the page's own title. So each doc has two H1s; the first is a wrapper, not content structure. Header count per doc: 3 to 160.
- Every doc has headings (none header-less). Depth mostly H2/H3; H4 rare (#02, #12, #13, #23).
- Code-heavy: fenced code blocks per doc range 0 to 195 (e.g. #23: 195, #17: 174, #13: 151). Code blocks are likely a large part of section size.
- Tables: markdown tables are rare except #23 (218 table lines), #17 (56), #10 (16), #16 (12), #02 (10), #29 (5).
- Some pages are mostly link lists / navigation (e.g. #09 language reference, #08), where sections contain little prose.
- Small docs (#09 1.1 K, #22 1.9 K, #29 1.7 K, #18 2.8 K) would be a single chunk or a few; merging rules matter.
- Heading duplicates inside a doc exist (e.g. #09 has "C# language reference" as H1 and H2), so heading paths alone may not be unique; IDs need an index.
- Stats were computed by simple line regex outside code fences; they are approximate.

## 6. Constraints and non-goals
- Do not renumber/edit corpus sources. No fabricated results. Setup-phase: no chunker code written.
- No embedding provider or Gemini model chosen; no chunk size chosen.
- Reranking, hybrid search are optional bonus, not baseline.

## 7. Suggested deliverable from the consultant
A recommendation covering: split rules, size limits with justification, overlap, metadata schema and chunk ID scheme, the exact 2-arm experiment (parameters, metrics, how to measure), and expected failure modes to look for in failure analysis.

## 8. Files to read
`CLAUDE.md`, `docs/specs/assignment-requirements.md`, `docs/specs/ingestion-spec.md`, `docs/architecture/decisions/0002-markitdown-and-header-chunking.md`, `docs/architecture/ingestion-architecture.md`, `src/knowledge_assistant/core/interfaces/chunker.py`, `src/knowledge_assistant/core/models/__init__.py`, sample docs in `corpus/sources/` (#09 small, #13 or #23 large).

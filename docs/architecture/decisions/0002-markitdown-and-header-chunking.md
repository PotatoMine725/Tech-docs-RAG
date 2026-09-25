# ADR-0002 MarkItDown parsing and header-based chunking

Date: 2026-09-24
Status: Accepted (user decision). MarkItDown adapter implemented in INGEST-003 (2026-09-25); chunkers in INGEST-002.

## Decision
1. Use Microsoft **MarkItDown** (https://github.com/microsoft/markitdown) as the converter for non-Markdown inputs (PDF, HTML, txt, others). It lives only in `infrastructure/parsing/` as an adapter behind `ParserRegistry`, returning a normalized `ParsedDocument` whose text is Markdown.
   - *Amendment (INGEST-003, 2026-09-25; AI decision while the owner was away, pending owner review):* "normalized" here means Markdown text with LF line endings and computed sections. Converted files are **not** passed through the ADR-0003 D1 normalizer, which is specific to the web-exported corpus pages (see `docs/specs/ingestion-spec.md` § Parsing).
2. Baseline chunking strategy is **header-aware chunking**: split on Markdown headings, keep the heading path as chunk location, apply size limits (merge small sections, split oversized ones), and fall back to paragraph/size splitting for documents without headings.
3. **Fixed-size chunking** (size TBD, e.g. 300 vs 800) is the comparison approach for the >= 2-approach experiment. The experiment design is defined in `docs/specs/evaluation-spec.md` and the plan for EPIC-06.

## Rationale
- Supports multi-format ingestion without changing core/application.
- Heading path gives citations that never assume page numbers.
- Gives a baseline vs alternative pair that can be measured on the 30+ evaluation questions.

## Consequences / risks
- Conversion quality varies by format (tables, scanned PDFs, PDFs with few headings). Spot-check needed before trusting any converted format.
- Licence: MarkItDown is MIT-licensed (confirmed by user). This project itself has no licence: individual, non-commercial, educational only. Python 3.13: verified in INGEST-003 (V-2) — `markitdown` 0.1.8 installs and converts PDF/HTML/DOCX/txt on Python 3.13.12 (Linux). Added to `pyproject.toml` and `requirements.txt` as `markitdown[pdf,docx]>=0.1.8,<0.2`.
- Core and application MUST NOT import `markitdown`; boundary tests must cover it when the adapter is added.
- The current 24 corpus files are already Markdown; MarkItDown is not required for them.

## Still open
None. Embedding model: ADR-0004. Size limits, overlap and experiment parameters: decided in ADR-0003.

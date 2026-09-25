# INGEST-003 — MarkItDown adapter for non-Markdown inputs (cuttable, OD-15)

Read `agents/prompts/_common.md` first and follow it. Read ADR-0002.
Only run if on schedule (master-plan §6 cut line).

## Do
1. V-2: install `markitdown` in `.venv`, confirm it imports and converts on the venv's Python version; record the version.
2. Adapter `infrastructure/parsing/markitdown_parser.py` behind `ParserRegistry` for `.pdf`, `.html`, `.docx`, `.txt` → `ParsedDocument` with Markdown text; the rest of the pipeline is unchanged (this proves format independence).
3. Tests with tiny fixtures generated in the test itself (no binary files committed if avoidable). `markitdown` imported only in that one module (add a structure test).
4. Resolve OD-6 in `ingestion-architecture.md`: delete or redirect the `html_parser.py` / `pdf_parser.py` stubs.

## Do not
Add new documents to the corpus.

# INGEST-001 — Core models, Markdown parser, normalization

Read `agents/prompts/_common.md` first and follow it.
Read: ADR-0002, ADR-0003 (D1, D5, D6), `docs/specs/ingestion-spec.md`, `docs/architecture/ingestion-architecture.md`, `docs/architecture/data-model.md`, `docs/knowledge/domain/corpus-topic-map.md`, `src/knowledge_assistant/infrastructure/chunking/markdown_structure.py` (reuse it, do not duplicate heading detection).
Can run in parallel with EVAL-001/002 (no Gemini, no index).

## Do
1. **Core models** (`core/models/`, plain dataclasses, no third-party imports): `Document`, `ParsedDocument` (normalized Markdown text + metadata: source_id, document_name, source_url, variant info), `DocumentChunk` with exactly the D6 fields, `Citation` (`location_type="heading"`). Frozen/immutable where sensible.
2. **Markdown parser** in `infrastructure/parsing/markdown_parser.py`, registered in `ParserRegistry` by extension.
3. **Normalizer** (infrastructure, deterministic, in-memory; sources never written):
   - `\r\n` → `\n` FIRST (offsets and hashes depend on it);
   - move wrapper H1 + `Source:` URL into metadata, drop wrapper H1 / `Source:` / `---`;
   - remove known boilerplate lines (list them in one constant, sourced from the EPIC-01 report);
   - keep version variants (variant 1..n), never infer version labels.
4. **Ingestion use case** (application layer, depends on core interfaces only): load accepted docs from `corpus/manifest.json` → parse → normalize → write `data/processed/documents/normalized.jsonl` (one line per doc: id, metadata, text, sha256). Script: `scripts/ingestion/normalize_corpus.py`.
5. Tests (offline): EOL handling, wrapper removal, boilerplate removal, YAML front-matter in #29, determinism (two runs → identical hashes), excluded docs never loaded, no infrastructure import in core/application.
6. Check: every heading path in the section inventory can be located in the normalized text (character span) — needed later for section hit@5. Report any that cannot.

## Do not
Chunk, embed, or call Gemini.

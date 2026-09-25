# INGEST-001 execution report

**Date:** 2026-09-25 · **Prompt:** [`agents/prompts/03-INGEST-001-models-parser-normalization.md`](../../prompt-log/claude-code/INGEST-001.md) · **Agent:** Claude Code (cloud session, Linux) · **Branch:** `claude/sleepy-wright-vj962y`

## Entry condition
Ledger: HOUSE-001 `verified`; REORIENT-001 `verified` (re-verify `8104105`, after the fixes in `47b9c4e`). The ledger's extra "00R verified" prerequisite is met. No earlier INGEST-001 work existed.

## Files changed
| File | Change |
|---|---|
| `src/knowledge_assistant/core/models/__init__.py` | `Document` (+ `path`, `source_url`), new `SectionSpan`, `ParsedDocument` (text + metadata + sections, `normalized` flag), `DocumentChunk` with exactly the D6 fields, `Citation.location_type` defaults to `"heading"` (moved last so it can have a default), `HEADING_PATH_SEPARATOR` |
| `src/knowledge_assistant/core/interfaces/parser.py` | `parse(document: Document)` instead of `parse(path: str)`: the parser needs the source ID, and it is a corpus concept, not a file-name rule |
| `src/knowledge_assistant/core/interfaces/normalizer.py` (new) | `DocumentNormalizer` protocol, so the use case depends on core only |
| `src/knowledge_assistant/core/exceptions/__init__.py` | `DocumentParseError` (unreadable file, missing page H1, unknown preamble line) |
| `src/knowledge_assistant/infrastructure/parsing/markdown_parser.py` | `MarkdownParser`: reads UTF-8 with `newline=""` (line endings untouched) |
| `src/knowledge_assistant/infrastructure/parsing/registry.py` | `default_registry()`: `.md`, `.markdown` → `MarkdownParser` |
| `src/knowledge_assistant/infrastructure/parsing/markdown_normalizer.py` (new) | D1 normalizer; `BOILERPLATE_LINES` constant; `section_spans()`; `content_sha256()` |
| `src/knowledge_assistant/infrastructure/chunking/markdown_structure.py` | New `fence_mask()` (same fence rules as `find_headings`; existing functions unchanged) |
| `src/knowledge_assistant/application/ingestion/normalize_corpus.py` (new) | `load_accepted_documents`, `NormalizeCorpus`, `to_record`, `write_jsonl`, `unlocated_inventory_sections` |
| `scripts/ingestion/normalize_corpus.py` (new) | Wires the pipeline, writes `normalized.jsonl`, runs the step-6 heading-path check (exit 1 on any miss) |
| `data/processed/documents/normalized.jsonl` (new, generated) | 24 lines, 1,393,800 bytes |
| `tests/unit/infrastructure/test_markdown_normalizer.py` (new) | 11 tests |
| `tests/unit/application/test_normalize_corpus.py` (new) | 7 tests |
| `docs/architecture/data-model.md`, `docs/architecture/ingestion-architecture.md`, `docs/specs/ingestion-spec.md` | Implemented fields and flow |
| `docs/plans/master-plan.md`, `docs/plans/epics/EPIC-02-ingestion-pipeline.md`, `docs/plans/task-ledger.md`, `AI_WORKLOG.md`, `docs/prompt-log/claude-code/INGEST-001.md` | Status, gate note, log |

## Normalization rules (what is removed, and why it is safe)
- **Preamble** (everything before the page's own H1): wrapper H1 and `Source:` URL go to metadata (`wrapper_title`, `source_url`); `---`, the "Note" label, both "Access to this page requires authorization…" lines and #29's YAML front matter are dropped. Every preamble line must match one of these patterns, otherwise `DocumentParseError`. All 24 documents pass.
- **Body boilerplate** (outside code fences only), sourced from the EPIC-01 report and ADR-0003's measured facts: access notes; "This isn't the latest version of this article." and "This version of ASP.NET Core is no longer supported." (#10–#13, #23); author bylines `By [Name](url)…` (#03, #10, #13 ×5, #17, #23); the page footer `- Last updated on` + date (19 docs). An admonition label (`Note`/`Warning`/…) goes only when the line it introduces is removed; the `---` goes only when it introduces the footer. Real notes stay (tested).
- **Blank lines:** runs collapse to one outside code fences.
- **Kept:** version variants (numbered 1..n by repeated heading path, no version labels), tab-selector link lists, "Additional resources" sections, everything inside code fences.
- **Safety check:** all 107 EVAL-001 evidence quotes are still found (whitespace-normalized) inside a span of their own heading path in the normalized text (`test_every_evidence_quote_survives_normalization_inside_its_section`).

## Commands run (real output)
```
$ .venv/bin/python scripts/ingestion/normalize_corpus.py
24 documents, 1,186,335 normalized chars (raw LF 1,197,929)
wrote data/processed/documents/normalized.jsonl
inventory heading paths located: 636/636

$ .venv/bin/python -m pytest -q
63 passed in 4.69s        (45 before this task + 18 new)

$ npx -y gitnexus impact <symbol> --direction upstream   (before editing)
ParsedDocument, DocumentChunk, Citation, Document: risk LOW (3 direct)
DocumentParser: risk LOW (1 direct)
```
**Tests can fail (mutation check, reverted afterwards):** without the CRLF step, 1 normalizer test fails; without the boilerplate removal, 3 tests fail; without the excluded-document guard, 1 use-case test fails.

## Step 6: heading paths → character spans
636/636 section-inventory rows (source_id, heading path, variant) have a span in the normalized text whose text starts with that heading line. None unlocated.

## Unverified / not done
- Commands use `.venv/bin/python` (Linux cloud container), not `.venv/Scripts/python.exe`. Not run on Windows.
- The GitNexus MCP tools are unavailable in this session; the `npx gitnexus` CLI was used instead. Its index is local (`.gitnexus/`, git-excluded); the tool-rewritten symbol counts in `CLAUDE.md`/`AGENTS.md` and the generated `.claude/skills/gitnexus-*` folders were reverted, not committed.
- No manual spot-check of the normalized text beyond #10, #23 and #29 (head and tail read).

## Deviations from the prompt
1. `DocumentParser.parse` now takes a `Document`, not a path (see table). The only callers are the new use case and tests (GitNexus impact LOW).
2. `Citation` field order changed so `location_type` can default to `"heading"`. No code constructed `Citation` before this task.
3. A `DocumentNormalizer` core interface was added (not named in the prompt) so the application layer stays on core interfaces only.
4. `normalized.jsonl` is committed, like `section-inventory.jsonl` next to it; a test checks it equals a fresh run.
5. The evidence-quote survival test goes beyond the prompt's test list; it guards the frozen ground truth against normalization.

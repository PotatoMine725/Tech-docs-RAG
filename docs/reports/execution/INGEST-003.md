# INGEST-003 execution report

**Date:** 2026-09-25 · **Prompt:** [`agents/prompts/05-INGEST-003-markitdown-optional.md`](../../prompt-log/claude-code/INGEST-003.md) · **Agent:** Claude Code (cloud session, Linux, owner away — authorized to run the next prompts) · **Branch:** `claude/workflows-ingest-002-review-svn2dq` (from `dev` `443582a`)

## Entry condition
Ledger: INGEST-001 (03) `verified`. Schedule: target Sat 26, run Fri 25 → not behind, so the cut line (OD-15) does not apply. No earlier INGEST-003 work existed (`html_parser.py` / `pdf_parser.py` were one-line SETUP-001 skeletons).

## Files changed
| File | Change |
|---|---|
| `src/.../infrastructure/parsing/markitdown_parser.py` (new) | `MarkItDownParser` for `.pdf .html .htm .docx .txt`; lazy `markitdown` import; signature check for `.pdf`/`.docx`; `DocumentParseError` on any failure; raw `ParsedDocument` with LF text, title, `section_spans` |
| `src/.../infrastructure/parsing/registry.py` | `default_registry()` registers one shared `MarkItDownParser` for `MARKITDOWN_EXTENSIONS` (Markdown entries unchanged) |
| `src/.../infrastructure/parsing/html_parser.py`, `pdf_parser.py` | Deleted (OD-6, see Decisions) |
| `tests/unit/infrastructure/test_markitdown_parser.py` (new) | 11 tests; PDF and DOCX fixtures are built as bytes inside the test (no binary files committed) |
| `tests/unit/test_project_structure.py` | `markitdown` added to the forbidden imports of core/application; new `test_markitdown_is_imported_only_by_its_adapter` |
| `pyproject.toml`, `requirements.txt` | `markitdown[pdf,docx]>=0.1.8,<0.2` (the `pdf`/`docx` extras pull `pdfminer.six` and `mammoth`; without them MarkItDown cannot read those formats) |
| `docs/architecture/ingestion-architecture.md`, `docs/specs/ingestion-spec.md`, `docs/architecture/tech-stack.md`, ADR-0002 status/consequences | As implemented, OD-6, V-2 |
| `docs/plans/master-plan.md`, `EPIC-02`, `task-ledger.md`, `AI_WORKLOG.md`, prompt log | Status. Also corrected two stale lines left by the INGEST-002 verify: G2 "not yet verified" → verified, EPIC-02 status "awaiting 99-VERIFY" → verified |

## Do items
1. **V-2** — answered: yes. `markitdown` **0.1.8** installed with `pip install "markitdown[pdf,docx]"` into a fresh **Python 3.13.12** venv (`python3.13 -m venv .venv313`, Linux); converts all four fixture formats (tests below). The owner's Windows venv (3.13.3) was not available: run `.venv/Scripts/pip install -r requirements.txt` there before the next test run, or the new tests fail with `ModuleNotFoundError`.
2. **Adapter behind `ParserRegistry`** — done. "Rest of the pipeline unchanged": `test_converted_formats_chunk_like_the_same_markdown` (both arms) shows an HTML file and a DOCX file give exactly the same chunks (heading path, `display_text`, `location_type`) as the equivalent `.md`; no chunker or core code changed.
3. **Tests** — 11 new + 1 structure test; fixtures generated in the test. `markitdown` import guarded by the structure test.
4. **OD-6** — resolved: stubs deleted, one adapter (see Decisions).

## Commands run (real output)
```
$ .venv313/bin/pip show markitdown | head -2
Name: markitdown
Version: 0.1.8
$ .venv313/bin/python --version
Python 3.13.12
$ .venv313/bin/python -m pytest -q
104 passed in 6.03s
$ .venv313/bin/python -m pytest -q tests/unit/infrastructure/test_markitdown_parser.py tests/unit/test_project_structure.py
18 passed in 1.08s
$ .venv313/bin/python scripts/ingestion/normalize_corpus.py   # then build_chunks.py --arm A / --arm B, check_g2.py
wrote data/processed/documents/normalized.jsonl
inventory heading paths located: 636/636
**Overall: PASS** (11/11)
$ git status --short data validation        # (empty: outputs byte-identical)
$ sha256sum data/processed/documents/normalized.jsonl
a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95
$ npx -y gitnexus impact default_registry|ParserRegistry|FORBIDDEN_CORE --direction upstream
impactedCount 0, risk UNKNOWN (no resolved callers) for all three; text search: default_registry is called by
scripts/ingestion/normalize_corpus.py and tests/unit/infrastructure/test_markdown_normalizer.py -> LOW
$ npx -y gitnexus detect-changes -s compare -b 443582a   (staged)
Changes: 15 files, 19 symbols / Affected processes: 0 / Risk level: low
```
The GitNexus index was built before the new files existed, so the adapter's own symbols are not in the detect-changes list.

Mutation checks (each restored from a scratch backup, full suite re-run after: 104 passed):
| Mutation | Result |
|---|---|
| `import markitdown` in a new `core/_mut.py` | structure tests: 2 failed |
| `.docx` signature check removed | adapter tests: 1 failed (broken `.docx` returned its bytes as text) |
| eager `import markitdown` at module top | adapter tests: 1 failed (lazy-import test) |

## Decisions taken without the owner (owner away; flagged in the autonomous-session note)
1. **OD-6:** one shared `MarkItDownParser` registered for all MarkItDown extensions; `pdf_parser.py` / `html_parser.py` deleted. Alternative: keep per-format files that delegate — rejected, they would be empty pass-throughs (MarkItDown already dispatches by format). `base.py` (skeleton) kept: not in scope.
2. **No D1 normalizer for converted files.** `MarkdownNormalizer` requires the web-export frame (wrapper H1 + page H1) and raised `expected a wrapper H1 followed by the page's own H1` on all four converted fixtures. The adapter unifies line endings and computes `sections` itself. Alternative: a generic normalizer step — not needed for the corpus (all Markdown) and would be new design.
3. **Signature check for `.pdf`/`.docx`.** Found by the first test run: MarkItDown returned a damaged `.docx` (`b"not a zip file"`) as plain text, a silent fallback forbidden by `ingestion-spec.md` ("MUST NOT silently drop"/clear error).
4. **Extras `[pdf,docx]` and version pin `>=0.1.8,<0.2`.** MarkItDown 0.1.x is pre-1.0; the pin keeps API changes out.

## Deviations / unverified
- V-2 checked on Linux Python 3.13.12, not on the owner's Windows 3.13.3 venv (unverified there).
- MarkItDown depends on `magika`, which pulls in `onnxruntime` (CLAUDE.md rule 2: "ML/ONNX only when a concrete decision requires"). It is a transitive dependency of the tool ADR-0002 chose, not an ML feature; imported lazily so the Markdown pipeline never loads it. Flagged for the owner.
- Conversion quality of real-world PDFs/tables not checked: there are no non-Markdown inputs in the corpus (the prompt forbids adding documents). `ingestion-spec.md` still requires a spot-check before a converted format is used in evaluation.
- Headingless input (PDF, txt) gets chunks with an empty heading path and `location_type="heading"`; the `position` location type is not produced. Not needed for the corpus; open for a later task.
- `requirements.txt` still lacks PySide6 (pre-existing gap, EPIC-07).
- A separate `.venv313/` was used so the concurrent EVAL-001 verifier's `.venv` (3.11) was not disturbed; it is git-excluded locally.

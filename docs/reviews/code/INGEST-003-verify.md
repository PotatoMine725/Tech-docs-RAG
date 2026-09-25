# VERIFY INGEST-003

Verifier session, 2026-09-25. Reviewed commit `7e51ad0` ("INGEST-003: MarkItDown adapter for PDF/HTML/DOCX/txt, V-2, OD-6", branch `claude/workflows-ingest-002-review-svn2dq`, base `dev` `443582a`) against `agents/prompts/05-INGEST-003-markitdown-optional.md`, `_common.md`, ADR-0002 and `CLAUDE.md`. Verifier branch `verify-ingest-003` from `13121ce` (session head; the only later commit, `15654a1`, is the EVAL-001 re-verify and touches no INGEST-003 file).

Environment: **Linux container, not Windows.** `.venv/Scripts/python.exe` does not exist here; commands used `/home/user/Tech-docs-RAG/.venv313/bin/python` (Python 3.13.12, `markitdown` 0.1.8) and, for a second run of the suite, `/home/user/Tech-docs-RAG/.venv/bin/python` (Python 3.11.15, `markitdown` 0.1.8). pytest's `pythonpath = ["src"]` puts the worktree's `src` first; the scripts insert it themselves. Edge-case probes were scratchpad scripts that assert `knowledge_assistant.__file__` is inside the worktree. Mutation checks backed up the edited files to the scratchpad and restored them from there; `git status --short --untracked-files=all` was empty after every restore and after the final suite run (`104 passed`).

## A. Acceptance / gate items

| # | Item | Result | Evidence |
|---|---|---|---|
| Entry | Run only if on schedule (master-plan §6 cut line); INGEST-001 `verified` | PASS | Ledger row 03 = `verified`. Master-plan §6 lists the MarkItDown adapter as cut item 3 only "if behind schedule"; target Sat 26, run Fri 25. |
| Do 1 | V-2: `markitdown` installs, imports and converts on the venv's Python; version recorded | PASS (Linux) / UNVERIFIED (Windows) | `.venv313/bin/pip show markitdown` → `Version: 0.1.8`; `python --version` → `Python 3.13.12`; the 11 adapter tests (real HTML/DOCX/PDF/txt conversions) pass on 3.13.12 and on 3.11.15. The prompt says "in `.venv`": the owner's Windows 3.13.3 venv was not available to the task or to this verifier. Disclosed. |
| Do 2 | Adapter `infrastructure/parsing/markitdown_parser.py` behind `ParserRegistry` for `.pdf .html .docx .txt` → `ParsedDocument` with Markdown text | PASS | `registry.py:20-31` registers one `MarkItDownParser` for `MARKITDOWN_EXTENSIONS` (`markitdown_parser.py:16`, adds `.htm`). Test `test_registry_sends_every_markitdown_format_to_one_adapter` (upper-case lookup too). Verifier probe: `upper.DOCX` → same Markdown as the lower-case fixture. |
| Do 2 | "Rest of the pipeline unchanged" (format independence) | PASS | `git diff --stat 443582a 7e51ad0 -- data validation corpus config scripts src/knowledge_assistant/core src/knowledge_assistant/application src/knowledge_assistant/infrastructure/chunking` → empty. `test_converted_formats_chunk_like_the_same_markdown[A/B]`: HTML and DOCX give the same `(heading_path, display_text, location_type)` as the `.md`, and every `display_text` equals its text slice. |
| Do 3 | Tests with tiny fixtures generated in the test; no binary files committed | PASS | PDF/DOCX built as bytes in `_pdf` / `_docx` (`test_markitdown_parser.py:30-90`); `git ls-files '*.pdf' '*.docx' '*.html' '*.htm'` → nothing. |
| Do 3 | `markitdown` imported only in that one module (structure test) | PASS | `test_markitdown_is_imported_only_by_its_adapter` + `markitdown` in `FORBIDDEN_CORE`. Mutation (new `application/_mut_verify.py` with `from markitdown import MarkItDown` + `infrastructure/_mut_verify.py` with `import markitdown`) → `2 failed, 5 passed`. `grep -rnE "chromadb\|google\.genai\|PySide6\|markitdown" src/knowledge_assistant/{core,application}` → none. |
| Do 4 | Resolve OD-6 in `ingestion-architecture.md`: delete or redirect the stubs | PASS | Both one-line stubs deleted; `ingestion-architecture.md:7` records the decision, reason and "AI decision while the owner was away"; master-plan OD-6 row updated. `git grep -nE "html_parser\|pdf_parser"` → only the prompt, the architecture note and the report. |
| Do not | No new documents in the corpus | PASS | `corpus/` not in the diff; 24 files in `corpus/sources`, manifest checksums match (D). |
| _common | Dependency in BOTH `pyproject.toml` and `requirements.txt`, with a reason | PASS | `markitdown[pdf,docx]>=0.1.8,<0.2` in both; reason in the report (extras pull `pdfminer.six` 20260107 and `mammoth` 1.11.0, confirmed by `pip show`; `pip check` → no broken requirements). |
| _common | Prompt log, report, worklog, plan/epic/ledger updates | PASS | All present in the commit. |

## B. Tests

`.venv313/bin/python -m pytest -q` → `104 passed in 6.51s`; `.venv/bin/python -m pytest -q` (3.11) → `104 passed in 6.21s`. `pytest -q tests/unit/infrastructure/test_markitdown_parser.py tests/unit/test_project_structure.py` → `18 passed` (11 adapter + 7 structure; 92 before + 11 + 1 = 104).

Verifier mutations of `markitdown_parser.py` (each restored from the scratch backup):

| Mutation | Result | Reading |
|---|---|---|
| Signature check disabled (`if False:`) | `2 failed, 9 passed` (`broken.docx`, `broken.pdf`) | Test guards the check. |
| Converter title ignored (`document_name=document.name`) | `1 failed` (HTML title test) | OK. |
| Eager `import markitdown` at module top | **`11 passed`** in the worktree; with `PYTHONPATH=<worktree>/src` → `1 failed` (`test_markitdown_is_imported_lazily`) | **FAIL (B1).** The test starts `subprocess.run([sys.executable, "-c", ...])` (`:167`) without passing pytest's `pythonpath`, so the child imports whatever `knowledge_assistant` is installed: the editable install points at `/home/user/Tech-docs-RAG/src` (main checkout), not the code under test. Confirmed: `python -c "import knowledge_assistant; print(knowledge_assistant.__file__)"` → `/home/user/Tech-docs-RAG/src/...`. In a worktree, or with no editable install (then `check=True` errors), the test does not test this checkout. |
| CRLF unification removed (`text = result.text_content`) | `11 passed` | Minor (B2): `test_txt_keeps_text_and_unifies_line_endings` cannot fail on the adapter's own line (`:40`); MarkItDown already returns LF for that input. The assertion is correct but tests MarkItDown, not the adapter. |

Other tests assert behaviour (exact Markdown text, heading paths, `sections == section_spans(text)`, `normalized is False`, error message contains `#91`). No assertion-free or mock-only tests.

## C. Claims vs reality

| Claim (report / worklog / commit) | Result | Evidence |
|---|---|---|
| `markitdown` 0.1.8, Python 3.13.12 | PASS | `pip show`, `--version` (A, Do 1). |
| `104 passed`, `18 passed` | PASS | Re-run (B). |
| "11 tests" (report) / "12 offline tests" (commit, worklog) | PASS | 11 collected in the new file + 1 new structure test = 12. |
| `normalize_corpus.py` → 636/636; `build_chunks.py --arm A/B`; `check_g2.py` → `**Overall: PASS** (11/11)`; outputs byte-identical | PASS | Verifier re-ran all four: `inventory heading paths located: 636/636`; A `13/1157/1526/1600`, 24 fence cuts (3.19%), 447 dups; B `207/1600/1600/1600`, 387 cuts (45.05%), one-chunk `['09','29']`; `**Overall: PASS** (11/11)`. `sha256sum -c` of the 7 files in `data/processed/{documents/normalized.jsonl,chunks/*}` and `validation/ingestion/*` taken before the run → all `OK`; `git status --short --ignored data validation` → empty. |
| `normalized.jsonl` sha256 `a6db2f26…9ae95` | PASS | `sha256sum` → `a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95`. |
| D1 normalizer "raised `expected a wrapper H1 followed by the page's own H1` on all four converted fixtures" | PASS | Verifier script: HTML, DOCX, PDF, txt → `DocumentParseError #90: expected a wrapper H1 followed by the page's own H1` (4/4). |
| First test run: MarkItDown returned a damaged `.docx` as plain text | PASS | Signature-check mutation → the `broken.docx` case no longer raises. |
| Mutation table (3 rows) | PASS | Verifier mutations reproduce rows 1 and 2 (row 2 with the `.pdf` check also removed → 2 fails instead of 1). Row 3 holds only when the editable install points at the same checkout (B1). |
| `gitnexus impact default_registry` → `impactedCount 0`, UNKNOWN; text search finds 2 callers | PASS | `npx -y gitnexus impact default_registry --direction upstream` → `"impactedCount": 0, "risk": "UNKNOWN"`; `git grep default_registry` → `scripts/ingestion/normalize_corpus.py`, `tests/unit/infrastructure/test_markdown_normalizer.py` (+ the new test). |
| `gitnexus detect-changes -s compare -b 443582a` → 15 files, 19 symbols, 0 processes, risk low | PARTLY | Verifier, tree at `7e51ad0`: `Changes: 19 files, 24 symbols / Affected processes: 0 / Risk level: low`. Processes and risk reproduced; the counts differ (the report ran it "staged", plausibly before the 4 bookkeeping files existed; not provable). |
| "Any conversion failure raises `DocumentParseError`" (`ingestion-architecture.md:20`) | **FAIL** | See F1/F2: empty or textless inputs and some mismatched `.pdf`/`.docx` inputs return text without an error. |
| `onnxruntime` arrives via MarkItDown's `magika` (flagged as a CLAUDE.md rule-2 concern) | PASS, framing incomplete | `pip show onnxruntime` → `Required-by: chromadb, magika` in both venvs: it was already a transitive dependency of the locked ChromaDB stack before INGEST-003. |
| Decisions "flagged in the autonomous-session note" | PARTLY | `docs/plans/session-handoff-2026-09-25-autonomous.md` "For the owner" still reads `_Filled in at the end of the run._` at `13121ce`. The decisions are recorded in the report, `ingestion-spec.md`, `ingestion-architecture.md`, master-plan OD-6, the ledger row and the worklog. |
| Windows: without `pip install` the new tests "fail with `ModuleNotFoundError`" | Minor inaccuracy | The lazy import sits inside the `try` (`:34-39`), so conversions fail with `DocumentParseError: ... No module named 'markitdown'`; only the direct `markitdown` import would give `ModuleNotFoundError`. |

## D. Project rules

| Rule | Result | Evidence |
|---|---|---|
| Layer imports | PASS | Structure tests green; grep in core/application → none (A, Do 3). |
| MarkItDown only in `infrastructure/parsing/` (ADR-0002, CLAUDE.md rule 2) | PASS | `grep -rn markitdown src` (non-cache) → only `markitdown_parser.py` (import at `:52`) and the registry's import of the adapter module. |
| Model names only in config | PASS | The only `gemini-` hit in the diff is an unchanged context line of `tech-stack.md`. |
| No API key | PASS | `git grep -nE "AIza[0-9A-Za-z_-]{20,}"` → none. |
| Corpus untouched | PASS | `corpus/manifest.json` `sha256_lf` recomputed for 24 files → 0 mismatches. |
| Excluded 14/19/24/27 unused | PASS | `corpus/excluded` = `['14','19','24','27']`; chunk files unchanged. |
| Eval set unchanged / not used for tuning | PASS | `data/` not in the diff; no `eval-freeze-v1` tag exists yet (`git tag -l` → empty). |

## E. Scope and decisions (owner away; AI authorized to decide and record)

| Item | Recorded? | Assessment |
|---|---|---|
| OD-6: one shared adapter, stubs deleted | Yes (architecture, master-plan OD-6, report, worklog, ledger) | Reasonable: MarkItDown dispatches by format, the stubs had no importers. The prompt offered "delete or redirect". **Flag for owner.** |
| Converted files skip the D1 normalizer (`normalized=False`) | Yes (`ingestion-spec.md` "As implemented", architecture, report Decision 2) | Reasonable (normalizer requires the web-export frame, verified 4/4). But ADR-0002 Decision 1 still says the adapter returns "a normalized `ParsedDocument`", and the flow diagram at `ingestion-architecture.md:12` still routes MarkItDown output through `MarkdownNormalizer (D1)`. Doc inconsistency (F6). **Flag for owner.** |
| Signature check for `.pdf`/`.docx` | Yes | Reasonable and required by `ingestion-spec.md`; incomplete (F2). |
| `[pdf,docx]` extras, pin `>=0.1.8,<0.2`, extra `.htm` extension | Yes | Reasonable, small. |
| Two stale INGEST-002 lines corrected (G2 "not yet verified", EPIC-02 status) | Yes (report) | Unasked but correct (matches the INGEST-002 verify). |
| Placeholder `session-handoff-2026-09-25-autonomous.md` | Yes | Part of the owner's authorization; still empty (C). |

No functionality beyond the prompt. PASS.

## F. Quality spot-read (`markitdown_parser.py`, line by line)

Verifier probes (scratch script, worktree code):

| Input | Result |
|---|---|
| empty `.txt`, empty `.html`, empty `.htm` | `OK text=''`, 0 sections → **0 chunks in both arms** |
| valid PDF with no text (like a scanned PDF), `.docx` with no paragraphs | `OK text=''` → 0 chunks |
| empty `.pdf` / empty `.docx` | `DocumentParseError: content is not a valid .pdf/.docx file` |
| `.pdf` = `b"%PDF-1.4\n"` only | **`OK text='%PDF-1.4\n'`** (read as plain text) |
| `.docx` = a valid zip without `word/document.xml` | **`OK text='Content from the zip file …'`** (MarkItDown's ZipConverter) |
| `.pdf` header + garbage | `DocumentParseError … PDFSyntaxError: No /Root object!` |
| missing `.docx`, directory named `.docx` | `DocumentParseError: content is not a valid .docx file` (misleading: file not found / is a directory) |
| missing `.html`, directory named `.pdf` | `DocumentParseError` with the OS error — OK |
| `.txt` UTF-8 with BOM + `# Title` | text starts with `'﻿# Title'`, sections `[]` (heading lost); without BOM → `[('Title',)]` |
| `.txt` Latin-1 `café résumé` (12 bytes) | `'cafﻠ rﻠsumﻠ'` (charset guess on a tiny file; covered by the spec's spot-check rule) |
| `.htm` cp1252 with `<meta charset>`; `.htm` UTF-8 without meta | both decoded correctly (`Café “q”`, `Xin chào`, `Tiếng Việt`) |
| HTML `<title>  Retry\n   guide \t</title>` | `document_name='Retry\n   guide'` (inner newline kept) |
| blank `<title>` | falls back to `Document.name` — OK |
| headingless PDF | one chunk per arm, `heading_path=()`, `location_type='heading'` (disclosed limit) |

- **F1 (FAIL, spec MUST):** `:40-41` turn an empty conversion into `text=""` with no error; both chunkers then emit 0 chunks, so the document disappears from the index without a message. `ingestion-spec.md`: "Conversion failures MUST raise a clear error and MUST NOT silently drop a document." Scanned PDFs are the main real case (ADR-0002 risks). Not triggered by the current corpus (all Markdown).
- **F2 (FAIL):** the signature check (`:19-24, :35`) only catches "not a zip" / "no `%PDF-` prefix". Anything that passes it but is not a real document of that format falls back to MarkItDown's content guess and is returned as document text (`%PDF-1.4` header-only file; any zip renamed `.docx`). This is the same silent fallback the report says was fixed. Missing / directory `.docx` also gives a misleading "not a valid .docx" message because `zipfile.is_zipfile` returns `False` instead of raising.
- **F3 (minor):** UTF-8 BOM not stripped → first heading of a BOM `.txt` is lost (Notepad on Windows can write BOM files).
- **F4 (minor):** `document_name` only `.strip()`ed; inner whitespace/newlines from `<title>` reach chunk `document_name` and citations. `" ".join(title.split())` would fix it.
- **F5 (minor):** `result.text_content` is a "soft-deprecated alias for `markdown`" in 0.1.8 (`markitdown/_base_converter.py:28-30`); `result.markdown` is the stable name, which matters with the `<0.2` pin.
- OK: lazy import and converter cached per instance (`:50-55`, `enable_plugins=False`); one shared instance in the registry; `except Exception` wraps every converter error (also a missing `markitdown`) into `DocumentParseError` with `#source_id` and path, chained with `from error`, nothing swallowed; `KeyboardInterrupt` not caught; suffix checks lower-cased; `section_spans` reused so sections match the normalizer's spans.

## G. Explain-it-back

No "Explain it back" section in the report (the chat report is not visible to the verifier): UNVERIFIED. Corrections to the report's statements: (1) `onnxruntime` is not new with MarkItDown, ChromaDB already requires it; (2) without `markitdown` installed the adapter raises `DocumentParseError`, not `ModuleNotFoundError`; (3) "any conversion failure raises `DocumentParseError`" is not true for empty/textless or mismatched inputs (F1/F2); (4) the lazy-import mutation result depends on which checkout the editable install points at (B1).

## Findings

- **B1 (FAIL):** `test_markitdown_is_imported_lazily` is not hermetic: the subprocess ignores pytest's `pythonpath` and imports the installed package (here the main checkout), so a regression in this checkout passes. Fix 3.
- **F1 (FAIL):** empty or textless conversion (empty txt/html, scanned PDF, empty DOCX) → `text=""`, 0 chunks, no error. Fix 1.
- **F2 (FAIL):** signature check incomplete: header-only `.pdf` and non-Word zip `.docx` are returned as text; misleading error for a missing `.docx`. Fix 2.
- **F3–F5, B2 (minor):** BOM, title whitespace, deprecated `text_content`, CRLF test that cannot fail. Fixes 4–5.
- **F6 (minor, docs):** ADR-0002 D1 still says "normalized `ParsedDocument`"; `ingestion-architecture.md:12` diagram contradicts `:19`; `ingestion-architecture.md:20` "Any conversion failure raises" overstates; report/tech-stack `onnxruntime` framing. Fix 6.
- **Owner items (not defects):** OD-6 and "skip D1 for converted files" were AI decisions; the autonomous handoff note's "For the owner" section is still empty; V-2 on the Windows 3.13.3 venv (`.venv/Scripts/pip install -r requirements.txt`, then pytest) not checked by anyone.
- **Not re-checkable:** Windows `.venv/Scripts/python.exe` run; exact GitNexus file/symbol counts of the staged run; chat "Explain it back".

## Verdict

**ACCEPT WITH FIXES** — 3 FAIL (B1, F1, F2), 2 UNVERIFIED (V-2 on the owner's Windows venv; Explain-it-back). All four "Do" items are delivered, the corpus pipeline output is byte-identical and layer rules hold; the FAILs are in error handling for non-Markdown inputs, which the current corpus does not use, and one test that does not test its own checkout.

## Fix prompt (ready to paste, run in a new session)

```
Fix INGEST-003 per docs/reviews/code/INGEST-003-verify.md. Read CLAUDE.md, agents/prompts/_common.md, ADR-0002,
docs/specs/ingestion-spec.md first. Run GitNexus impact on MarkItDownParser.parse before editing. Do not touch corpus/,
data/ or validation/. Commit as "INGEST-003: fixes from verification".

1. Empty conversion is an error (src/knowledge_assistant/infrastructure/parsing/markitdown_parser.py, parse, ~l.40-41).
   Expected: if the converted text is empty or whitespace-only, raise DocumentParseError
   ("cannot convert #<id> (<path>): no text extracted ...") instead of returning text="".
   Proof: new parametrized test in tests/unit/infrastructure/test_markitdown_parser.py: empty .txt, empty .html,
   _pdf([]) (textless PDF), _docx([]) each raise DocumentParseError matching "#9x"; removing the guard makes it fail.

2. No content-guess fallback for .pdf/.docx (same file, _SIGNATURES / parse).
   Expected: a .pdf or .docx that passes the signature but is not a real document of that format raises
   DocumentParseError. Preferred: call the format's converter directly (markitdown.converters.PdfConverter /
   DocxConverter with StreamInfo(extension=...)) so MarkItDown cannot pick PlainText/Zip converters; minimum: require
   "word/document.xml" in the zip for .docx. Check that the file exists and is a regular file first, so a missing or
   directory path reports "file not found"/"not a file", not "not a valid .docx".
   Proof: tests: b"%PDF-1.4\n" as .pdf raises; a zip with only readme.txt as .docx raises; missing .docx message
   mentions not found. Existing 11 tests still pass.

3. Hermetic lazy-import test (tests/unit/infrastructure/test_markitdown_parser.py, test_markitdown_is_imported_lazily).
   Expected: the subprocess imports this checkout's src: pass cwd=ROOT and
   env={**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}.
   Proof: in a git worktree (or any checkout whose editable install points elsewhere), adding "import markitdown" at the
   top of markitdown_parser.py makes this test fail; restore -> passes.

4. Small robustness fixes (markitdown_parser.py).
   Expected: strip a leading "﻿" from the converted text; document_name = " ".join(title.split()) or Document.name;
   use result.markdown instead of the soft-deprecated result.text_content.
   Proof: tests: UTF-8-BOM .txt "# Title\n\nBody\n" -> sections [("Title",)]; HTML <title>"  Retry\n guide "</title>
   -> document_name "Retry guide".

5. CRLF test must test the adapter (test_txt_keeps_text_and_unifies_line_endings).
   Expected: a test where the converter result itself contains "\r\n"/"\r" (e.g. monkeypatch the parser's _markitdown
   to return an object whose .markdown is "a\r\nb\rc") and the ParsedDocument text is "a\nb\nc\n".
   Proof: removing the replace() line in parse makes the test fail.

6. Docs (no decision changes).
   - docs/architecture/ingestion-architecture.md: flow diagram (l.12) shows both flows (Markdown -> normalizer D1;
     MarkItDown -> ParsedDocument raw -> chunker); l.20 wording matches the fixed behaviour.
   - ADR-0002: add a dated "Amendment (INGEST-003)" line under Decision 1 pointing to ingestion-spec.md
     ("converted files are not D1-normalized"), marked as an AI decision pending owner review; do not rewrite D1.
   - docs/reports/execution/INGEST-003.md is history: add a "Fixes from verification" section instead of editing,
     noting onnxruntime is already required by chromadb and that a missing markitdown gives DocumentParseError.
   Proof: git diff shows only these additions.

After all fixes: .venv/Scripts/python.exe -m pytest -q (or the Linux venv; say which) -> all pass, count reported;
re-run scripts/ingestion/normalize_corpus.py, build_chunks.py --arm A, --arm B, check_g2.py -> git status clean on
data/ and validation/ (byte-identical), G2 11/11. Update the execution report, AI_WORKLOG (INGEST-003 entry) and the
ledger row 05 (stays "verified with fixes" until 99-VERIFY re-verifies). Run gitnexus detect-changes before committing.
```

# RE-VERIFY INGEST-003

Verifier session, 2026-09-25. Re-verification after the first verify ([INGEST-003-verify](INGEST-003-verify.md), ACCEPT WITH FIXES, `aa593b9`). Reviewed the fix commit `43910e5` ("INGEST-003: fixes from verification", parent `aa593b9`, 9 files) against the fix prompt at the end of the first review (fixes 1–6, each with its "Proof"), and re-ran the task's gate commands. Verifier branch `reverify-ingest-003` created at `43910e5` in a git worktree.

Environment: **Linux container, not Windows.** `.venv/Scripts/python.exe` does not exist here. Commands used `/home/user/Tech-docs-RAG/.venv313/bin/python` (Python 3.13.12, `markitdown` 0.1.8) and, for a second suite run, `/home/user/Tech-docs-RAG/.venv/bin/python` (Python 3.11.15). The editable install points at the main checkout (`python -c "import knowledge_assistant; print(knowledge_assistant.__file__)"` run outside the repo → `/home/user/Tech-docs-RAG/src/knowledge_assistant/__init__.py`). pytest's `pythonpath = ["src"]` puts this worktree's `src` first; every script and probe ran with `PYTHONPATH=<worktree>/src`, and the probes assert that `knowledge_assistant.__file__` is inside the worktree. Mutation checks backed up `markitdown_parser.py` to the session scratchpad, applied one mutation at a time, ran the adapter tests, and restored from the backup (byte comparison `restored: True`). `git status --short --untracked-files=all` was empty afterwards.

## 1. Fix-by-fix check

| # | Fix (first review's fix prompt) | Result | Evidence |
|---|---|---|---|
| 1 | Empty or whitespace-only conversion raises `DocumentParseError` ("no text extracted") | PASS | `markitdown_parser.py:48-50`. Test `test_document_without_text_raises_instead_of_vanishing` with 4 cases: empty `.txt`, `<html><body></body></html>`, `_pdf([])`, `_docx([])`, all matching `#92.*no text extracted`. |
| 1 proof | Removing the guard makes the test fail | PASS | Mutation (lines 49-50 deleted) → `4 failed, 16 passed` (all four parametrized cases). Probe: whitespace-only `.txt` (`"  \n\t\n"`) and `<body>&nbsp;</body>` `.htm` also → `no text extracted`. At `aa593b9` all of these returned `text=''`. |
| 2 | No content-guess fallback for `.pdf`/`.docx`; each format uses its own converter; file-not-found / not-a-file checked first | PASS | `_CONVERTERS` (`:18-24`) maps each extension to `PdfConverter` / `HtmlConverter` / `DocxConverter` / `PlainTextConverter`; `parse` calls `self._converter(extension).convert(stream, StreamInfo(extension=...))` (`:43-45`), which bypasses `MarkItDown`'s converter guessing. `path.is_file()` / `path.exists()` checked at `:38-39`. The fix prompt's "preferred" option was implemented. |
| 2 proof | `b"%PDF-1.4\n"` as `.pdf` raises; zip with only `readme.txt` as `.docx` raises; missing `.docx` says "not found"; existing tests still pass | PASS | Test `test_damaged_or_mismatched_file_raises_instead_of_being_read_as_text` (4 cases: non-zip `.docx`, readme-zip `.docx`, garbage `.pdf`, header-only `.pdf`) and `test_missing_file_and_directory_get_their_own_message`. Mutation "front end back" (`MarkItDown(enable_plugins=False).convert_local(...)` in place of the per-format converter) → `5 failed, 15 passed` (the 4 mismatched-file cases + the stub test). Mutation "is_file check removed" → `1 failed` (missing/directory test). Probe messages: header-only PDF → `No /Root object! - Is this really a PDF?`; readme zip → `Could not find main document part. Are you sure this is a valid .docx file?`; missing `.docx` / `.html` → `file not found`; directory `.docx` → `not a file`. At `aa593b9` the first two returned text (`'%PDF-1.4\n'`, `'Content from the zip file …'`). |
| 3 | Hermetic lazy-import test: subprocess gets `cwd=ROOT` and `PYTHONPATH=<checkout>/src` | PASS | `test_markitdown_parser.py:224-226`. |
| 3 proof | In a worktree whose editable install points elsewhere, an eager `import markitdown` at the top of the adapter makes the test fail | PASS | This verifier runs in exactly that setup (editable install → main checkout) and ran pytest without `PYTHONPATH` set: mutation (`import markitdown` after `from pathlib import Path`) → `1 failed, 19 passed` (`test_markitdown_is_imported_lazily`). In the first verify the same mutation passed (`11 passed`). |
| 4 | Leading BOM stripped; `document_name = " ".join(title.split()) or Document.name`; `result.markdown` instead of `result.text_content` | PASS | `:48` `result.markdown.removeprefix("﻿")` (escape, not a literal BOM: `cat -A` shows no `M-oM-;M-?` in the file); `:55`; `grep -rn text_content src/` → none. |
| 4 proof | BOM `.txt` `"# Title\n\nBody\n"` → sections `[("Title",)]`; `<title>"  Retry\n guide "</title>` → `"Retry guide"` | PASS | Tests `test_utf8_bom_does_not_hide_the_first_heading`, `test_title_whitespace_is_collapsed`. Mutation `.strip()` title → `1 failed` (title test). Mutation `removeprefix` removed → `1 failed`, but only the **stub** test fails: with the real `PlainTextConverter`, `charset_normalizer` already drops the BOM, so the BOM-`.txt` test passes without the adapter's line. The fix commit states this in the stub test's docstring. Acceptable: the adapter's own line is covered by the stub test, the end-to-end behaviour by the `.txt` test. |
| 5 | CRLF test must test the adapter (stub converter returning `"a\r\nb\rc"`) | PASS | `test_adapter_unifies_line_endings_and_drops_a_bom_from_the_converter_output` monkeypatches `parser._converter` to return `markdown="﻿a\r\nb\rc"` and asserts `text == "a\nb\nc\n"`. |
| 5 proof | Removing the `replace()` calls makes the test fail | PASS | Mutation (both `.replace(...)` removed) → `1 failed, 19 passed` (the stub test). |
| 6a | `ingestion-architecture.md`: flow diagram shows both flows; the error wording matches the fixed behaviour | PASS | `:12-13` two lines (Markdown → `MarkdownNormalizer (D1)` → Chunker; PDF/HTML/DOCX/txt → `MarkItDownParser` → `ParsedDocument (raw, LF, sections)` → Chunker). `:21` gives the reason for direct converters; `:22` lists the error cases (unknown extension, file not found, not a file, converter error incl. missing install, no text extracted); all five reproduced by the probe (unknown `.md` → `no MarkItDown converter for '.md'`). |
| 6b | ADR-0002: dated "Amendment (INGEST-003)" line under Decision 1, AI decision pending owner review; D1 not rewritten | PASS | `0002-markitdown-and-header-chunking.md:8`. `git diff aa593b9 43910e5 -- <ADR> docs/reports/execution/INGEST-003.md` → 0 removed lines (additions only). |
| 6c | Execution report is history: new "Fixes from verification" section; `onnxruntime` already required by `chromadb`; missing `markitdown` → `DocumentParseError` | PASS | `INGEST-003.md:73-109` appended, earlier sections unchanged (0 removed lines). `pip show chromadb` → `Requires: … onnxruntime …`; `pip show onnxruntime` → `Required-by: chromadb, magika`. The import is inside the `try` (`:41`, and `_converter`'s import runs from `:45`). |
| 6 proof | "git diff shows only these additions" | PASS (with two expected extras) | The docs diff also changes `tech-stack.md:12` (the `onnxruntime` framing, listed in the first review's F6) and one line of `ingestion-spec.md:10` (the signature-check sentence, which the fix made stale). Both are corrections, not decision changes. |
| After | pytest all pass (say which venv); pipeline re-run byte-identical, G2 11/11; report / worklog / ledger updated; detect-changes run | PASS | See §2. Report, worklog (`AI_WORKLOG.md:153-155`) and ledger row 05 updated in the commit (row left at `verified with fixes`, "not yet re-verified", as asked). |

## 2. Regression check of the whole task

| Check | Result | Evidence |
|---|---|---|
| Tests (3.13) | PASS | `.venv313/bin/python -m pytest -q` → `113 passed in 5.98s`. |
| Tests (3.11) | PASS | `.venv/bin/python -m pytest -q` → `113 passed in 5.84s`. |
| Test count | PASS | Adapter file: `20 tests collected` (was 11: the CRLF test replaced by `test_txt_keeps_text`, the 3-case broken-file test replaced by 4 mismatched + 4 empty + 1 missing/directory + stub + BOM + title = +9). 104 + 9 = 113. Adapter + structure tests: `27 passed`. |
| Corpus pipeline | PASS | With `PYTHONPATH=<worktree>/src` (probe line prints the worktree path): `normalize_corpus.py` → `24 documents, 1,186,335 normalized chars (raw LF 1,197,929)` / `inventory heading paths located: 636/636`, exit 0; `build_chunks.py --arm A` → `752 chunks`, `13/1157/1526/1600`, `24 (3.19%)` fence cuts, `447` dups, exit 0; `--arm B` → `859 chunks`, `207/1600/1600/1600`, `387 (45.05%)`, one-chunk `['09', '29']`, exit 0; `check_g2.py` → `**Overall: PASS** (11/11)`, exit 0. |
| Outputs byte-identical | PASS | `sha256sum` of the 11 tracked files under `data/processed/` and `validation/ingestion/` taken before the run, `sha256sum -c` after → `OK: 11`, `NOT OK: 0`; `normalized.jsonl` → `a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95`; `git status --short --ignored data validation` → empty. |
| Scope of the fix commit | PASS | `git diff --stat aa593b9 43910e5 -- corpus data validation config scripts src/knowledge_assistant/core src/knowledge_assistant/application src/knowledge_assistant/infrastructure/chunking` → empty. Code change is limited to `markitdown_parser.py` and its test file. `git ls-files '*.pdf' '*.docx' '*.html' '*.htm'` → nothing. |
| Layer rules | PASS | Structure tests in the green suite (incl. `test_markitdown_is_imported_only_by_its_adapter`); `grep -rnE "chromadb\|google\.genai\|PySide6\|markitdown" src/knowledge_assistant/{core,application}` → none; `grep -rln markitdown src --include=*.py` → only `markitdown_parser.py` and `registry.py` (which imports the adapter module, `registry.py:23`, not `markitdown`). |
| GitNexus | PASS (counts differ, as disclosed) | `npx -y gitnexus impact MarkItDownParser --direction upstream` → `"impactedCount": 1, "risk": "LOW"`, the one importer is `registry.py` (report: "impactedCount 1 (default_registry), risk LOW"). `npx -y gitnexus detect-changes -s compare -b aa593b9` on the tree at `43910e5` → `Changes: 9 files, 26 symbols` / `Affected processes: 1` / `Risk level: medium` / flow `Parse → _closes (5 steps) — changed: parse`. The report's "6 files, 18 symbols" was a staged run (marked "(staged)"), before the 3 bookkeeping files; flow and risk match. No side effects (`git status` empty afterwards). |
| Environment | UNVERIFIED (owner) | V-2 on the owner's Windows 3.13.3 `.venv` is still unchecked by anyone (same as the first review). |

## 3. Line-by-line read of the new `parse` (`markitdown_parser.py:32-66`)

| Line(s) | Reading |
|---|---|
| 33-35 | `extension = path.suffix.lower()` keeps the upper-case lookup working (probe `UPPER.DOCX` → same Markdown as the lower-case fixture). `where` gives every error `#<source_id> (<path>)`. |
| 36-37 | Unknown extension raises. Only reachable when the adapter is called directly (the registry routes `.md` to `MarkdownParser`); at `aa593b9` a direct `.md` call converted silently. Fine. |
| 38-39 | `is_file()` then `exists()`: missing → "file not found", directory → "not a file"; broken symlink → "file not found"; a symlink to a file works (probe `link.txt` → OK). The small race between the check and `open` is covered: `open` is inside the `try`. |
| 40-47 | `from markitdown import StreamInfo` and `_converter`'s `from markitdown import converters` both run inside the `try`, so a missing install becomes `DocumentParseError` (chained with `from error`). The file handle is closed by `with`. `StreamInfo` carries no `charset`: `HtmlConverter` then calls BeautifulSoup with `from_encoding="utf-8"`, which falls back to the `<meta charset>` or a guess when UTF-8 decoding fails. Probe: cp1252 `.htm` with meta → `Café “q”`; cp1252 `.html` **without** meta → `Café “q” résumé`; UTF-8 with and without BOM → correct; UTF-16 `.txt` → correct. `PlainTextConverter` uses `charset_normalizer` (unchanged from before: short Latin-1 text still decodes wrongly, `'cafﻠ rﻠsumﻠ'`, same output as `aa593b9`; covered by the spec's spot-check rule). `except Exception` does not catch `KeyboardInterrupt`. No exception is swallowed. |
| 48 | `removeprefix("﻿")`, CRLF/CR → LF, `strip("\n")` (only newlines; leading spaces kept). Correct for the fix prompt. |
| 49-51 | Whitespace-only text raises, otherwise exactly one trailing `\n`. |
| 52-58 | `normalized` stays at its default `False`; `document_name` collapses all whitespace and falls back to `Document.name` for a missing or blank `<title>` (probe `blanktitle.html` → file stem); `sections=section_spans(text)`, the same function the normalizer uses. |
| 60-66 | Converter instances cached per class name, created lazily; `.html`/`.htm` share one `HtmlConverter` (probe: `True`, cache `['HtmlConverter']`). The registry holds one adapter instance. |

Headingless PDF still gives one chunk per arm with `heading_path=()` and `location_type='heading'` (probe), the disclosed limit.

## 4. New findings (non-blocking)

- **N1 (minor, behaviour change not disclosed):** calling the converters directly also skips the `MarkItDown` front end's output clean-up (`markitdown/_markitdown.py:685-689`: `line.rstrip()` on every line and `re.sub(r"\n{3,}", "\n\n", …)`). Verifier probe, `aa593b9` vs `43910e5`: HTML `line one<br>line two` → old `'line one\nline two'`, new `'line one  \nline two'` (Markdown hard-break spaces kept); `.txt` `"# Title\n\n\n\n\nBody   \n"` → old `'# Title\n\nBody\n'`, new `'# Title\n\n\n\n\nBody   \n'`; PDF → new text ends with `'\n\n\x0c\n'` (a trailing form-feed line; the form feeds between pages were there before too). Chunk offsets stay correct (chunkers split on `"\n"` and `display_text` is still the exact slice), no heading path changes, the corpus is unaffected, and no spec rule requires the clean-up. But the report says the only change was "no content guessing". Suggested small follow-up: re-apply the two clean-up steps in `parse` after the line-ending unification, with a test (e.g. HTML `<br>` and 3+ blank lines).
- **N2 (minor, pre-existing, not in fix scope):** a `.txt` file with binary content is still returned as text (probe: `bytes(range(256))` and a PNG header renamed `.txt` → `OK`, text full of control characters). `PlainTextConverter` never fails; the fix prompt covered `.pdf`/`.docx` only. The spec's per-format spot-check rule applies before `.txt` is used.
- **N3 (cosmetic):** `docs/reports/execution/INGEST-003.md:82` (fix 5 row) contains a literal invisible BOM character inside `"…a\r\nb\rc"` (`cat -A` → `M-oM-;M-?`); the source file itself uses the escape. Harmless in rendered Markdown.
- **N4 (cosmetic):** the lazy-import test builds `PYTHONPATH` as `src + os.pathsep + ""` when `PYTHONPATH` is unset; the empty entry adds the cwd (`ROOT`) to `sys.path`. Harmless (`ROOT` has no `knowledge_assistant` package outside `src`).

## 5. Items from the first review

| Item | Now |
|---|---|
| B1, F1, F2 (FAIL) | PASS (fixes 3, 1, 2 above). |
| F3–F5, B2, F6 (minor) | PASS (fixes 4, 5, 6). |
| Explain-it-back | Now in the report (`INGEST-003.md:104-109`). Correct, with one caveat: "failures loud" holds for `.pdf`/`.docx`/empty output, not for binary `.txt` (N2). |
| V-2 on the owner's Windows 3.13.3 venv | UNVERIFIED (owner). |
| Owner items: OD-6 (one adapter, stubs deleted); converted files skip the D1 normalizer (now also an ADR-0002 amendment line "pending owner review") | Open for the owner (not defects). |
| Autonomous handoff note "For the owner" section | Still `_Filled in at the end of the run._` (`docs/plans/session-handoff-2026-09-25-autonomous.md:6`). Not part of the fix prompt; stays open. |
| Pre-edit `gitnexus impact` of the fix session | PASS as far as checkable: the claimed result (`impactedCount 1`, LOW) reproduces now. |

## Verdict: ACCEPT

All six fixes pass their stated proofs, each code fix is guarded by a test that fails under the matching mutation (guard removed → 4 failed; front end restored → 5 failed; `is_file` removed → 1; eager import → 1; BOM strip → 1; CRLF → 1; title → 1). The full suite passes on 3.13.12 and 3.11.15 (113), the corpus pipeline output is byte-identical (11/11 checksums, `normalized.jsonl` `a6db2f26…9ae95`, G2 11/11), and the layer rules hold. Together with the first review, INGEST-003 as a whole is accepted.

**FAIL: 0.** **UNVERIFIED: 1** (V-2 on the owner's Windows venv).

Open, non-blocking:
1. N1: direct converters dropped MarkItDown's line `rstrip` and 3+-newline collapse (undisclosed behaviour change for converted files; corpus unaffected). Re-apply in `parse` with a test when the adapter is next touched, or before a converted format is used in evaluation.
2. N2: binary `.txt` still read as text (spot-check rule covers it).
3. Owner review: OD-6, "converted files skip D1" (ADR-0002 amendment line), V-2 on Windows, the empty "For the owner" section of the autonomous handoff note.
4. Cosmetic: literal BOM in report line 82; empty `PYTHONPATH` entry in the lazy-import test.

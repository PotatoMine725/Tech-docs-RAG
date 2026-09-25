# VERIFY INGEST-001

Verifier session, 2026-09-25. Reviewed commit `1858e27` ("INGEST-001: core models, Markdown parser, normalization", 22 files) against `agents/prompts/03-INGEST-001-models-parser-normalization.md`, `agents/prompts/_common.md`, ADR-0003 (D1, D5, D6) and the EPIC-01 report. Commands were re-run by the verifier in a Linux container (`.venv/bin/python`, not `.venv/Scripts/python.exe`). GitNexus MCP tools are not available; the `npx -y gitnexus` CLI was used. Nothing was copied from the execution report. Mutation checks were run on a copy of the repo in the session scratchpad, not in the checkout.

## A. Acceptance / gate items

| # | Item (prompt "Do" / "Do not") | Result | Evidence |
|---|---|---|---|
| A1 | Do 1: core models in `core/models/`, plain dataclasses, no third-party imports | PASS | `core/models/__init__.py` imports only `dataclasses`; all classes `@dataclass(frozen=True)`. |
| A2 | Do 1: `ParsedDocument` = normalized text + source_id, document_name, source_url, variant info | PASS | `ParsedDocument.text`, `.source_id` property, `.document_name`, `.source_url`, `.sections` (`SectionSpan.variant`, `.variant_count`). |
| A3 | Do 1: `DocumentChunk` with exactly the D6 fields | PASS | 12 fields at `core/models/__init__.py:47-60` = ADR-0003 D6 list (`chunk_id` … `chunker_config`), same order, nothing extra. |
| A4 | Do 1: `Citation` with `location_type="heading"` | PASS | `core/models/__init__.py:70` default `"heading"`. |
| A5 | Do 2: Markdown parser in `infrastructure/parsing/markdown_parser.py`, registered by extension | PASS | `registry.default_registry()` maps `.md`/`.markdown`; `get(".MD")` resolves (test `test_parser_keeps_raw_line_endings_and_the_registry_selects_it`). |
| A6 | Do 3: deterministic, in-memory, sources never written | PASS | Normalizer has no I/O. After re-running the script, `git status --short` → empty (sources and `normalized.jsonl` unchanged). Checksum tests (`test_manifest_hashes_match_the_files_on_disk`, snapshot test) pass. |
| A7 | Do 3: `\r\n` → `\n` FIRST | PASS | `markdown_normalizer.py` `normalize()` first statement. Mutation "no CRLF step" → 1 test fails. Note: the Linux checkout is LF, so only the synthetic CRLF test exercises this. |
| A8 | Do 3: wrapper H1 + `Source:` → metadata; drop wrapper H1 / `Source:` / `---` | PASS | Preamble of all 24 docs listed by the verifier: only wrapper H1, `Source:`, `---`, `Note`, two access lines, and #29's YAML block. All 24 `text` start with `# <document_name>\n` and have `https://` `source_url`. |
| A9 | Do 3: remove known boilerplate lines, "list them in one constant, sourced from the EPIC-01 report" | FAIL (minor) | Removal is correct (see F), but (a) `BOILERPLATE_LINES` (`:24`) holds 4 patterns; the footer (`_LAST_UPDATED`, `_DATE`), label and rule removals are separate constants/logic, so the list is not in one constant. (b) The EPIC-01 report names only the wrapper, access lines and #29 front matter; ADR-0003:11 adds "latest version", "no longer supported", bylines and "version-selector lines". The `- Last updated on` + date footer and its `---` (19 docs, 57 lines) are in neither source: an unrecorded extension of the list. (c) ADR-0003's "version-selector lines" are not mentioned; the verifier's grep found no such lines (only tab-selector lists in #12, kept and disclosed). |
| A10 | Do 3: keep version variants 1..n, never infer labels | PASS | 636 spans with `variant`/`variant_count`; the (heading_path, variant, variant_count) multiset per doc equals the section inventory for all 24 docs. No version text added (0 lines added vs raw, see F). |
| A11 | Do 4: use case in application layer on core interfaces only; reads accepted docs from manifest → parse → normalize → `normalized.jsonl` (id, metadata, text, sha256); script | PASS | `application/ingestion/normalize_corpus.py` imports only `core.*` + stdlib. `.venv/bin/python scripts/ingestion/normalize_corpus.py` → `24 documents, 1,186,335 normalized chars (raw LF 1,197,929)` / `inventory heading paths located: 636/636`, exit 0. File: 24 lines, 1,393,800 bytes, sha256 `a6db2f26…9ae95`, keys `id, metadata, text, sha256`. |
| A12 | Do 5: offline tests for EOL, wrapper, boilerplate, #29 front matter, determinism, excluded docs never loaded, no infra import in core/application | PASS | One test each (names in B); layer rule by existing `tests/unit/test_project_structure.py` (green). |
| A13 | Do 6: every inventory heading path located as a character span; report misses | PASS | Script 636/636. Verifier's own check: spans contiguous (0 gaps), first `char_start` 0, last `char_end == len(text)` for all 24 docs, every span starts with `"#"*level + " " + last heading part + "\n"`. |
| A14 | Do not: chunk, embed, call Gemini | PASS | No chunker/embedder/Gemini code in the diff (`git show --stat 1858e27`). |
| A15 | `_common`: prompt saved verbatim | PASS | `diff agents/prompts/03-… docs/prompt-log/claude-code/INGEST-001.md` → identical. |
| A16 | `_common`: report, worklog, master plan / epic / ledger updated | PASS | All in the commit; ledger row `done`. |
| A17 | `_common`: `gitnexus_detect_changes()` before commit | FAIL (minor, claim) | Commit message says "gitnexus detect-changes: 0 processes, risk low". Verifier: `npx -y gitnexus detect-changes -s compare -b 3b7a9e2` → `Changes: 22 files, 135 symbols / Affected processes: 5 / Risk level: medium`. All 5 flows are inside the new code (`normalize`, `section_spans`, `_drop_boilerplate`, `main/build`), so no existing flow is at risk; but the recorded result reflects the default `unstaged` scope, which does not see new untracked files. |

## B. Tests

`.venv/bin/python -m pytest -q` → `63 passed in 4.47s`. At `3b7a9e2` (parent): `45 passed` → 18 new (11 in `tests/unit/infrastructure/test_markdown_normalizer.py`, 7 in `tests/unit/application/test_normalize_corpus.py`).

The tests assert behaviour, not just execution. Mutation checks (repo copy, one mutation at a time, the 18 new tests):

| Mutation | Result |
|---|---|
| none | 18 passed |
| no CRLF step | 1 failed |
| `BOILERPLATE_LINES` empty | 7 failed, 4 errors (preamble check raises) |
| no admonition-label removal | 3 failed |
| no blank-line collapse | 3 failed |
| `char_end - 1` | 1 failed |
| no excluded-document guard | 1 failed |
| no footer removal | 2 failed |
| no unknown-preamble raise | 1 failed |
| boilerplate removed inside code fences too | 1 failed |

Weak spots (not defects): several corpus-level assertions rely on `test_two_runs_give_identical_hashes_and_match_the_committed_file` (committed file = fresh run), which catches any output change but not whether the committed file was right in the first place; the verifier's independent line-diff in F covers that.

## C. Claims vs reality

| Claim (report / commit / worklog) | Result |
|---|---|
| 24 documents, 1,186,335 normalized chars, raw LF 1,197,929 | PASS (script re-run; 1,197,929 = EPIC-01 report) |
| `normalized.jsonl` 24 lines, 1,393,800 bytes | PASS (`wc -c -l`) |
| 636/636 inventory heading paths | PASS (script + own check A13) |
| 63 passed; 45 before + 18 new; 11 + 7 | PASS |
| 107 evidence quotes survive | PASS (42 blueprints, 107 evidence entries in `blueprint.yaml`; test green) |
| bylines #03, #10, #13 ×5, #17, #23; notes in #10–#13, #23; footer in 19 docs | PASS (verifier's raw-vs-normalized line diff: exactly these) |
| "boilerplate list from EPIC-01" (worklog) / "sourced from the EPIC-01 report and ADR-0003's measured facts" (report) | FAIL (minor): footer + `---` rule are in neither source (A9) |
| "gitnexus detect-changes: 0 processes, risk low" (commit message) | FAIL (minor): compare scope gives 5 flows / medium (A17) |
| "without the boilerplate removal, 3 tests fail" | UNVERIFIED: depends on how the mutation was made; the verifier's variant gave 7 failed + 4 errors. Tests demonstrably can fail. |
| GitNexus `impact` before editing: LOW (3 direct / 1 direct) | UNVERIFIED (index now stale at `3b7a9e2`; not re-run) |
| CLAUDE.md/AGENTS.md rewrites and `.claude/skills/gitnexus-*` not committed | PASS (`git show --stat` has neither; working tree clean after the verifier's gitnexus runs) |

## D. Project rules

| Rule | Result | Evidence |
|---|---|---|
| Layer imports | PASS | `grep -rnE "chromadb\|google\.genai\|PySide6\|infrastructure" src/knowledge_assistant/{core,application} --include=*.py` → only docstrings; structure tests green. |
| Model names only in config | PASS | No model names in the diff. |
| No API key | PASS | `git grep -E "AIza[0-9A-Za-z_-]{20,}"` → none. |
| Corpus untouched | PASS | `git show --stat 1858e27 -- corpus data/evaluation` → empty; checksum tests pass; `git status` clean after the run. |
| Excluded 14/19/24/27 never opened | PASS | `load_accepted_documents` reads only `documents` and raises on an excluded ID or `excluded/` path; `test_excluded_documents_are_never_opened` records 24 opens, all in `corpus/sources`. The script's `raw_chars` reads only `records` files. No other code references `corpus/excluded`. |
| Eval question file unchanged since `eval-freeze-v1` | N/A | Tag does not exist yet (`git tag` → none); EVAL-002 not run. The commit does not touch `data/evaluation`. |
| No eval question used for tuning | PASS | Blueprints are read only by the survival test (assertion that quotes survive); no parameter is derived from them. |

## E. Scope

- Disclosed deviations 1–5 (parser takes `Document`; `Citation` field order; `DocumentNormalizer` interface; committed `normalized.jsonl`; extra survival test): reasonable and within the prompt's intent.
- Not disclosed: the footer removal (`- Last updated on` + date + preceding `---`) extends the ADR-0003 D1 boilerplate list without an ADR/spec note (A9). Harmless for this corpus (content check in F), but it is a normalization parameter decided silently.
- `fence_mask()` added to the existing `markdown_structure.py` (new function, existing ones unchanged; reuses `_FENCE`/`_closes` instead of duplicating rules) — in line with "reuse it".

## F. Quality spot-read (`markdown_normalizer.py`)

- **Preamble validation** (`_check_preamble`, `:90-113`): every preamble line must be blank, the wrapper H1 at index 0, `Source:`, `---`, an admonition label, a boilerplate line, or inside a `---`-delimited YAML block whose lines look like `key:`; otherwise `DocumentParseError`. No silent drop. Multi-line YAML values would raise (loud, acceptable). An admonition label anywhere in the preamble is accepted without checking what follows (tolerable: the preamble is dropped as a whole).
- **Boilerplate removal** (`_drop_boilerplate`, `:120-153`): skips fenced lines; the date line is dropped only if it is the next non-blank line after `- Last updated on` and matches `YYYY-MM-DD`; a label goes only if the next non-blank line is a removed boilerplate line; a rule goes only if the next non-blank line is the footer. Correct.
- **Independent content check:** for all 24 docs, the verifier compared the multiset of non-blank raw lines (from the page H1, CRLF→LF) with the normalized text. Lines added: 0. Lines removed, in total: 19 `---`, 19 `- Last updated on `, 19 dates, 5 `Note`, 5 `Warning`, 5 "This isn't the latest version…", 5 "This version of ASP.NET Core is no longer supported…", 9 author bylines. Nothing else. Every non-blank code line is kept byte-for-byte.
- **Could `BOILERPLATE_LINES` remove real content?** `grep -E "^\s*By \["` over `corpus/sources` → 9 lines, all author bylines; `grep` for "Last updated on" / "isn't the latest version" / "no longer supported" finds no other forms. No false positives in this corpus. Latent risk: `^By \[[^\]]+\]\([^)]*\)` would also match a prose line such as "By [configuring X](…), you …" in a future corpus (INGEST-003); a stricter byline pattern would be safer.
- **Blank-line collapse** (`_collapse_blank_lines`): runs outside fences become one empty line; whitespace-only lines outside fences become `""`; fenced blank lines untouched. `"\n\n\n"` does not occur outside fences (test).
- **Spans** (`section_spans`, `:65-87`): `starts` built with `len(line)+1`; `char_end = min(starts[end_line], len(text))` clamps the last section to `len(text)` (the text ends with one `\n`, so `split` yields a trailing `""` and `starts[len(lines)] = len(text)+1`). Verified on all 24 docs (A13). No off-by-one.
- **Residue kept (observations, not defects of the prompt):** a `---` rule before `## Additional resources` in 20 docs stays at the end of the preceding section's span (e.g. #01 "Next step" ends with `---`); #15 (Q&A thread) keeps "Sign in to comment" / "No comments" chrome. Both are noise for chunk text, not content loss.

## G. Explain-it-back

The final chat report's "Explain it back" bullets are not in any file, so they cannot be checked (UNVERIFIED). The report's "Normalization rules" section is correct except the source attribution of the footer rule (C). For the record, what the owner should be able to defend:
- CRLF→LF happens before anything else because `char_start`/`char_end` and `sha256` are computed on the normalized text; a Windows checkout (CRLF) and a Linux checkout (LF) must produce identical offsets and hashes.
- Unknown preamble lines raise instead of being dropped: dropping by position alone could silently delete content if a page's layout differs.
- Boilerplate is removed as whole lines outside code fences, with the label/rule only when it belongs to a removed line, so real Notes/Warnings survive (70 `Warning`, 28 `Note` labels remain).
- Variants are numbered by repeated heading path, not labelled with versions, because the corpus gives no reliable version per variant (ADR-0003).
- Spans are validated against the EPIC-01 inventory (636/636) and the 107 evidence quotes, which is what later makes section hit@5 computable against the frozen ground truth.

## Verdict: ACCEPT WITH FIXES

The code is correct: normalization removes exactly the intended lines, is deterministic, keeps sources and excluded docs untouched, and all 636 sections have correct spans. The fixes are documentation-only: the provenance of the boilerplate list, an undocumented extension of that list, and a wrong GitNexus claim. **FAIL: 4 rows, 2 distinct defects** (A9 = C "boilerplate source"; A17 = C "gitnexus"), all minor. **UNVERIFIED: 3** (mutation count claim, pre-edit impact claim, chat Explain-it-back).

## Fix prompt (run in a new session)

```
Fix INGEST-001 verification findings (docs/reviews/code/INGEST-001-verify.md). Read agents/prompts/_common.md.
Do not change normalization behaviour: data/processed/documents/normalized.jsonl must stay byte-identical
(sha256 a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95).

1. Boilerplate list in one place (src/knowledge_assistant/infrastructure/parsing/markdown_normalizer.py):
   make the complete removal list visible in one constant or one documented block (the four BOILERPLATE_LINES
   patterns + footer "- Last updated on"/date/preceding "---" + admonition label + wrapper items), each with its
   source (EPIC-01 report, ADR-0003:11, or "added in INGEST-001, observed in 19 docs").
   Check: pytest green; re-run scripts/ingestion/normalize_corpus.py; `git status` shows no diff to normalized.jsonl.
2. Record the footer extension: ADR-0003 D1 lists no page footer. Add it to docs/specs/ingestion-spec.md (D1 removal
   list with sources) and as Deviation 6 in docs/reports/execution/INGEST-001.md. Also state there that ADR-0003's
   "version-selector lines" were searched for and none exist in the corpus (tab-selector lists in #12 are kept).
   If the owner should confirm the footer removal, ask (AskUserQuestion) and record the answer.
   Check: grep "Last updated" docs/specs/ingestion-spec.md docs/reports/execution/INGEST-001.md → hits.
3. Correct provenance wording: AI_WORKLOG.md INGEST-001 entry ("boilerplate list from EPIC-01") and the report's
   "sourced from the EPIC-01 report and ADR-0003's measured facts" → name which item comes from which source.
   Check: the wording matches the list in fix 1.
4. GitNexus claim: in the report, replace/qualify "0 processes, risk low" with the compare-scope result
   (`npx -y gitnexus detect-changes -s compare -b 3b7a9e2` → 22 files, 5 affected processes, risk medium; all flows
   are in new code) and note that the default unstaged scope ignores new untracked files.
   Check: the report quotes the real command output.
5. (Optional, owner decision) the `---` before "## Additional resources" (20 docs) and #15's Q&A chrome
   ("Sign in to comment", "No comments") are kept. List them as known residue in the report; remove only if the
   owner decides so (that would change normalized.jsonl and needs its own test).
Commit: "INGEST-001: fixes from verification". Then re-run 99-VERIFY for INGEST-001.
```

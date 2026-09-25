# RE-VERIFY INGEST-001

Verifier session, 2026-09-25. Re-verification after the first verify ([INGEST-001-verify](INGEST-001-verify.md), ACCEPT WITH FIXES, `50f45b1`). Reviewed the fix commit `98fdb5a` ("INGEST-001: fixes from verification", 5 files) against the fix prompt at the end of the first review, and re-ran the task's gate commands. HEAD stayed on `claude/sleepy-wright-vj962y`; older revisions were read with `git show <rev>:<path>`. Commands ran in a Linux container (`.venv/bin/python`). Mutation checks ran on a `git archive HEAD` copy in the session scratchpad, not in the checkout.

## 1. Fix-by-fix check

| # | Fix (first review's fix prompt) | Result | Evidence |
|---|---|---|---|
| 1 | Removal list in one constant / one documented block, source per item; no behaviour change | PASS | `markdown_normalizer.py:22-52` "REMOVAL LIST (ADR-0003 D1)": sections A (preamble), B (body lines), C (removed only with the line they introduce) plus "kept on purpose" residue; each item tagged EPIC-01 / ADR-0003 / INGEST-001. Behaviour check in §2. |
| 1 check | pytest green; script re-run; no diff to `normalized.jsonl` | PASS | `63 passed in 4.54s`; script → `24 documents, 1,186,335 normalized chars (raw LF 1,197,929)` / `inventory heading paths located: 636/636`, exit 0; `sha256sum` → `a6db2f26954d77ddd4d52913f163572c174a113b48534a35420dea3bff19ae95`; `git status --short` → empty. |
| 2 | Footer extension recorded in `ingestion-spec.md` and as report Deviation 6; version-selector lines searched and absent | PASS | `docs/specs/ingestion-spec.md:15-20` (removal list with sources, footer marked "extension beyond ADR-0003 D1", version-selector note, residue); `docs/reports/execution/INGEST-001.md:73` (Deviation 6). Verifier's own search: `grep -rhiE "\?view=aspnetcore" corpus/sources` → 383 lines, all ordinary in-text links with a `?view=` query, none a selector line; no line matching `^\s*(version\|select a version)`. Claim holds. |
| 2 check | `grep "Last updated" docs/specs/ingestion-spec.md docs/reports/execution/INGEST-001.md` → hits | PASS | `ingestion-spec.md:18`, `INGEST-001.md:29`, `INGEST-001.md:73`. |
| 2 (owner) | "If the owner should confirm the footer removal, ask and record the answer" | OPEN (owner) | No AskUserQuestion answer recorded; the report/spec do not say an owner decision is pending either. Not a defect of the fix (the step was conditional); recorded by the verifier as an open owner item in the ledger. |
| 3 | Provenance wording in worklog and report | PASS | Worklog `AI_WORKLOG.md:108` now "boilerplate list from EPIC-01 + ADR-0003 plus a page-footer rule added in this task"; report `INGEST-001.md:29` names a source per item. Cross-check against sources: ADR-0003 line 11 lists wrapper, `Source:`, `---`, access line, "latest version", "no longer supported", bylines, version-selector lines; EPIC-01 report lines 47-48 list the wrapper, access lines and #29's YAML front matter. The tags in the code block match these. Small gap: in the report, the "latest version" / "no longer supported" item carries only doc numbers, not "(ADR-0003)"; the code block has it. Not material. |
| 4 | GitNexus claim replaced with compare-scope output | PASS | Report `INGEST-001.md:44-49` + "Correction (verify fix)" paragraph (`:57`). Verifier: `npx -y gitnexus detect-changes -s compare -b 3b7a9e2` → `Changes: 23 files, 139 symbols` / `Affected processes: 5` / `Risk level: medium`; the 5 flows are the same as quoted (Main → Normalize; Section_spans → _closes; Normalize → _is_boilerplate / Next_content / _closes), all in new code. The report says 137 symbols; the 2-symbol difference comes from the report being written before its own final edits were committed; files, flows and risk match. |
| 5 | (Optional) residue listed; remove only on owner decision | PASS | Listed in code block (`:50-51`), spec `:20`, report Deviation 7. Behaviour unchanged (hash identical). Removal left to the owner. |

## 2. Is the code change comments/structure only?

`git diff --stat 98fdb5a~1 98fdb5a -- src tests data corpus` → only `markdown_normalizer.py` (31+, 14-). The diff edits the module docstring, adds comment lines, and moves the definitions of `_RULE`, `_SOURCE`, `_FRONT_MATTER_KEY` above `BOILERPLATE_LINES` (module-level `re.compile` constants with no dependencies on each other).

AST check (scratchpad script, module docstring removed): every top-level statement at `98fdb5a~1` has an identical `ast.dump` at `98fdb5a` (same set, all statements equal); only the order of the constant assignments differs. All regex strings are unchanged. **No behaviour change**, consistent with the byte-identical `normalized.jsonl`.

(`detect-changes -s compare -b 50f45b1` reports `normalize` as changed in 3 flows; GitNexus works on line ranges and the constants moved lines. The AST check shows no real change.)

## 3. Re-run of the task gates

| Check | Result | Evidence |
|---|---|---|
| Tests | PASS | `.venv/bin/python -m pytest -q` → `63 passed in 4.54s`. |
| Script / 636 spans / determinism | PASS | See fix 1 check. |
| Corpus, `data/evaluation`, tests untouched by the fix commit | PASS | `git diff --stat 98fdb5a~1 98fdb5a -- tests data corpus` → empty. |
| Layer rule | PASS | Fix commit touches only comments in an infrastructure file; structure tests green. |
| GitNexus side effects | PASS | After both runs `git status --short` → empty; `.claude/skills/gitnexus/` is tracked and unchanged; `.gitnexus/` is ignored. |

## 4. Items UNVERIFIED in the first review

| Item | Now |
|---|---|
| "3 tests fail" mutation count | PASS. The report now names the mutation (`if _is_boilerplate(stripped):` → `if False:` in the body loop, preamble check untouched). Verifier applied exactly that at `markdown_normalizer.py:151` on a scratch copy → `3 failed, 15 passed` (the two normalizer tests for wrapper/boilerplate and the committed-file hash test). |
| Pre-edit `gitnexus impact` results | UNVERIFIED (historical; the index state before the edit cannot be reconstructed). Accepted. |
| Chat "Explain it back" | UNVERIFIED (not in any file). Accepted, as for earlier tasks. |

## 5. New findings

- **(minor, docs)** The code comment (`markdown_normalizer.py:28`) and `ingestion-spec.md:19` say the tab-selector link lists are in "#12/#13". `grep -rnE "tabpanel|\?tabs=" corpus/sources` → hits only in #12 (12 lines, e.g. `- [Minimal APIs](#tabpanel_1_minimal-apis)`); #13 has none. It does not affect behaviour or any decision (those lines are kept either way). Fix when the file is next edited; does not block.

## Verdict: ACCEPT

Fixes 1–4 pass their checks, fix 5 is handled as intended (residue listed, left to the owner), the code change in `98fdb5a` has no effect on behaviour (AST-identical statements, `normalized.jsonl` sha256 `a6db2f26…9ae95` unchanged), and the full suite passes (63). Together with the first review, INGEST-001 as a whole is accepted.

**FAIL: 0** (one trivial wording inaccuracy, "#12/#13" → "#12", recorded as non-blocking). **UNVERIFIED: 2** (pre-edit `gitnexus impact`, chat "Explain it back"; both historical, accepted).

Open, non-blocking:
1. **Owner decision:** confirm the footer removal (`- Last updated on` + date + preceding `---`, 19 docs), which extends ADR-0003 D1 (spec `ingestion-spec.md:18`, report Deviation 6). Not yet asked.
2. **Owner decision (optional):** remove the known residue (`---` before "## Additional resources", #15 Q&A text)? Would change `normalized.jsonl` and needs its own test.
3. "#12/#13" → "#12" in the code comment and spec (tab-selector lists).
4. Byline regex could match prose in a future corpus (INGEST-003); consider a stricter pattern there.

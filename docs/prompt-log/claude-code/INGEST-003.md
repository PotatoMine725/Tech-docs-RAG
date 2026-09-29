# INGEST-003 — prompt log

## Owner message that started the session (2026-09-25)

```
Another session is opening, performing review & verify ingest-002. You have my authorization to perform tasks after that session finishes doing, including executing next prompts, verify, manage git & PRs. You can spawn at most 3 sub-agents. Periodically run /compact yourself if possible. I won't be back for over an hour so if you stumble against anything, make your own decisons and write back to a document. And when i come back, flag me.
```

The INGEST-002 verify had already finished (ACCEPT, merged into `dev` as PR #4). Next prompts per `docs/plans/session-handoff-2026-09-25.md`: 1 (owner verdicts) is human-only; 2 (EVAL-001 re-verify) was given to a separate verifier sub-agent; 4 (EVAL-002) stays blocked by 1; so this session ran 5: `agents/prompts/05-INGEST-003-markitdown-optional.md`. The project is not behind schedule (target Sat 26), so the cut line (OD-15) does not apply.

## Prompt file (verbatim)

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

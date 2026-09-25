# SETUP-001 execution report

**Date:** 2026-09-24 · **Scope:** setup only (no RAG, embeddings, retrieval, Gemini calls, evaluation, experiments, GUI).

## Established
- Architecture: presentation -> application -> core <- infrastructure; skeleton packages under `src/knowledge_assistant/` (Protocol interfaces, minimal dataclasses, parser registry, Gemini stub that makes no calls, lazy-PySide6 `app.py`).
- Stack: Python, PySide6, ChromaDB, Gemini (`google-genai`), pytest, JSON/JSONL. `python-dotenv` retained (used by existing smoke script).
- Structure, docs (specs, architecture, ADR, tech-stack), agents, plan/epics, snapshots, prompt log created; `CLAUDE.md` rewritten short.

## Corpus migration
- 28 files found in `Markdown sources/` (brief said 29): 01-24, 26-29. **#25 never existed** (owner-confirmed 2026-09-24: skipped in conversion). Effective counts: 28 original / 24 accepted / 4 excluded. Excluded: **4** (14, 19, 24, 27). Move (not copy); no contents edited.
- Source integrity: SHA-256 taken before (`docs/snapshots/corpus/source-checksums-premigration.sha256`) and after; sorted diff identical -> **PASS**.

## Validation performed (actually run)
- pyproject parses (tomllib): pass.
- `.venv` pytest (installed pytest into `.venv`): **9 passed**; gemini-marked tests deselected by default.
- Tests cover: package import, core/application have no PySide6/chromadb/google imports (AST) and no outer-layer imports, excluded IDs exactly {14,19,24,27} and absent from sources, Gemini stub raises ConfigurationError without key, existing chroma path config.
- Secret scan (`AIza`) outside .venv/.git: none. `git check-ignore`: `.env` ignored, `.env.example` not; corpus/docs/agents/src/tests/scripts/data/evaluation not ignored.
- PySide6 6.11.2 installed into `.venv` afterwards (import verified); `app.py` GUI window not launched; `smoke_test.py` not run.

## Deviations / issues
- Built at repo root (no nested `knowledge-assistant/`); did not create question-bank directories.
- Old CLAUDE.md (question-bank rules, untracked) preserved at `docs/specs/question-bank-rules.md`; GitNexus block retained.
- `app_config.py` -> `src/knowledge_assistant/config.py`; `tests/test_app_config.py` -> `tests/unit/test_config.py`; `scripts/smoke_test.py` -> `scripts/utilities/`; `links.txt` -> `corpus/`; source `prompt.md` copied to prompt-log, `Markdown sources/` removed after emptied (`prompt.md` original was moved out).
- Empty dirs tracked with `.gitkeep`. `data/chroma/*` ignored by default.
- `CHROMA_PATH` default `D:\ChromaDB` kept.

## Unresolved decisions
Canonical ChromaDB path/commit policy; Gemini model (SDK-selected, owner has key only); embedding provider; chunking (requirements to come from owner); metrics; experiment selection.

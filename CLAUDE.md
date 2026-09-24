# CLAUDE.md — Knowledge Assistant constitution

Grounded RAG desktop assistant over a curated corpus. Details live in `docs/`; keep this file short.

1. **Purpose/scope:** Documents → Parsing → Chunking → Embedding → ChromaDB → Retrieval → Gemini → Answer + Citation. Evaluation (≥30 questions) and ≥2-approach experiment (header-aware vs fixed-size chunking, ADR-0003) are first-class. Questions may be English or Vietnamese over an English corpus (ADR-0003 D9). Setup-phase skeletons only until a task says otherwise.
2. **Stack (locked):** Python, PySide6, ChromaDB, Google Gemini API (`google-genai`), pytest, JSON/JSONL; MarkItDown for non-Markdown inputs, in `infrastructure/parsing/` only (ADR-0002). MUST NOT add C#/.NET/Java/Node/React/Angular/Vue/Flutter/Electron/ASP.NET as the app stack (they are corpus *subject matter* only). SQLite, ML/ONNX, reranking: only when a concrete decision requires. See `docs/architecture/tech-stack.md`.
3. **Layers:** presentation → application → core ← infrastructure. Core MUST NOT import PySide6/ChromaDB/Gemini/format-specific code; application MUST depend on core interfaces only; GUI MUST NOT hold business logic. Enforced by `tests/unit/test_project_structure.py`.
4. **Corpus:** IDs run 1–29 but #25 never existed (skipped during conversion), so 28 original, 24 accepted (`corpus/sources/`), 4 excluded (`corpus/excluded/`: 14, 19, 24, 27). MUST NOT renumber, edit, or delete sources; MUST NOT use excluded docs. Normalization/dedup happens in memory only (ADR-0003 D1).
5. **Formats/citations:** domain models Document/ParsedDocument/DocumentChunk/Citation stay format-independent; parsers normalize to Markdown text, which only infrastructure chunkers interpret (ADR-0002). Citations use the heading path (`location_type="heading"`, ADR-0003 D5/D6) and MUST NOT assume page numbers.
6. **Grounding/models:** answers MUST be grounded in retrieved corpus context; if insufficient, say so explicitly. Answer in the question's language; citation excerpts stay in the original English. Gemini MUST be behind `core/interfaces/llm.py`, only in `infrastructure/llm/gemini/`. Models (ADR-0004): embedding `gemini-embedding-001`; answer + judge `gemini-3.5-flash-lite`; fallback `gemini-3.5-flash` after retry/backoff. Model names are pinned in configuration only, never hard-coded in code and never `-latest` aliases.
7. **Secrets:** `GEMINI_API_KEY` from environment only. MUST NOT hard-code, commit, print or log keys. `.env` git-ignored; `.env.example` placeholders only.
8. **Tests/validation:** offline tests by default; Gemini tests use `@pytest.mark.gemini` (deselected). Run with `.venv/Scripts/python.exe -m pytest`. MUST NOT report success for unverified checks.
9. **Data/evaluation:** MUST NOT fabricate results, scores, latency, ground truth. Ground truth (expected `source_id` + heading path) is written before indexes are built; LLM-judge verdicts get a manual spot-check (ADR-0004 D12). Unknown decisions are marked TBD / DECISION REQUIRED.
10. **Docs:** specs=WHAT/WHY, architecture=HOW, plans=WILL, reports=HAPPENED, reviews=QUALITY, knowledge=DISTILLED, snapshots=POINT-IN-TIME, prompt-log=HISTORY, agents/=OPERATIONAL. Do not merge them.
11. **Git safety:** MUST NOT commit secrets or overwrite untracked files without a backup. Before editing symbols, follow the GitNexus rules below.

Legacy question-bank rules (superseded for this project, preserved): `docs/specs/question-bank-rules.md`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Tech-docs-RAG** (1638 symbols, 1836 relationships, 6 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Tech-docs-RAG/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Tech-docs-RAG/clusters` | All functional areas |
| `gitnexus://repo/Tech-docs-RAG/processes` | All execution flows |
| `gitnexus://repo/Tech-docs-RAG/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

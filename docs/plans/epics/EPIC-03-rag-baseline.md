# EPIC-03-rag-baseline

Status: in progress. RAG-001a done 2026-09-26 (embedder + cache, V-1, ADR-0005; awaiting 99-VERIFY). OD-7 and OD-8 decided (ADR-0005).

Target: Sun 27 – Mon 28 Sep 2026 (Phase 2). Deadline for the whole project: 2026-10-01.
Entry condition: evaluation ground truth committed (M1) before any index is built.

Scope: Gemini embedder, ChromaDB collections for both arms, retrieval (top-k = 5), grounded generation with heading-path citations and "insufficient information" handling, retry/fallback (ADR-0004), CLI ask script. Deliverables and exit gate G3: [master-plan.md](../master-plan.md#epic-03-rag-baseline).

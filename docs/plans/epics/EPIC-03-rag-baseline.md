# EPIC-03-rag-baseline

Status: in progress. RAG-001a done 2026-09-26 (embedder + cache, V-1, ADR-0005; verified). RAG-001b done 2026-09-26 (Chroma store, both arms indexed: A 733 = 733, B 859 = 859; verified); G3 box 1 ticked. RAG-002 done 2026-09-26 (retriever with passage-hash dedup, prompt `answer_v1`, citations, gate threshold 0.686, basic Gemini LLM; first end-to-end dev answers in EN and VI; verified). RAG-003 done 2026-09-26 (retry/fallback/throttle, `LLMError` kinds, token accounting, `scripts/ask.py`, live smoke checks; awaiting 99-VERIFY; G3 evidence complete). OD-9, OD-10 and OD-11 decided. OD-7 and OD-8 decided (ADR-0005). The index is in `data/chroma/` (OD-7), rebuilt from the embedding cache with 0 API requests.

Target: Sun 27 – Mon 28 Sep 2026 (Phase 2). Deadline for the whole project: 2026-10-01.
Entry condition: evaluation ground truth committed (M1) before any index is built.

Scope: Gemini embedder, ChromaDB collections for both arms, retrieval (top-k = 5), grounded generation with heading-path citations and "insufficient information" handling, retry/fallback (ADR-0004), CLI ask script. Deliverables and exit gate G3: [master-plan.md](../master-plan.md#epic-03-rag-baseline).

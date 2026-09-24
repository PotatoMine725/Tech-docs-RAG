# BONUS-001 — Hybrid search (BM25 + vector, RRF) and VI→EN query rewriting (optional, OD-16)

Read `agents/prompts/_common.md` first and follow it.
Entry: EXP-001 done (M3) and time left. Ask the user which parts to do (A only / A+B).

## Why
The corpus is full of exact identifiers (`ASP0033`, `IAsyncEnumerable`, `[Theory]`, keyword names) where lexical search should beat embeddings; VI questions against an English corpus are the known weak spot. Both are brief bonus items and cheap to evaluate with the existing runner (retrieval mode = no LLM quota).

## Do
Write ADR-0006 first (design + what is held constant). Use the winning arm's chunks from EXP-001; eval set unchanged; no tuning on the eval set (RRF k = 60 fixed, weights fixed a priori).
- **A. Hybrid**: local BM25 (`rank_bm25`) over `embed_text`, tokenizer that keeps code identifiers (split camelCase/dots but keep original token too); fuse with vector top-k via Reciprocal Rank Fusion; retrieval as a strategy selectable by config. Offline tests. Retrieval-only eval → compare vector vs hybrid (overall, per language, identifier-heavy questions).
- **B. Query rewriting**: for VI questions, one Flash-Lite call translates/rewrites to an English search query before retrieval (answer still in VI). Cache rewrites. Retrieval-only eval on VI cases + parallel subset → does it close the EN/VI gap?
- Report `docs/reports/epics/BONUS-001.md` with the same 5-point structure + per-case evidence + added latency/cost per query.

# EPIC-02-ingestion-pipeline

Status: in progress. INGEST-001 (models, parser, normalization) verified 2026-09-25 (re-verify ACCEPT); INGEST-002 (both chunkers + stats) verified 2026-09-25 (ACCEPT, G2 passed); INGEST-003 (MarkItDown adapter) verified 2026-09-25 (ACCEPT WITH FIXES → fixes re-verified ACCEPT). All three EPIC-02 tasks verified. INGEST-004 (ADR-0003 D3a amendment: Arm A drops heading-only chunks, 752 → 733) done 2026-09-25, waiting for `99-VERIFY`. Task status: [ledger](../task-ledger.md).

Target: Fri 25 – Sat 26 Sep 2026 (Phase 2). Deadline for the whole project: 2026-10-01.

Scope: core models, Markdown parser, normalization (ADR-0003 D1), header-aware chunker (D2–D5), fixed-size chunker (D7), per-arm chunk files and stats, then the MarkItDown adapter (ADR-0002). Deliverables and exit gate G2: [master-plan.md](../master-plan.md#epic-02-ingestion-pipeline).

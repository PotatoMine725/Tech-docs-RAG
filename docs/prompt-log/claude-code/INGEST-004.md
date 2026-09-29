# INGEST-004 prompt (verbatim, given in chat 2026-09-25)

Step 0 (housekeeping, same commit as the ledger update): in docs/plans/task-ledger.md, row 02 EVAL-002 — replace
"waits for OWNER-001 to be verified" with "waits for INGEST-004 (verified) — OWNER-001 verified 2026-09-25".

Task INGEST-004 — ADR-0003 amendment: drop heading-only Arm A chunks.
Read agents/prompts/_common.md first and follow it. Entry: OWNER-001 `verified`; no ChromaDB index exists (check data/chroma/). Otherwise STOP.

Owner decision 2026-09-25: Arm A emits 19 chunks whose body is only a heading line (D3 merges only with the next sibling, so an H2 followed directly by its H3 child is left alone). They add no content (the heading path is already in every child chunk's D5 header), can crowd top-k, and their span lies inside the expected section, so section_hit counts them as hits (false hit favouring Arm A). Decided before any index or result exists.

1. Add amendment "D3a" to docs/architecture/decisions/0003-…md: after chunking, Arm A drops chunks whose display text is empty after removing heading lines. Arm B is unchanged. State the reason above and that it was decided before results.
2. Implement it in the header-aware chunker (config-driven, offline tests: heading-only dropped, heading + body kept, IDs stay deterministic and contiguous).
3. Re-run scripts/ingestion/build_chunks.py for both arms. Expect: Arm A heading_only_chunks = 0 and count 752 − 19 = 733 (explain any other difference); Arm B byte-identical to before (prove with hashes).
4. Re-run the G2 checks. Also check that every expected and alternate heading path in blueprint.yaml still has ≥ 1 Arm A chunk overlapping its span; list any that don't.
5. Update the INGEST-002 report (addendum section), stats, ledger, AI_WORKLOG; commit on a new branch ingest-004, push, open a PR into dev. STOP — the owner runs 99-VERIFY for INGEST-004.

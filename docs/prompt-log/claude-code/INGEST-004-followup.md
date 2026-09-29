# INGEST-004 follow-up prompt (verbatim, given in chat 2026-09-25)

INGEST-004 follow-up — fixes from docs/reviews/code/INGEST-004-verify.md (verdict ACCEPT, non-blocking notes).
Read agents/prompts/_common.md and the review first. Keep the scope to the items below.

1. Stats: make heading_only_chunks use the D3a definition (display text empty after removing heading lines, headings inside code fences not counted), sharing the same helper the filter uses. Add a test where the old definition and the new one disagree. Re-run build_chunks for both arms: arm-a.jsonl and arm-b.jsonl must be byte-identical to the verified versions (only stats files may change); show the SHA-256.
2. Tests: remove or rewrite the fence test that can never fail (named in the execution report) so it fails when fence handling is broken; prove it with a mutation, then restore.
3. Execution report: "5 new tests" → the real count; rephrase the "no content lost" claim precisely: D3a removes 0 characters in all 24 docs; the pre-existing D1 duplicate drop leaves coverage gaps in #11, #13, #17, #23 (duplicate text, identical before and after D3a).
4. Explain-it-back: add your "Explain it back" bullets to docs/reports/execution/INGEST-004.md. Also update agents/prompts/_common.md "When done" step 6 so the bullets are saved in the execution report, not only in chat; log it in agents/prompts/CHANGELOG.md.
5. Run `npx gitnexus analyze`, then gitnexus_detect_changes(), full pytest (paste the summary), update the ledger row 04a note ("follow-up fixes after verify, checked by tests"), AI_WORKLOG entry.
6. Commit "INGEST-004: follow-up fixes from verify" on ingest-004, then push ingest-004 including the verifier's commit a142387 (it is local-only). Do not merge. STOP.

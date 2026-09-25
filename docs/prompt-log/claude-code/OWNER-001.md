Task OWNER-001 — apply the owner's decisions from the EVAL-001 re-check and the 2026-09-25 session handoff.
Read agents/prompts/_common.md first and follow it. No pipeline code changes; do not start EVAL-002.

Entry: dev is up to date; INGEST-003 is `verified` in docs/plans/task-ledger.md and V-2 passed on Windows 3.13.3. Otherwise STOP.

1. Fill docs/reviews/evaluation/EVAL-001-owner-recheck.md with these owner verdicts, verbatim, marked "owner, 2026-09-25":
   - 009 and 010: ok
   - 016: change: remove alternate #20 "Familiar C# features" (states collections are reference types but not assignment semantics → false hit); keep both #07 alternates.
   - 022: ok — add a validator test that 022 has two slots (S1 Redirects, S2 ReExecute).
   - 023: ok
   - 024: change: P1 → "Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying."
   - 025: ok
   - 031: ok
   - 036: ok
   - Other changes table: ok — condition: EVAL-003b reports source/section hit both strict (expected sources only) and lenient (with alternates).
   - Additional change 017: split slots — S1 = H1 intro (+ the "Additional resources" alternates that hold variant intros), S2 = "IMiddleware" (+ #10 "Service lifetimes"); P2/P3 evidence is in the intro, P1 in IMiddleware. Update its citation criteria to one citation per slot.
2. Apply the changes to data/evaluation/questions/blueprint.yaml (016, 024, 017; add the 022 test). Keep every evidence quote verbatim; run the blueprint tests. Update coverage-matrix.yaml / evaluation-dataset-design.md only where counts change.
3. Strict vs lenient retrieval: add to docs/specs/evaluation-spec.md and agents/prompts/09b-EVAL-003b-metrics-and-judge.md (+ a test case: slots S1={04}, S2={26,20}; top-k {04,20} → lenient hit, strict miss). Log in agents/prompts/CHANGELOG.md.
4. Owner accepts the AI decisions from docs/plans/session-handoff-2026-09-25-autonomous.md: OD-6 single MarkItDownParser; converted formats skip the ADR-0003 D1 normalizer (change the ADR-0002 amendment from "pending owner review" to accepted); per-format converters; markitdown[pdf,docx] dependency. N1/N2 stay deferred: record them as known limitations (ledger open items + a "Limitations" note for the final README).
5. Ledger rows, AI_WORKLOG entry, commit on a new branch owner-001, push, open a PR into dev. STOP — the owner runs 99-VERIFY for OWNER-001.

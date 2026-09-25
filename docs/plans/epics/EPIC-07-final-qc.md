# EPIC-07-final-qc

Status: not started.

Target: Wed 30 Sep – Thu 1 Oct 2026 (Phase 4). 🔴 Deadline: 2026-10-01 (final submission).

Scope: root README (dataset description plus the submission sections: problem, solution, architecture/workflow, AI usage, completed work, limitations), `AI_WORKLOG.md` summary, demo video script (≤ 5 min), GitHub push, brief traceability checklist, final checks (tests, secret scan, excluded docs unused, sources unchanged), final report, submission. Deliverables and exit gate G7: [master-plan.md](../master-plan.md#epic-07-final-qc).

## Known limitations (for the README "Limitations" section)
Collected as tasks record them; QC-001 copies them into the root README.
- **Converted formats (PDF, HTML, DOCX, txt) skip MarkItDown's post-clean-up** (owner, 2026-09-25, OWNER-001; INGEST-003 re-verify note N1). The adapter calls each format's MarkItDown converter directly, so trailing spaces per line are kept, 3+ blank lines are not collapsed, and a PDF can end with a form-feed line. Chunk offsets stay exact; the Markdown corpus is unaffected. Deferred: fix it with a test before any converted format is used in evaluation.
- **Binary content in a `.txt` file is read as text** (owner, 2026-09-25, OWNER-001; INGEST-003 note N2). No format sniffing for plain text; covered only by the per-format spot-check rule (`docs/specs/ingestion-spec.md`).

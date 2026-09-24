# QC-001 — README, AI_WORKLOG, final checks, GitHub, demo video script (gate G7)

Read `agents/prompts/_common.md` first and follow it.
Entry: EXP-001 done (BONUS optional).

## Do
1. **Root `README.md`** (English, concise, every number linked to a report/results file):
   Problem · Solution · Dataset (24 docs, sources, why 4 excluded, why no #25) · Architecture & workflow (Mermaid: Documents → Parsing → Normalization → Chunking A/B → Embedding → Chroma → Retrieval → Gemini → Answer + Citation / insufficient) · How to run (install, `.env`, build chunks, build index, ask CLI, GUI, tests, evaluation) · Evaluation summary · Experiment summary · Bonus (if any) · AI usage (short, link AI_WORKLOG) · Completed work · Limitations (honest) · Repo map.
2. **`AI_WORKLOG.md`** final: fill "Summary: how AI helped", "Incorrect AI outputs and improvements" (from the log — real events only), "With 7 more days". Draft the 7-days list from report limitations, then ASK the user to confirm/edit it.
3. **Traceability** `docs/reviews/milestones/brief-traceability.md`: every brief + submission row → evidence link. Any row not met → fix or list as a limitation.
4. **Final checks** (real output into the QC report): full offline pytest; fresh-clone test (clone to a temp dir, install from `requirements.txt`, run tests — catches missing deps/paths); secret scan incl. git history; excluded docs unused (grep results/indexes); corpus checksums unchanged; `gitnexus_detect_changes()`.
5. **Demo video script** `docs/reports/milestones/demo-video-script.md`, ≤ 5 min with timestamps: problem (20 s) → dataset (20 s) → live GUI: EN answer + citations, VI answer, out-of-corpus refusal (90 s) → pipeline diagram (40 s) → evaluation results (50 s) → experiment + one failure case (50 s) → limitations & next steps (20 s).
6. Ask the user before `git push origin main` and before creating tag `v1.0-submission`.
7. Final report `docs/reports/milestones/final.md`.

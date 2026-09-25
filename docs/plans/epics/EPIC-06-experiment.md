# EPIC-06-experiment

Status: not started.

Target: Tue 29 – Wed 30 Sep 2026 (Phase 3). Deadline for the whole project: 2026-10-01.

Accepted design (ADR-0002, parameters in ADR-0003 D7/D8): Arm A **header-aware chunking** (baseline, max 1,600 chars) against Arm B **fixed-size chunking** (1,600 chars, 200 overlap), with the same normalization and contextual header, one ChromaDB collection per arm, and embedding model, distance metric, top-k = 5, prompt, Gemini model and question set held constant. Evaluated on the same ≥ 30 questions for answer quality, retrieval quality, citation quality and latency, with failure analysis. Results MUST NOT be fabricated.

Deliverables and exit gate G6: [master-plan.md](../master-plan.md#epic-06-experiment).

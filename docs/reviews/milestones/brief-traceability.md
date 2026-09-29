# Brief traceability

Every requirement in `docs/specs/assignment-requirements.md` (the assignment brief, verbatim-in-substance record),
mapped to real evidence. Built at QC-001, from `docs/plans/master-plan.md` §9 (which stated the *plan*; this file
states what actually exists, with a link to each piece of evidence). Any row not met is fixed before this file is
written, or listed as a limitation instead of a false "met".

## Challenge

| Requirement | Met | Evidence |
|---|---|---|
| Dataset ≥ 20 documents | ✅ | 24 accepted sources: [`corpus/manifest.json`](../../../corpus/manifest.json); [`corpus/sources/`](../../../corpus/sources/) |
| Dataset clearly described in the README | ✅ | [`README.md`](../../../README.md) § Dataset |

## Minimum RAG pipeline (Documents → Parsing → Chunking → Embedding → Retrieval → LLM → Answer + Citation)

| Stage | Met | Evidence |
|---|---|---|
| Parsing | ✅ | Markdown parser + MarkItDown adapter (PDF/HTML/DOCX/txt): `src/knowledge_assistant/infrastructure/parsing/`; [INGEST-001](../../reports/execution/INGEST-001.md), [INGEST-003](../../reports/execution/INGEST-003.md) |
| Chunking | ✅ | Two chunkers (header-aware Arm A, fixed-size Arm B): `src/knowledge_assistant/infrastructure/chunking/`; [INGEST-002](../../reports/execution/INGEST-002.md), [INGEST-004](../../reports/execution/INGEST-004.md) |
| Embedding | ✅ | `gemini-embedding-001`, cached: `src/knowledge_assistant/infrastructure/embeddings/`; [RAG-001a](../../reports/execution/RAG-001a.md) |
| Retrieval | ✅ | ChromaDB, top-5 + score gate: `src/knowledge_assistant/infrastructure/vector_store/`; [RAG-001b](../../reports/execution/RAG-001b.md), [RAG-002](../../reports/execution/RAG-002.md) |
| LLM | ✅ | `gemini-3.5-flash-lite` + `gemini-3.5-flash` fallback: `src/knowledge_assistant/infrastructure/llm/gemini/`; [RAG-003](../../reports/execution/RAG-003.md) |
| Answer + Citation | ✅ | Heading-path citations, grounded generation: [RAG-002](../../reports/execution/RAG-002.md); live smoke: [`smoke-2026-09-29.md`](../../../validation/generation/smoke-2026-09-29.md) |

## Minimum requirements

| Requirement | Met | Evidence |
|---|---|---|
| Document ingestion | ✅ | 24/24 docs normalized + chunked (both arms); [INGEST-001/002/003/004](../../reports/execution/) |
| Search / retrieval | ✅ | ChromaDB, both arms indexed (Arm A 733, Arm B 859, confirmed at QC-001); [`docs/reports/epics/EPIC-05-evaluation.md`](../../reports/epics/EPIC-05-evaluation.md) § Retrieval metrics |
| Answer generation | ✅ | [RAG-002](../../reports/execution/RAG-002.md), [RAG-003](../../reports/execution/RAG-003.md); GUI + CLI both call the same use case |
| Citation of relevant sources | ✅ | `source_precision` 1.000, `section_precision` 0.977 (n=58); [EPIC-05 § Citation metrics](../../reports/epics/EPIC-05-evaluation.md#citation-metrics) |
| Says when information is insufficient | ✅ | Retrieval-score gate (0.686) + LLM-level refusal; `correct_refusal_rate` 1.000/8, 0 hallucinations; [EPIC-05 § Refusal metrics](../../reports/epics/EPIC-05-evaluation.md#refusal-metrics); live proof: [`smoke-2026-09-29.md`](../../../validation/generation/smoke-2026-09-29.md) Q-DEV-005 |
| Answers grounded in the collection (not the LLM's general knowledge) | ✅ | Prompt restricts generation to retrieved passages (`config/prompts/answer_v2.md`); `groundedness_rate` 0.965 overall (55/57); per-arm 0.926 / 1.000 (Arm A / Arm B; [EPIC-06 § 3](../../reports/epics/EPIC-06-experiment.md)); [EPIC-05](../../reports/epics/EPIC-05-evaluation.md) |

## Evaluation

| Requirement | Met | Evidence |
|---|---|---|
| ≥ 30 questions, 5 fields each (question, ground truth, expected source, generated answer, result) | ✅ | 36 questions (32 answerable + 4 insufficient) × 2 arms = 72 records; [`data/evaluation/questions/eval-v1.jsonl`](../../../data/evaluation/questions/eval-v1.jsonl); brief's 5-column appendix: [`data/evaluation/results/eval-table-eval-004-appendix.md`](../../../data/evaluation/results/eval-table-eval-004-appendix.md) |
| Report covers answer, retrieval, citation, latency, with method + summary | ✅ | [`docs/reports/epics/EPIC-05-evaluation.md`](../../reports/epics/EPIC-05-evaluation.md) — one section per metric family, "How measured" + "Observation" under each |

## Experiment

| Requirement | Met | Evidence |
|---|---|---|
| ≥ 2 approaches compared | ✅ | Arm A (header-aware) vs Arm B (fixed-size); [`docs/reports/epics/EPIC-06-experiment.md`](../../reports/epics/EPIC-06-experiment.md) § 1 |
| What was changed | ✅ | EPIC-06 § 1 |
| How each approach was evaluated | ✅ | EPIC-06 § 2 (same runner, same metrics, paired McNemar + bootstrap CI) |
| The results | ✅ | EPIC-06 § 3 (AUTO-generated tables from the committed runs) |
| Why the results differ | ✅ | EPIC-06 § 4 (23 discordant cases, each with chunk-level evidence) |
| What was learned | ✅ | EPIC-06 § 5 |
| Evidence-based, not just a claim | ✅ | EPIC-06's tables are generated from the committed runs and `data/experiments/exp-001/`; the verifier re-derived them at [EXP-001-verify](../../reviews/evaluation/EXP-001-verify.md) |
| Failure analysis (grading emphasis) | ✅ | EPIC-06 § "Failure analysis" — every ADR-0003 predicted failure mode checked against real case IDs |

## Bonus (extra credit)

| Item | Done? | Evidence |
|---|---|---|
| Reranking | No | Not attempted (`BONUS-001`, `not started`) |
| Hybrid search | No | Not attempted (`BONUS-001`, `not started`) |
| Query rewriting | No | Not attempted (OD-16, stretch, not reached before the deadline) |
| Agentic RAG | No | Out of scope for this project |
| Automated evaluation | Partial | The LLM judge (`scripts/evaluation/judge_run.py`) automates answer/citation scoring, spot-checked by the owner for reliability; [EPIC-05 § Judge reliability](../../reports/epics/EPIC-05-evaluation.md#judge-spot-check-agreement-owner) |
| Cost benchmarking | Partial | [EPIC-05 § Cost](../../reports/epics/EPIC-05-evaluation.md#cost-estimate) reports a list-price estimate for the evaluation runs (actual free-tier usage: $0) |

## Evaluation focus (grading emphasis)

| Emphasis | Evidence |
|---|---|
| Experiment design | [`docs/reports/epics/EPIC-06-experiment.md`](../../reports/epics/EPIC-06-experiment.md) § 1–2 |
| Evaluation | [`docs/reports/epics/EPIC-05-evaluation.md`](../../reports/epics/EPIC-05-evaluation.md) |
| Failure analysis | [EPIC-06 § "Failure analysis"](../../reports/epics/EPIC-06-experiment.md) |
| Data and retrieval understanding | [`docs/knowledge/domain/corpus-topic-map.md`](../../knowledge/domain/corpus-topic-map.md), [EPIC-01 report](../../reports/epics/EPIC-01-corpus-analysis.md) |
| Ability to prove system improvements | Every experiment claim carries a McNemar p-value and 95% CI, not just a direction; [EPIC-06 § 3](../../reports/epics/EPIC-06-experiment.md) |

## Submission

| Requirement | Met | Evidence |
|---|---|---|
| Working product (prototype/demo) or link | ✅ (desktop app, no hosted link — see README) | [`README.md`](../../../README.md) § Working product |
| GitHub repository | ✅ | [github.com/PotatoMine725/Tech-docs-RAG](https://github.com/PotatoMine725/Tech-docs-RAG); **not on `main` yet**: PR #22 (`qc-001` → `dev`) and PR #23 (`dev` → `main`) are unmerged drafts awaiting the owner |
| README: problem, solution, architecture/workflow, AI usage, completed work, limitations + dataset description | ✅ | [`README.md`](../../../README.md), all sections present |
| Demo video ≤ 5 minutes | ❌ not done — script done; recording is the owner's step | [`docs/reports/milestones/demo-video-script.md`](../../reports/milestones/demo-video-script.md) |
| `AI_WORKLOG.md`: tools, how AI helped, incorrect outputs + fixes, 7 more days | ✅ | [`AI_WORKLOG.md`](../../../AI_WORKLOG.md) — filled at QC-001; "7 more days" confirmed by the owner 2026-09-29 |
| Originality (can explain everything, no fake functionality) | ✅ | Every task's execution report has an "Explain it back" section (see `docs/reports/execution/*.md`); this QC pass ran the whole pipeline live rather than trusting prior claims |
| Quality (small and working beats large and not understood) | ✅ | 866 offline tests, fresh-clone install verified end to end (QC-001; owner-run on Windows/PowerShell in a fresh clone of `qc-001`, 2026-09-29: install and activation worked verbatim, under 1 minute with a warm pip cache, offline tests all passed, no errors — [report](../../reports/execution/QC-001.md)); known gaps are listed in [`README.md`](../../../README.md) § Limitations |

## Notes on this file's own honesty

This table was built by re-deriving each "met" from a real file or a real command run during QC-001 (see
[`docs/reports/execution/QC-001.md`](../../reports/execution/QC-001.md) for the commands and their output), not by
copying the plan's intentions from `master-plan.md` §9. Rows marked "No" or "Partial" are true gaps, listed here and
in `README.md` § Limitations / § Bonus rather than hidden.

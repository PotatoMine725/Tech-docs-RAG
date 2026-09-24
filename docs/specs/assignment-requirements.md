# Assignment requirements (source of truth)

Verbatim-in-substance record of the challenge brief supplied by the user on 2026-09-24. Other specs refine this file; they must not contradict it.

**Title:** Build a RAG System That Can Prove It Works. Simply calling an LLM API is not considered AI Engineering.

## Challenge
Build a Knowledge Assistant that answers questions from a defined document collection.
- Dataset: at least **20 documents** (PDF, documentation, regulations, academic papers, public company documents, technical documents, ...).
- The dataset must be clearly described in the **README**.

## Minimum RAG pipeline
Documents -> Parsing -> Chunking -> Embedding -> Retrieval -> LLM -> Answer + Citation

## Minimum requirements
- Document ingestion
- Search / retrieval
- Answer generation
- Citation of relevant sources
- Ability to indicate that available information is **insufficient** to answer
- Answers must be **grounded in the collection**, not generated from the LLM's general knowledge

## Evaluation
Build an evaluation dataset of at least **30 questions**. For each record: question, expected answer / ground truth, expected source, generated answer, result.

Evaluation report must cover at least: **answer quality, retrieval quality, citation quality, latency** - and explain how each metric was measured and summarize results.

## Experiment
Compare at least **2 approaches** (examples: chunk size 300 vs 800; vector vs hybrid search; baseline vs reranking). Explain:
1. what was changed
2. how each approach was evaluated
3. the results
4. why the results differ
5. what was learned

The goal is to demonstrate the difference with evidence from the evaluation, not merely claim one is better.

## Bonus (extra credit)
Reranking, hybrid search, query rewriting, agentic RAG, automated evaluation, cost benchmarking.

## Evaluation focus (grading emphasis)
Experiment design; evaluation; failure analysis; data and retrieval understanding; ability to prove system improvements.

## Submission
Added 2026-09-24 (HOUSE-001) from the owner's record of the brief; not in the first version of this file.
- **Working product:** a prototype or demo link, and the GitHub repository.
- **README** covering: the problem, the solution, architecture/workflow, AI usage, completed work, limitations, plus the dataset description (above).
- **Demo video:** at most 5 minutes.
- **`AI_WORKLOG.md`:** the AI tools used, how AI helped, incorrect AI outputs and how they were improved, and what would be improved with 7 more days.
- **Originality:** the author must understand and be able to explain everything; no fake functionality.
- **Quality:** a small system that works beats a large one that is not understood.

## Status against this brief (updated 2026-09-24, HOUSE-001)
| Requirement | Status |
|---|---|
| >= 20 documents | 24 accepted sources in `corpus/sources/` (met) |
| README describing dataset | draft dataset section in root `README.md` (EPIC-01); other README sections in EPIC-07 |
| Pipeline, ingestion, retrieval, generation, citation, insufficient-info | not started (skeletons only) |
| >= 30 eval questions with 5 fields | not started (design: EVAL-001) |
| Report: quality / retrieval / citation / latency | not started |
| >= 2-approach experiment | approach decided (ADR-0003 D7: header-aware vs fixed-size chunking); not run |
| Working product / demo link | not started |
| GitHub repository | remote `origin` = github.com/PotatoMine725/Tech-docs-RAG; nothing pushed by the AI so far |
| README: problem, solution, architecture/workflow, AI usage, completed work, limitations | not started (EPIC-07) |
| Demo video <= 5 min | not started (EPIC-07 script; recorded by the owner) |
| `AI_WORKLOG.md` | created (HOUSE-001); summary sections filled at QC-001 |
| Originality / quality | ongoing: every task ends with an "Explain it back" section |

Note: this brief contains no chunking requirements; chunk size is only offered as an example experiment. The chunking experiment was decided later in ADR-0003.

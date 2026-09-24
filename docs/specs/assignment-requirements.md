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

## Status against this brief (2026-09-24)
| Requirement | Status |
|---|---|
| >= 20 documents | 24 accepted sources in `corpus/sources/` (met) |
| README describing dataset | not yet written (root README missing) - TODO |
| Pipeline, ingestion, retrieval, generation, citation, insufficient-info | not started (skeletons only) |
| >= 30 eval questions with 5 fields | not started |
| Report: quality / retrieval / citation / latency | not started |
| >= 2-approach experiment | not started; approach TBD (DECISION REQUIRED) |

Note: this brief contains no chunking requirements. Chunking strategy remains undecided; chunk size is only offered as an example experiment.

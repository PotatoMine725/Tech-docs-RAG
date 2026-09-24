# Evaluation specification

Status: skeleton. Undecided items are TBD / DECISION REQUIRED.

## Known facts
- At least 30 questions; each case: question, expected answer/ground truth, expected source, generated answer, result.
- Dimensions: answer quality, retrieval quality, citation quality, latency. Metrics: TBD.

## Requirements
Source: `assignment-requirements.md`. Report must explain how each metric was measured. Failure analysis and evidence for any claimed improvement are graded emphasis. Metric definitions: TBD.

## Chunking experiment (ADR-0003 D7-D8, accepted)
- Arms: header-aware (max 1,600 chars) vs fixed-size (1,600 chars, 200 overlap); one ChromaDB collection per arm; embedding model, distance metric, top-k=5, prompt, Gemini model and question set held constant.
- Retrieval metrics: source hit@5, section hit@5 (char-span overlap with expected section; any version variant counts), MRR. Also answer quality (rubric), citation quality (cited chunk contains evidence), per-stage latency, and per-arm chunk statistics.
- Ground truth (expected `source_id` + heading path) is written before indexes are built. Questions must cover small docs as well as #13/#17/#23.
- Query language: English + Vietnamese (ADR-0003 D9). Each case has a `language` field; metrics reported overall and per language; a parallel EN/VI subset (same ground truth) isolates the cross-lingual effect.
- Answer model and LLM judge: `gemini-3.5-flash-lite` (ADR-0004). Judge verdicts are spot-checked manually on a sample (self-grading bias). Each result records the model that produced the answer and the retry/fallback count; retried calls are reported separately in latency statistics.
- Optional: <= 20-question subset answered by `gemini-3.5-flash` for an answer-model comparison.

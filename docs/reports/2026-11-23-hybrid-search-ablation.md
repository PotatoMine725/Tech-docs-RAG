# Hybrid search ablation: dense / sparse / hybrid × Gemini / EmbeddingGemma (plan step 4a)

Date: 2026-11-23. Commit of every run: `44f25e6` (branch `hybrid-search`). 21 runs recorded a clean tree. Three
runs recorded `git_dirty: true` because docs were being edited while they ran: `dev-B-…-local-hybrid` and
`eval-A-…-local-hybrid` (`.env.example`) and `eval-B-…-local-hybrid` (`.env.example`, `docs/specs/retrieval-spec.md`).
No code file was dirty and neither file is read at runtime (`.env.example` is never loaded), so the results stand.
Decision record: ADR-0007.
Retrieval only: 24 runs, **0 LLM requests, 0 embedding API requests** (every query embedding was cached; all 24 runs
finished with every case ok, no errors). No question file was written or changed.

## Setup
- Modes: `dense` (Chroma, unchanged), `sparse` (SQLite FTS5 BM25 on the original question), `hybrid` (Reciprocal
  Rank Fusion, k = 60, over dense top 15 and BM25 top 15, then passage dedup to top 5).
- Embedders: `gemini-embedding-001@768` (default) and `embeddinggemma-300m-5090578d-fp32-t2048@768` (local).
- Arms A (header-1600, 733 chunks) and B (fixed-1600, 859 chunks); keyword index built from the same chunk files
  (733 / 859 rows, MATCH with the chunk files; `validation/retrieval/indexing-log.jsonl`).
- Splits: eval (36 cases: 32 answerable, 16 EN + 16 VI; 4 unanswerable) and dev (6 cases: 4 answerable, 2
  unanswerable; no span ground truth, so only source hit rates).
- Run ids: `20261123-<split>-<arm>-retrieval-<gemini|local>-<dense|sparse|hybrid>-44f25e6` under
  `data/evaluation/results/`. Tables: `scripts/evaluation/compare_retrieval_runs.py --no-cases --runs ...`
  (appendix); per-case wins/losses from the same scoring code (`eval_report_data.score_runs`).
- Gate: the dense top-1 score of the active embedder in every mode (ADR-0007 D6), so the gate columns are the same
  for dense, sparse and hybrid of one embedder. Sparse rankings do not use the embedder: the gemini and local sparse
  runs of an arm have identical rankings and differ only in the gate column, so they are one result, shown once.

## Regression check: dense mode is unchanged
The new dense runs were compared case by case with the recorded runs (same chunk_id lists, `gate_fired`, and every
score):

| recorded run | new run | cases compared | chunk lists differ | gate differs | max score diff |
|---|---|---|---|---|---|
| 20261123-{dev,eval}-{A,B}-retrieval-local-4937f03 (4 runs) | ...-local-dense-44f25e6 | 6+6+36+36 | 0 | 0 | 0 |
| 20260927-dev-A-retrieval-05680f9 | dev-A-retrieval-gemini-dense-44f25e6 | 3 (the recorded run has 3 ok cases) | 0 | 0 | 0 |
| 20260928-eval-{A,B}-full-491f137 (retrieval fields) | eval-{A,B}-retrieval-gemini-dense-44f25e6 | 36+36 | 0 | 0 | 0 |

There is no recorded Gemini dev-B run, so `dev-B-retrieval-gemini-dense-44f25e6` is new, not a comparison.

## Results: eval split, answerable cases (n = 32; one case = 0.031)

| arm | embedder | mode | expected source top-1 | section_hit@1 | section_hit@5 | evidence_hit@5 | MRR |
|---|---|---|---|---|---|---|---|
| A | gemini | dense | 32/32 | 0.812 | 0.938 | 0.938 | 1.000 |
| A | gemini | hybrid | 32/32 | 0.781 | 0.938 | 0.875 | 0.969 |
| A | local | dense | 30/32 | 0.750 | 0.906 | 0.719 | 0.961 |
| A | local | hybrid | 30/32 | 0.719 | 0.875 | 0.812 | 0.919 |
| A | — | sparse | 27/32 | 0.719 | 0.844 | 0.812 | 0.858 |
| B | gemini | dense | 32/32 | 0.844 | 0.938 | 0.844 | 0.984 |
| B | gemini | hybrid | 32/32 | 0.844 | 0.969 | 0.781 | 1.000 |
| B | local | dense | 29/32 | 0.750 | 0.875 | 0.719 | 0.938 |
| B | local | hybrid | 31/32 | 0.812 | 0.906 | 0.812 | 0.959 |
| B | — | sparse | 28/32 | 0.750 | 0.906 | 0.750 | 0.885 |

Expected source in top-5 is 32/32 everywhere except local dense arm B (31/32).

### Per case: hybrid against dense (eval, answerable)

| arm | embedder | section_hit@5 better / worse | evidence_hit@5 better / worse |
|---|---|---|---|
| A | gemini | +1 / −1 (022 vi / 009 en) | +1 / −3 (022 vi / 006 vi, 009 en, 026 vi) |
| A | local | +0 / −1 (009 en) | +4 / −1 (005 en, 007 en, 008 vi, 022 vi / 009 en) |
| B | gemini | +1 / −0 (031 en) | +2 / −4 (018 vi, 027 en / 006 vi, 009 en, 010 vi, 032 vi) |
| B | local | +2 / −1 (016 vi, 029 en / 031 en) | +5 / −2 (005 en, 018 vi, 022 vi, 025 en, 029 en / 009 en, 010 vi) |

(Case ids are `Q-EVAL-0nn`. No significance test was run; with 32 cases these counts are indications, not proof.)

### Per language (eval, answerable, n = 16 each)

| arm | embedder | mode | EN section_hit@5 | EN evidence_hit@5 | VI section_hit@5 | VI evidence_hit@5 | gate refuses answerable EN / VI |
|---|---|---|---|---|---|---|---|
| A | gemini | dense | 1.000 | 1.000 | 0.875 | 0.875 | 1/16 / 2/16 |
| A | gemini | hybrid | 0.938 | 0.938 | 0.938 | 0.812 | 1/16 / 2/16 |
| A | local | dense | 0.938 | 0.812 | 0.875 | 0.625 | 1/16 / 4/16 |
| A | local | hybrid | 0.875 | 0.875 | 0.875 | 0.750 | 1/16 / 4/16 |
| A | — | sparse | 0.812 | 0.875 | 0.875 | 0.750 | (as dense of the embedder) |
| B | gemini | dense | 0.938 | 0.938 | 0.938 | 0.750 | 0/16 / 2/16 |
| B | gemini | hybrid | 1.000 | 0.938 | 0.938 | 0.625 | 0/16 / 2/16 |
| B | local | dense | 0.938 | 0.812 | 0.812 | 0.625 | 0/16 / 5/16 |
| B | local | hybrid | 0.938 | 0.938 | 0.875 | 0.688 | 0/16 / 5/16 |
| B | — | sparse | 0.938 | 0.875 | 0.875 | 0.625 | (as dense of the embedder) |

Unanswerable eval cases refused by the gate (all modes): gemini 3/4, local 2/4 on each arm.

### Dev split (6 cases)
Expected source in top-5: 4/4 in every run. Expected source in top-1: 4/4, except sparse arm B (3/4; one VI case).
Gate: no answerable dev case refused in any run; unanswerable refused gemini 2/2 (both arms), local 1/2 (A), 0/2 (B).
The dev split has no span ground truth, so it cannot show section or evidence differences.

## Reading
- **Local embedder:** hybrid lifts evidence_hit@5 on both arms (A 0.719 → 0.812, B 0.719 → 0.812; +4/−1 and +5/−2
  cases) and source top-1 on B (29 → 31). section_hit@5 moves by one case (A −1, B +1). In Vietnamese questions,
  evidence_hit@5 goes 0.625 → 0.750 (A) and 0.625 → 0.688 (B). BM25 on the original Vietnamese question matches through
  the English words the question contains. Checked on the sparse runs: for all 16 VI answerable eval questions on
  both arms, the words the question shares with its sparse top-1 chunk are ASCII only (no Vietnamese word). Examples:
  Q-EVAL-022 matches `usestatuscodepageswithredirects`, `status`, `code`, `url`, `client`; Q-EVAL-008 matches
  `404`, `api`, `id`, `int`. Every sparse eval and dev question matched at least one chunk (0 errors).
- **Gemini:** hybrid does not help on this set. evidence_hit@5 drops (A 0.938 → 0.875, B 0.844 → 0.781; −3/+1 and
  −4/+2 cases, mostly VI), and section_hit@5 is flat or +1. Sparse alone is below Gemini dense on every eval metric
  except expected source in top-5 (32/32 for both).
- **Sparse alone** matches local dense on evidence_hit@5 or beats it (A 0.812 vs 0.719, B 0.750 vs 0.719) but is
  worse on top-1 and MRR.
- **Gate:** unchanged by design (dense top-1). The local gate still refuses 5/32 answerable eval questions on each arm,
  4 or 5 of them Vietnamese. Whatever hybrid retrieves, the gate decision is the same as in dense mode. Changing it
  needs the reranker's absolute score (plan §7.1, ADR-0007 D6, TBD) or a different local threshold rule (owner's call,
  retrieval-spec.md).

## Caveats (honest limits of this benchmark)
- **Ceiling.** Gemini dense is already at 0.938 (30/32) section_hit@5 on both arms and 0.938 evidence_hit@5 on arm A,
  with source top-1 at 32/32. On those metrics only two cases of headroom are left, so they cannot show a hybrid gain
  for Gemini. The ceiling does **not** explain everything: Gemini arm B evidence_hit@5 is 0.844 (27/32, five cases of
  headroom), and hybrid still went down there (−4/+2, mostly VI). No significance test was run; differences of one
  to three cases are indications only. As plan §7.1 says, the
  benchmark needs exact-identifier questions (class names, method names, error codes, where keyword search should
  help) and Vietnamese-corpus questions before hybrid can be judged.
- **Vietnamese tokenization is not validated.** The corpus is English only. The VI numbers above measure Vietnamese
  *questions* over English *documents*, which mostly match through embedded English terms. They say nothing about
  the tokenizer choice. ADR-0007 D3 (`remove_diacritics 0`, diacritics kept) is PROVISIONAL. The plan §2 design
  (syllable + bigram tokens plus a diacritic-stripped copy) is TBD / DECISION REQUIRED until Vietnamese documents
  and questions exist, including questions typed without diacritics.
- Small samples: 16 questions per language, 6 dev cases. No significance test.
- Latency and memory of the keyword index were not measured in a controlled way (TBD with the reranker step).

## Next steps
1. Extend the benchmark (owner task; no question file was written here): exact-identifier questions, and Vietnamese
   documents with VI questions (with and without diacritics). Ground truth is written before the indexes are
   rebuilt (CLAUDE.md rule 9).
2. Reranker (plan step 4b) and an absolute-score gate for hybrid mode (ADR-0007 D6 TBD).
3. Re-run this ablation, plus hybrid + rerank, on the extended benchmark. Then decide whether the default mode
   changes (it stays `dense` until then).

## Appendix: generated tables (`compare_retrieval_runs.py --no-cases`, verbatim)

### eval

| run | retrieval | embedding model | threshold | cases | errors | answerable | expected source in top-1 | expected source in top-5 | source_hit@1 | section_hit@1 | evidence_hit@1 | source_hit@5 | section_hit@5 | evidence_hit@5 | mrr | answerable top-1 | unanswerable top-1 | gate fired: answerable | gate fired: unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261123-eval-A-retrieval-gemini-dense-44f25e6 | dense | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 32/32 (1.000) | 32/32 (1.000) | 0.875 | 0.812 | 0.594 | 0.969 | 0.938 | 0.938 | 1.000 | 0.6269–0.8091 (median 0.7500) | 0.6481–0.7540 (median 0.6635) | 3/32 (0.094) | 3/4 (0.750) |
| 20261123-eval-A-retrieval-gemini-sparse-44f25e6 | sparse | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 27/32 (0.844) | 32/32 (1.000) | 0.812 | 0.719 | 0.469 | 0.875 | 0.844 | 0.812 | 0.858 | 0.6269–0.8091 (median 0.7500) | 0.6481–0.7540 (median 0.6635) | 3/32 (0.094) | 3/4 (0.750) |
| 20261123-eval-A-retrieval-gemini-hybrid-44f25e6 | hybrid | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 32/32 (1.000) | 32/32 (1.000) | 0.875 | 0.781 | 0.531 | 0.969 | 0.938 | 0.875 | 0.969 | 0.6269–0.8091 (median 0.7500) | 0.6481–0.7540 (median 0.6635) | 3/32 (0.094) | 3/4 (0.750) |
| 20261123-eval-A-retrieval-local-dense-44f25e6 | dense | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 30/32 (0.938) | 32/32 (1.000) | 0.812 | 0.750 | 0.406 | 0.906 | 0.906 | 0.719 | 0.961 | 0.4121–0.7766 (median 0.6300) | 0.4872–0.7146 (median 0.5557) | 5/32 (0.156) | 2/4 (0.500) |
| 20261123-eval-A-retrieval-local-sparse-44f25e6 | sparse | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 27/32 (0.844) | 32/32 (1.000) | 0.812 | 0.719 | 0.469 | 0.875 | 0.844 | 0.812 | 0.858 | 0.4121–0.7766 (median 0.6300) | 0.4872–0.7146 (median 0.5557) | 5/32 (0.156) | 2/4 (0.500) |
| 20261123-eval-A-retrieval-local-hybrid-44f25e6 | hybrid | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 30/32 (0.938) | 32/32 (1.000) | 0.812 | 0.719 | 0.469 | 0.906 | 0.875 | 0.812 | 0.919 | 0.4121–0.7766 (median 0.6300) | 0.4872–0.7146 (median 0.5557) | 5/32 (0.156) | 2/4 (0.500) |
| 20261123-eval-B-retrieval-gemini-dense-44f25e6 | dense | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 32/32 (1.000) | 32/32 (1.000) | 0.875 | 0.844 | 0.406 | 0.938 | 0.938 | 0.844 | 0.984 | 0.6246–0.8127 (median 0.7388) | 0.6467–0.6908 (median 0.6603) | 2/32 (0.062) | 3/4 (0.750) |
| 20261123-eval-B-retrieval-gemini-sparse-44f25e6 | sparse | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 28/32 (0.875) | 32/32 (1.000) | 0.812 | 0.750 | 0.438 | 0.906 | 0.906 | 0.750 | 0.885 | 0.6246–0.8127 (median 0.7388) | 0.6467–0.6908 (median 0.6603) | 2/32 (0.062) | 3/4 (0.750) |
| 20261123-eval-B-retrieval-gemini-hybrid-44f25e6 | hybrid | gemini-embedding-001@768 | 0.686 | 36 | 0 | 32 | 32/32 (1.000) | 32/32 (1.000) | 0.875 | 0.844 | 0.375 | 0.969 | 0.969 | 0.781 | 1.000 | 0.6246–0.8127 (median 0.7388) | 0.6467–0.6908 (median 0.6603) | 2/32 (0.062) | 3/4 (0.750) |
| 20261123-eval-B-retrieval-local-dense-44f25e6 | dense | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 29/32 (0.906) | 31/32 (0.969) | 0.781 | 0.750 | 0.438 | 0.875 | 0.875 | 0.719 | 0.938 | 0.3755–0.7634 (median 0.6291) | 0.4719–0.6522 (median 0.5731) | 5/32 (0.156) | 2/4 (0.500) |
| 20261123-eval-B-retrieval-local-sparse-44f25e6 | sparse | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 28/32 (0.875) | 32/32 (1.000) | 0.812 | 0.750 | 0.438 | 0.906 | 0.906 | 0.750 | 0.885 | 0.3755–0.7634 (median 0.6291) | 0.4719–0.6522 (median 0.5731) | 5/32 (0.156) | 2/4 (0.500) |
| 20261123-eval-B-retrieval-local-hybrid-44f25e6 | hybrid | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 36 | 0 | 32 | 31/32 (0.969) | 32/32 (1.000) | 0.844 | 0.812 | 0.469 | 0.969 | 0.906 | 0.812 | 0.959 | 0.3755–0.7634 (median 0.6291) | 0.4719–0.6522 (median 0.5731) | 5/32 (0.156) | 2/4 (0.500) |

| run | retrieval | language | answerable n | expected source in top-1 | expected source in top-5 | source_hit@1 | section_hit@1 | evidence_hit@1 | source_hit@5 | section_hit@5 | evidence_hit@5 | mrr | gate fired: answerable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261123-eval-A-retrieval-gemini-dense-44f25e6 | dense | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.625 | 1.000 | 1.000 | 1.000 | 1.000 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-gemini-dense-44f25e6 | dense | vi | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.562 | 0.938 | 0.875 | 0.875 | 1.000 | 2/16 (0.125) |
| 20261123-eval-A-retrieval-gemini-sparse-44f25e6 | sparse | en | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.875 | 0.750 | 0.500 | 0.875 | 0.812 | 0.875 | 0.846 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-gemini-sparse-44f25e6 | sparse | vi | 16 | 13/16 (0.812) | 16/16 (1.000) | 0.750 | 0.688 | 0.438 | 0.875 | 0.875 | 0.750 | 0.870 | 2/16 (0.125) |
| 20261123-eval-A-retrieval-gemini-hybrid-44f25e6 | hybrid | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.750 | 0.500 | 1.000 | 0.938 | 0.938 | 0.938 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-gemini-hybrid-44f25e6 | hybrid | vi | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.562 | 0.938 | 0.938 | 0.812 | 1.000 | 2/16 (0.125) |
| 20261123-eval-A-retrieval-local-dense-44f25e6 | dense | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.375 | 0.938 | 0.938 | 0.812 | 1.000 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-local-dense-44f25e6 | dense | vi | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.750 | 0.688 | 0.438 | 0.875 | 0.875 | 0.625 | 0.922 | 4/16 (0.250) |
| 20261123-eval-A-retrieval-local-sparse-44f25e6 | sparse | en | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.875 | 0.750 | 0.500 | 0.875 | 0.812 | 0.875 | 0.846 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-local-sparse-44f25e6 | sparse | vi | 16 | 13/16 (0.812) | 16/16 (1.000) | 0.750 | 0.688 | 0.438 | 0.875 | 0.875 | 0.750 | 0.870 | 4/16 (0.250) |
| 20261123-eval-A-retrieval-local-hybrid-44f25e6 | hybrid | en | 16 | 15/16 (0.938) | 16/16 (1.000) | 0.812 | 0.688 | 0.438 | 0.938 | 0.875 | 0.875 | 0.887 | 1/16 (0.062) |
| 20261123-eval-A-retrieval-local-hybrid-44f25e6 | hybrid | vi | 16 | 15/16 (0.938) | 16/16 (1.000) | 0.812 | 0.750 | 0.500 | 0.875 | 0.875 | 0.750 | 0.950 | 4/16 (0.250) |
| 20261123-eval-B-retrieval-gemini-dense-44f25e6 | dense | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.312 | 0.938 | 0.938 | 0.938 | 0.969 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-gemini-dense-44f25e6 | dense | vi | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.875 | 0.500 | 0.938 | 0.938 | 0.750 | 1.000 | 2/16 (0.125) |
| 20261123-eval-B-retrieval-gemini-sparse-44f25e6 | sparse | en | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.875 | 0.750 | 0.438 | 0.938 | 0.938 | 0.875 | 0.896 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-gemini-sparse-44f25e6 | sparse | vi | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.750 | 0.750 | 0.438 | 0.875 | 0.875 | 0.625 | 0.875 | 2/16 (0.125) |
| 20261123-eval-B-retrieval-gemini-hybrid-44f25e6 | hybrid | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.312 | 1.000 | 1.000 | 0.938 | 1.000 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-gemini-hybrid-44f25e6 | hybrid | vi | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.875 | 0.438 | 0.938 | 0.938 | 0.625 | 1.000 | 2/16 (0.125) |
| 20261123-eval-B-retrieval-local-dense-44f25e6 | dense | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.500 | 0.938 | 0.938 | 0.812 | 1.000 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-local-dense-44f25e6 | dense | vi | 16 | 13/16 (0.812) | 15/16 (0.938) | 0.688 | 0.688 | 0.375 | 0.812 | 0.812 | 0.625 | 0.875 | 5/16 (0.312) |
| 20261123-eval-B-retrieval-local-sparse-44f25e6 | sparse | en | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.875 | 0.750 | 0.438 | 0.938 | 0.938 | 0.875 | 0.896 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-local-sparse-44f25e6 | sparse | vi | 16 | 14/16 (0.875) | 16/16 (1.000) | 0.750 | 0.750 | 0.438 | 0.875 | 0.875 | 0.625 | 0.875 | 5/16 (0.312) |
| 20261123-eval-B-retrieval-local-hybrid-44f25e6 | hybrid | en | 16 | 16/16 (1.000) | 16/16 (1.000) | 0.875 | 0.812 | 0.500 | 1.000 | 0.938 | 0.938 | 1.000 | 0/16 (0.000) |
| 20261123-eval-B-retrieval-local-hybrid-44f25e6 | hybrid | vi | 16 | 15/16 (0.938) | 16/16 (1.000) | 0.812 | 0.812 | 0.438 | 0.938 | 0.875 | 0.688 | 0.919 | 5/16 (0.312) |

### dev

| run | retrieval | embedding model | threshold | cases | errors | answerable | expected source in top-1 | expected source in top-5 | source_hit@1 | section_hit@1 | evidence_hit@1 | source_hit@5 | section_hit@5 | evidence_hit@5 | mrr | answerable top-1 | unanswerable top-1 | gate fired: answerable | gate fired: unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261123-dev-A-retrieval-gemini-dense-44f25e6 | dense | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7360–0.7943 (median 0.7643) | 0.6710–0.6741 (median 0.6725) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-A-retrieval-gemini-sparse-44f25e6 | sparse | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7360–0.7943 (median 0.7643) | 0.6710–0.6741 (median 0.6725) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-A-retrieval-gemini-hybrid-44f25e6 | hybrid | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7360–0.7943 (median 0.7643) | 0.6710–0.6741 (median 0.6725) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-A-retrieval-local-dense-44f25e6 | dense | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5917–0.7009 (median 0.6461) | 0.5378–0.5869 (median 0.5624) | 0/4 (0.000) | 1/2 (0.500) |
| 20261123-dev-A-retrieval-local-sparse-44f25e6 | sparse | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5917–0.7009 (median 0.6461) | 0.5378–0.5869 (median 0.5624) | 0/4 (0.000) | 1/2 (0.500) |
| 20261123-dev-A-retrieval-local-hybrid-44f25e6 | hybrid | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5917–0.7009 (median 0.6461) | 0.5378–0.5869 (median 0.5624) | 0/4 (0.000) | 1/2 (0.500) |
| 20261123-dev-B-retrieval-gemini-dense-44f25e6 | dense | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7256–0.7882 (median 0.7465) | 0.6707–0.6714 (median 0.6711) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-B-retrieval-gemini-sparse-44f25e6 | sparse | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 3/4 (0.750) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7256–0.7882 (median 0.7465) | 0.6707–0.6714 (median 0.6711) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-B-retrieval-gemini-hybrid-44f25e6 | hybrid | gemini-embedding-001@768 | 0.686 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.7256–0.7882 (median 0.7465) | 0.6707–0.6714 (median 0.6711) | 0/4 (0.000) | 2/2 (1.000) |
| 20261123-dev-B-retrieval-local-dense-44f25e6 | dense | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5823–0.6965 (median 0.6639) | 0.5524–0.5903 (median 0.5713) | 0/4 (0.000) | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-sparse-44f25e6 | sparse | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 3/4 (0.750) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5823–0.6965 (median 0.6639) | 0.5524–0.5903 (median 0.5713) | 0/4 (0.000) | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-hybrid-44f25e6 | hybrid | embeddinggemma-300m-5090578d-fp32-t2048@768 | 0.5417 | 6 | 0 | 4 | 4/4 (1.000) | 4/4 (1.000) | – | – | – | – | – | – | – | 0.5823–0.6965 (median 0.6639) | 0.5524–0.5903 (median 0.5713) | 0/4 (0.000) | 0/2 (0.000) |

| run | retrieval | language | answerable n | expected source in top-1 | expected source in top-5 | source_hit@1 | section_hit@1 | evidence_hit@1 | source_hit@5 | section_hit@5 | evidence_hit@5 | mrr | gate fired: answerable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261123-dev-A-retrieval-gemini-dense-44f25e6 | dense | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-gemini-dense-44f25e6 | dense | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-gemini-sparse-44f25e6 | sparse | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-gemini-sparse-44f25e6 | sparse | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-gemini-hybrid-44f25e6 | hybrid | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-gemini-hybrid-44f25e6 | hybrid | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-dense-44f25e6 | dense | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-dense-44f25e6 | dense | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-sparse-44f25e6 | sparse | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-sparse-44f25e6 | sparse | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-hybrid-44f25e6 | hybrid | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-A-retrieval-local-hybrid-44f25e6 | hybrid | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-dense-44f25e6 | dense | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-dense-44f25e6 | dense | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-sparse-44f25e6 | sparse | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-sparse-44f25e6 | sparse | vi | 2 | 1/2 (0.500) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-hybrid-44f25e6 | hybrid | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-gemini-hybrid-44f25e6 | hybrid | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-dense-44f25e6 | dense | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-dense-44f25e6 | dense | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-sparse-44f25e6 | sparse | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-sparse-44f25e6 | sparse | vi | 2 | 1/2 (0.500) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-hybrid-44f25e6 | hybrid | en | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |
| 20261123-dev-B-retrieval-local-hybrid-44f25e6 | hybrid | vi | 2 | 2/2 (1.000) | 2/2 (1.000) | – | – | – | – | – | – | – | 0/2 (0.000) |

# Corpus 2 ingestion and retrieval-only evaluation (benchmark v1 + v2)

Date: 2026-11-25. Status: **partial**. Local EmbeddingGemma: all runs. Gemini: v1 only. The Gemini corpus-2 index
stopped at the daily embedding quota: the embedder counted 1,100 requests (retries included) for 851 vectors kept
in the cache, 0 in the store (the STOPPED path writes no indexing-log line; this is its record). **Gemini v2
numbers: TBD** after the quota reset (about 1,112 more texts: arm A 194, arm B 840, 78 queries).
Every number below comes from `scripts/evaluation/report_corpus2.py --runs-glob '20261125-*-retrieval-*'`
(42 runs, commit c5a7117, no run git_dirty). No LLM call was made.

## What was built
- **Ingestion** (owner decisions 2026-11-25, ADR-0008 Resolutions): PDF `#`-lines escaped (only C2-21 changed;
  erratum [eval-v2.1](../reviews/evaluation/eval-v2.1-erratum.md), tag `eval-freeze-v2.1`). NFC after conversion:
  C2-07 (26 chars shorter), C2-08 (1,548), C2-25 (reordered marks, same length; not listed in ADR-0008 before).
  Corpus 1 and all questions were already NFC; corpus-1 `normalized.jsonl` and chunks are byte-identical.
- **Chunks** (same arm configs as corpus 1): arm A `header-1600` 1,045 chunks, arm B `fixed-1600` 840, 24 documents.
- **Indexes** (own directories, `config.corpus_scoped`): EmbeddingGemma FP32 and FTS5 for both arms, counts
  match the chunk files. Gemini: TBD (quota).
- **Run dimension:** `RunConfig.corpus` (runs recorded before read as corpus1); a resume with another corpus or a
  case of the other corpus is refused. v2 runs are checked byte for byte against `eval-freeze-v2.1`.
- **Spans:** `expected-spans-v2.json` (78 cases); every corpus-2 quote lies in its section's span in NFC.
- **Note:** the corpus-1 FTS5 files were missing from the main checkout's `data/keyword` (built in the
  reindex-local worktree); they were copied from there, and their chunk ids match the tracked chunk files 733/733,
  859/859.

## v1 eval (corpus 1; 32 answerable): evidence_hit@5

| mode | Gemini A | Gemini B | Local A | Local B |
|---|---:|---:|---:|---:|
| dense | **30/32 (0.938)** | 27/32 (0.844) | 23/32 (0.719) | 23/32 (0.719) |
| sparse | 26/32 (0.812) | 24/32 (0.750) | 26/32 (0.812) | 24/32 (0.750) |
| hybrid | 28/32 (0.875) | 25/32 (0.781) | 26/32 (0.812) | 26/32 (0.812) |

Paired (exact McNemar): Gemini dense A vs local dense A 30 vs 23, b=7 c=0, **p=0.016** (the only p < 0.05 on v1).
Hybrid vs dense: Gemini A p=0.625, local A p=0.375. Arm A vs B: no test below p=0.25.

## v2 eval, local EmbeddingGemma (Gemini: TBD)

| mode / arm | corpus 2 (A-D, n=52) | E identifier, corpus 1 (n=10) |
|---|---:|---:|
| dense A | 44/52 (0.846) | 10/10 |
| dense B | 46/52 (0.885) | 10/10 |
| sparse A | 39/52 (0.750) | 10/10 |
| sparse B | 38/52 (0.731) | 8/10 |
| hybrid A | **48/52 (0.923)** | 10/10 |
| hybrid B | 45/52 (0.865) | 10/10 |

Per category, evidence_hit@5 (F = unanswerable refused by the current default gate):

| mode / arm | A vi-on-vi (20) | B en-on-en (14) | C vi-on-en (8) | D vi-on-mixed (10) | E identifier (10) | F (10) |
|---|---:|---:|---:|---:|---:|---:|
| dense A | 16/20 | 12/14 | 7/8 | 9/10 | 10/10 | 9/10 |
| dense B | 16/20 | 13/14 | 7/8 | 10/10 | 10/10 | 9/10 |
| sparse A | 15/20 | 13/14 | **1/8** | 10/10 | 10/10 | 9/10 |
| sparse B | 15/20 | 12/14 | **1/8** | 10/10 | 8/10 | 9/10 |
| hybrid A | 17/20 | 13/14 | 8/8 | 10/10 | 10/10 | 9/10 |
| hybrid B | 16/20 | 13/14 | 6/8 | 10/10 | 10/10 | 9/10 |

Per language / typing (answerable v2, both corpora):

| mode / arm | vi (42) | en (20) | diacritics (33) | no_diacritics (9) |
|---|---:|---:|---:|---:|
| dense A | 36/42 | 18/20 | 32/33 | **4/9** |
| dense B | 37/42 | 19/20 | 31/33 | 6/9 |
| sparse A | 30/42 | 19/20 | 25/33 | 5/9 |
| hybrid A | 39/42 | 19/20 | 33/33 | 6/9 |
| hybrid B | 36/42 | 19/20 | 30/33 | 6/9 |

Paired tests, corpus 2 (n=52): hybrid vs dense A 48 vs 44, b=0 c=4, p=0.125; B p=1.000. Sparse vs dense B
38 vs 46, p=0.021 (sparse worse). Arm A vs B: dense p=0.688, hybrid p=0.250. Per category no test reaches
p < 0.5 (n 10-20). C (n=8) and no_diacritics (n=9) are **not tested: n too small**.

## Gate re-check (dev v1 + v2, Arm A, dense top-1; rule: lowest answerable − 0.05). Defaults unchanged.

| embedder | pool | answerable n | lowest answerable | highest unanswerable | rule value | overlap |
|---|---|---:|---:|---:|---:|---|
| Gemini | corpus 1 (v1 dev) | 4 | 0.7360 | 0.6741 | 0.6860 (= default) | no |
| Gemini | corpus 2 (v2 dev) | TBD | | | | |
| Local | corpus 1 | 4 | 0.5917 | 0.5869 | 0.5417 (= default) | no |
| Local | corpus 2 | 5 | 0.3923 | 0.3041 | 0.3423 | no |
| Local | pooled | 9 | 0.3923 | 0.5869 | 0.3423 | **yes** |

**Owner decision 2026-11-25 (local gate):** corpus-2 scores are lower overall, and pooling corpora makes answerable
and unanswerable overlap (0.3923 < 0.5869), so the dense-cosine gate does not separate them across domains for
embeddinggemma. No per-corpus thresholds (the app cannot know a user's corpus), no pooled 0.3423 (it would pass both
unanswerable corpus-1 dev cases, Q-DEV-005 0.5869 and Q-DEV-006 0.5378). Refusal moves to the reranker's absolute
score (next step) with the LLM refusal second; recorded in ADR-0007 (amendment) and retrieval-spec.md.
**Known limitation until then:** the default 0.5417 stays and over-refuses on corpus 2: it refuses 3 of 5 answerable
v2 dev questions (Q2-DEV-002 0.3923 no_diacritics, -003 0.4702, -005 0.5061) and 16/52 (arm A) / 21/52 (arm B)
answerable corpus-2 eval questions. Dev n is 9-11: small. Gemini gate: re-checked the same way once Gemini v2 runs
exist (**TBD**).

## Recommendation (provisional until Gemini v2)
- **Best so far:** on corpus 1, Gemini dense arm A (0.938). On corpus 2 the local embedder's best is hybrid arm A
  (0.923). Hybrid A ≥ dense A in every category; its gain on corpus 2 (48 vs 44) is not significant (p=0.125). On
  arm B hybrid is one case below dense on corpus 2 (45 vs 46, p=1.000) and on C (6/8 vs 7/8). Which embedder ×
  mode is best on corpus 2: **TBD (Gemini v2)**.
- **Where local lags:** v1 dense (23 vs 30, p=0.016); no-diacritics questions (dense A 4/9); gate calibration on
  corpus 2 (above). Sparse alone fails cross-language C (1/8), as expected without translation.
- **Next step (owner, 2026-11-25):** reranker benchmark (plan §7.1), not fine-tuning. Section hits exceed evidence hits (v1 local dense A: section
  29/32, evidence 23/32). Checked offline against the arm's whole chunk file (same NFC + whitespace rule): in every
  section-hit / evidence-miss case the required quotes are contained whole in some chunk of the arm, i.e. the misses
  are ranking, not chunking: v1 local dense A 6/6, v1 local dense B 5/5, corpus-2 local dense A 4/4, hybrid A 3/3,
  dense B 3/3 (Gemini dense A v1: no such case). A reranker over a deeper candidate list targets exactly these and
  could also give the absolute score the hybrid gate lacks. A fine-tune is not justified on 62 answerable questions.
  Reranker gain itself is untested: **TBD**.

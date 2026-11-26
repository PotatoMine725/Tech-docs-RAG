# Reranker benchmark, retrieval only (plan §7.1 step 4b, ADR-0009)

Date: 2026-11-25 (runs 2026-11-26). Status: **run once, as pre-registered**; owner decisions of 2026-11-26 (ADR-0009
D7): merged as infrastructure, default off, opt-in mode **EXPERIMENTAL / PROVISIONAL** (chosen on eval results, not by
the pre-registered rule), gate PROVISIONAL, no dev questions added now. §1 was committed in 6ad584d before any speed or
quality number of its configuration existed and is unchanged since (its gate bullet's "15-20 new dev questions" is
superseded by decision 4, see Recommendation); results are in §2. §4 (2026-11-26) is a tokenization-only check, not a
rerun.

## 1. Pre-registered procedure (owner decisions 2026-11-25)

- **Models:** `Alibaba-NLP/gte-multilingual-reranker-base` (onnx-community export @ee64367) and
  `BAAI/bge-reranker-v2-m3` (onnx-community export @6f5ff65): multilingual cross-encoders that read long input.
  mMiniLM (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) is **dropped**: in the exploratory run (§3) it was worse than
  no reranker on corpus 1, where the passage cut was not the cause, so it is a limit of the model itself.
- **Variant: int8 only.** fp32 is excluded before measuring: its file alone (gte 1,200 MiB, bge 2,166 MiB + graph) is
  over the ~0.5 GB reranker budget of the brief.
- **Passage handling: sliding windows + MaxP, no head cut.** Question cut to 128 tokens; each (question, window) pair is
  at most 512 tokens, so a window is 512 − question − 4 special tokens long; consecutive windows overlap by 128; the
  passage score is its best window's sigmoid(logit). Text: heading path + blank line + link-stripped passage body.
  Nothing about window length is chosen on the test set.
- **Candidates:** the retriever's best K unique passages, embedder's best current mode, Arm A (local: hybrid; Gemini:
  dense). The reranker's top 5 replace the retriever's top 5.
- **K is chosen on speed only**, before any accuracy is computed: per model, the largest K in {20, 15, 10} whose
  median latency per question is <= **2 s** on the low-end profile (4 efficiency cores of the i7-12700H pinned, 4
  intra-op threads, a stand-in for a 4-core Intel gen-10 laptop), measured on the dev questions (v1 + v2, local
  hybrid candidates). Batch size 8. Nothing else runs on the machine during the low-end pass.
- **Eval: exactly one run per model** at its K (full profile, every case of v1 eval, v2 eval corpus 1 + 2, and dev).
  Any other configuration reported is labelled "exploratory, chosen on test".
- **If K = 10 is still over 2 s for a model:** its eval still runs (to know the quality), the default ships **off**
  (`RERANK_PROVIDER=none`), the reranker becomes an opt-in "high quality" mode, and the report states the real latency.
- **Metrics:** evidence_hit@1 and @5 (headline @5), section MRR@5, per pool (v1 eval; v2 corpus 2 A-D; v2 corpus 1 E),
  per category / language / typing; paired exact McNemar against `none` (the production retriever, TOP_K=5), raw p.
  Peak working set and added RAM per model on the low-end profile.
- **Gate:** absolute reranker top-1 (sigmoid), set on **dev only** (dev v1 + v2), rule of retrieval-spec.md (lowest
  answerable − 0.05). Dev has 9 answerable cases (local), so the value stays **PROVISIONAL**. A reliable value needs
  15–20 new dev questions approved by the owner; the frozen eval sets are not touched.
- **Gemini:** v1 only. Gemini v2 has no corpus-2 index and uncached queries (quota): **TBD**.

## 2. Results

Every number comes from `scripts/benchmark/reranker_bench.py` (run folder `data/experiments/rerank-bench/20261125-run3`,
git-ignored; candidates at commit 6ad584d, `git_dirty` false; `report` regenerates every table). No LLM call.
Machine: i7-12700H; low-end profile = logical CPUs 12-15 (E-cores), 4 threads.

**Step 1, K on speed (dev questions, local hybrid candidates, n = 12, before any accuracy was computed):**

| model (int8) | K | median ms / question | p95 ms | median windows | peak RAM MB | <= 2 s |
|---|---:|---:|---:|---:|---:|---|
| gte | 20 | 12,752 | 18,032 | 21 | 2,310 | no |
| gte | 15 | 9,782 | 13,464 | 16 | 2,147 | no |
| gte | 10 | 5,590 | 8,788 | 10 | 2,136 | no |
| bge-m3 | 20 | 29,801 | 41,806 | 21 | 1,675 | no |
| bge-m3 | 15 | 22,989 | 30,835 | 16 | 1,673 | no |
| bge-m3 | 10 | 13,781 | 19,911 | 10 | 1,673 | no |

Both models are over 2 s even at K = 10, so by §1 each ran its one eval at **K = 10** and the default ships **off**.
Windows: about one per candidate (median 21 for 20 candidates), as expected with 512-token pairs. Added RAM (peak
working set − before load, 44 MB) is 2,092 MB for gte and 1,629 MB for bge-m3: both over the ~0.5 GB budget. gte's
peak is above its 325 MB file and above bge-m3's; why (e.g. ONNX Runtime's arena for the gte graph) is not
investigated: **TBD**. On all cores the same K = 10 eval took a median 1,945 ms (gte) and 4,178 ms (bge-m3).

**Step 2, one eval per model at K = 10.** evidence_hit@5 (@1), answerable eval, Arm A. Paired exact McNemar vs `none`
(b = only `none` hits, c = only the reranker hits), raw p.

| embedder (mode) | pool | n | none | gte | p @5 / @1 | bge-m3 | p @5 / @1 |
|---|---|---:|---|---|---|---|---|
| local (hybrid) | v1 eval, corpus 1 | 32 | 26 (15) | 26 (12) | 1.000 / 0.250 | 27 (14) | 1.000 / 1.000 |
| local (hybrid) | v2 eval, corpus 2 A-D | 52 | 48 (31) | 47 (38) | 1.000 / 0.065 | 48 (41) | 1.000 / **0.006** |
| local (hybrid) | v2 eval, corpus 1 E | 10 | 10 (9) | 9 (7) | 1.000 / 0.500 | 10 (7) | 1.000 / 0.500 |
| Gemini (dense) | v1 eval, corpus 1 | 32 | 30 (19) | 26 (13) | 0.219 / **0.031** | 27 (15) | 0.250 / 0.219 |

- **@5: no reranker beats `none`** (no p < 0.2); `none` is already near the candidate ceiling (§3: corpus 2 48 of
  at most 49). **@1 on corpus 2 improves** (bge-m3 31 → 41, b = 1, c = 11, p = 0.006; gte 31 → 38, p = 0.065), so
  the right chunk comes first more often. On corpus 1 @1 drops: local v1 15 → 12 (gte), 15 → 14 (bge-m3); E 9 → 7
  for both (b = 2, c = 0); Gemini dense v1 19 → 13 (gte, p = 0.031), 19 → 15 (bge-m3).
- **gte's published numbers predate the pair guard (§4):** 14 of its 1,766 K = 10 pairs (all in the local corpus-2
  eval) were 1 token over the 512 limit when scored, and the effect of cutting them back was not measured; gte is not
  the opt-in model, and bge-m3 had no such pair.
- Section MRR@5 (local): corpus 2 0.885 → 0.968 (gte), 0.952 (bge-m3); v1 0.919 → 0.911, 0.914.
- Per category / language / typing (local, v2, @5): bge-m3 equals `none` in every cell (A 17/20, B 13/14, C 8/8,
  D 10/10, E 10/10; vi 39/42, en 19/20; diacritics 33/33, no_diacritics 6/9). gte is one case lower in A, E, vi, en
  and diacritics. Subgroups (n 8-20) are not tested.
- Gemini v2: **TBD** (no corpus-2 Gemini index; v2 queries not cached).
- Note: the hybrid retriever is not fully deterministic between runs (near-tie RRF order; dense top-1 identical): two
  candidate builds of the same commit differed in 3 of 120 20-lists and 1 of 120 top-5 lists. Every comparison here
  uses one candidate file, so `none` and the rerankers see the same lists.

**Step 3, gate (PROVISIONAL, dev v1 + v2 only; reranker top-1 sigmoid; rule lowest answerable − 0.05):**

| embedder | model | pool | answerable / unanswerable n | lowest answerable | highest unanswerable | rule value | overlap |
|---|---|---|---|---:|---:|---:|---|
| local | gte | corpus 1 / corpus 2 | 4/2, 5/1 | 0.5362, 0.4783 | 0.5163, 0.4235 | 0.4862, 0.4283 | no, no |
| local | gte | pooled | 9/3 | 0.4783 | 0.5163 | 0.4283 | **yes: DECISION REQUIRED** |
| local | bge-m3 | corpus 1 / corpus 2 | 4/2, 5/1 | 0.1080, 0.0861 | 0.4042, 0.0003 | 0.0580, 0.0361 | **yes**, no |
| local | bge-m3 | pooled | 9/3 | 0.0861 | 0.4042 | 0.0361 | **yes: DECISION REQUIRED** |
| Gemini | gte / bge-m3 | corpus 1 | 4/2 | 0.5394 / 0.1354 | 0.5019 / 0.4477 | 0.4894 / 0.0854 | no / **yes** |

- Pooled across corpora, answerable and unanswerable reranker scores **overlap for both models**, like the dense
  cosine did (ADR-0007 amendment). The overlap comes from one unanswerable corpus-1 near miss, Q-DEV-005 (gte 0.5163,
  bge-m3 0.4042), against answerable cases the reranker scores low: gte Q2-DEV-002 0.4783; bge-m3 Q2-DEV-002 0.0861
  and Q-DEV-004 0.1080.
- With 9 answerable and 3 unanswerable dev cases no value is reliable: **PROVISIONAL**, no default changed. Owner
  decision 2026-11-26: no dev questions are added now (frozen eval sets untouched); the gate stays on the dense score
  and its re-calibration moves to the local LLM step.
- Information only, never used to set a value: at the pooled rule value the eval split would be refused, gte 2/14
  unanswerable and 2/94 answerable; bge-m3 7/14 and 3/94.

## Recommendation

**Owner decisions, 2026-11-26** (ADR-0009 D7): (1) merge the reranker as infrastructure, default stays
`RERANK_PROVIDER=none`; (2) opt-in mode = bge-reranker-v2-m3 int8, K = 10, local embedder only, **EXPERIMENTAL /
PROVISIONAL** because it was chosen on eval results, not by the pre-registered rule; the owner's reasons: latency on a
weak machine (bge-m3 13.8 s per question, gte 5.6 s at K = 10) and +1.6-2.1 GB RAM (bge-m3 1.6 GB, gte 2.1 GB; both in
§2 Step 1) exceed the budget, there is no @5 gain, and only an @1 gain on corpus 2; (3) `RERANK_CANDIDATES` = 10
(chosen by the speed rule) and `RERANK_BATCH_SIZE` = 8 stay; (4) the gate stays PROVISIONAL on the dense score, no dev
questions are added now, and gate re-calibration moves to the local LLM step (LLM refusal = second gate layer).

- **Default: off** (`RERANK_PROVIDER=none`), by the pre-registered rule: both models are over 2 s at K = 10 on the
  low-end profile (gte 5.6 s, bge-m3 13.8 s median) and over the ~0.5 GB RAM budget.
- **Opt-in "high quality" mode (EXPERIMENTAL / PROVISIONAL): bge-m3 int8, K = 10, local embedder.** Its @5 total is never below `none` on local
  hybrid (v1 27 vs 26: 1 case lost, 2 gained; corpus 2 48 vs 48 and E 10 vs 10, identical cases) and it puts the
  evidence first more often on corpus 2 (@1 41 vs 31, p = 0.006), at the cost of @1 on corpus 1 (v1 14 vs 15, E 7 vs
  9). **How this was chosen:** §1 fixed K and the default-off rule, not the choice between gte and bge-m3 nor
  "local embedder only"; both were made on these eval results, and no @5 comparison between the models or against
  `none` is significant, so treat the choice as provisional. Real cost: median 4.2 s per question on the i7-12700H with ONNX Runtime's default threads (full profile), 13.8 s on the low-end
  profile, about 1.6 GB more RAM. With the Gemini embedder (dense) it lowers @1 and @5 on v1: not recommended there.
- **Gate:** no reranker gate value is adopted; the dense gate stays (0.686 / 0.5417, known limitation on corpus 2).
  Reranker values above are PROVISIONAL; per the owner (2026-11-26) no dev questions are added now and the
  re-calibration moves to the local LLM step (LLM refusal = second gate layer).
- Open: Gemini v2 (TBD, quota); gte's RAM (TBD); a smaller/faster multilingual long-input cross-encoder that fits
  2 s would need a new candidate list from the owner.

## 3. Exploratory run before the procedure (head cut, chosen before the owner decisions)

mMiniLM int8, each passage cut to its first 256 tokens, 20 candidates: worse than no reranker. Local hybrid A,
evidence_hit@5: v1 26/32 → 21/32 (p=0.062), v2 corpus 2 48/52 → 39/52 (b=9, c=0, p=0.004), E 10/10 → 9/10; Gemini dense
v1 30/32 → 21/32 (p=0.012). Cause on corpus 2: chunks are longer than 256 tokens (median 394; 83% exceed 256) and in
8 of the 9 lost cases at least one required quote starts after token 256 in its chunk (in 7, every quote does). On
corpus 1, 3 of the 16 lost cases (local v1 5, local v2-E 1, Gemini 10) have one quote past token 256; in the other 13
every quote lies within the first 256 tokens and the model still ranks a required chunk below 5th.
Ceiling of the candidate list (evidence_hit@5 if the best 5 of 20 were chosen; local v1 / v2 corpus 2 / E, Gemini v1):
31/32, 49/52, 10/10, 32/32, against `none` 26, 48, 10, 30. Run folder `data/experiments/rerank-bench/20261125-run1`
(git-ignored), candidates at commit c9dba7b with uncommitted reranker code; these numbers are exploratory only.

## 4. Pair-length check (2026-11-26; tokenization only, not a rerun)

**What and why.** A window is cut on the tokens of the passage alone, but the pair tokenizes it afresh, so its boundary
tokens can come out a token or two longer than counted and a pair can pass the 512 limit. This PR cuts such a pair back
at its window's end (ADR-0009 D2); a pair that fits is never touched. The checks below only tokenize (the `tokenizers`
library, no ONNX session, no scoring, no benchmark or eval run); the §2 numbers are the numbers of the pre-registered
run. The scripts were throw-away replays of `reranker_bench.py`'s worker (same candidate file, `rerank_passage` text,
windows) and are not committed. Check of the replay: for both models its window count per case equals the `windows` the
run recorded in `rerank-{bge,gte}-int8-t512o128-c10-b8-full.json` (162 cases, 1,766 windows, 0 cases differ), so it saw
the same chunk text as the run.

**Method (to repeat it; tokenizer only).** Per model: load its `tokenizer.json`, build
`OnnxCrossEncoderReranker(settings, session=<stub with get_inputs()>, tokenizer=tok)`, cut the question and the windows of
`rerank_passage(chunk)` as `score` does, count the `tok.encode_batch` pairs longer than `pair_limit`. Inputs: benchmark
table = each row's K chunk ids (`c10_chunk_ids`, `c15_chunk_ids`, `chunk_ids` in `candidates-*.jsonl`) with its question;
all-chunks table = every chunk × the 120 questions; cut-back row = every chunk × one question per distinct question
length, through `_encode_pairs`.

**Pairs the benchmark scored** (`20261125-run3` candidate lists, 162 rows = 120 local + 42 Gemini; both models'
own `tokenizer.json`; limit 512; all candidate chunk ids resolved):

| model tokenizer | K | pairs | over the limit |
|---|---:|---:|---|
| bge-m3 | 10 / 15 / 20 | 1,766 / 2,652 / 3,535 | **0 / 0 / 0** |
| gte | 10 | 1,766 | 14 (each by 1 token; all local, v2 corpus-2 eval) |
| gte | 15 / 20 | 2,652 / 3,535 | 19 / 27 (each by 1 token) |

- **bge-m3, the opt-in model: no benchmark pair exceeded the limit, so the cut-back changes none of them and the §2
  bge-m3 numbers stand exactly.**
- **gte: 14 of its 1,766 K = 10 pairs were 1 token over and were scored as such** (its model accepts 8,192 positions,
  so 513 tokens is no error; 512 is the configured limit). With the cut-back each would lose its last window token. The
  gte numbers in §2 come from the code before the cut-back and were not re-run; whether those 14 scores or any rank
  would move is **not measured**. gte is not the opt-in model.

**All chunks, bge tokenizer** (every chunk of arm A / arm B, all 120 dev and eval questions of v1 and v2 as question
lengths; this counts every possible (chunk, question) pair, not only retrieved ones):

| corpus / arm | pairs | over the limit |
|---|---:|---|
| corpus 1 / A | 90,805 | 0 |
| corpus 1 / B | 116,687 | 0 |
| corpus 2 / A | 158,694 | 4 (each by 1 token) |
| corpus 2 / B | 153,701 | 10 (6 by 1 token, 4 by 2) |

**The cut-back on real data** (bge tokenizer, same chunks, one question per distinct question length, 45 lengths, 197,055
pairs; a pair depends only on the question's length, so this counts each over-limit pair once instead of once per
question, hence 7 and not the 14 above): 7 pairs were over the limit, **exactly those 7 were changed, none is over the
limit afterwards, every other pair is identical**.

Not checked: the dropped mMiniLM model, and the Gemini v2 candidates (TBD, quota).

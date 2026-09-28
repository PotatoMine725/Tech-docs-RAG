# EPIC-06 Experiment report: header-aware (Arm A) vs fixed-size (Arm B) chunking

Task EXP-001 (`agents/prompts/12-EXP-001-experiment-and-failure-analysis.md` with the owner's addendum of 2026-09-28,
[prompt log](../../prompt-log/claude-code/EXP-001.md)). Date: 2026-09-28. No Gemini request was made and no parameter,
config, prompt or threshold was changed: this report reads the committed EVAL-004a runs.

Every number below comes from a file:
- tables marked AUTO are written by `scripts/experiments/compare_arms.py` into this file and into
  `data/experiments/exp-001/tables.md`;
- the full comparison with per-row case lists is `data/experiments/exp-001/comparison.json`;
- chunk-level facts per discordant case are in `discordant-chunks.json` / `.md`;
- failures are in `failures.csv`, per-case hits in `per_case_diff.csv`, and chunk statistics in `chunk-stats.json`.

Re-run: `python scripts/experiments/compare_arms.py --run-a 20260928-eval-A-full-491f137 --run-b
20260928-eval-B-full-491f137 --data-root <checkout holding data/processed> --report docs/reports/epics/EPIC-06-experiment.md`.

**One-line answer.** On 36 questions, answer quality shows no statistically reliable difference between the arms.
The measurable differences are in the chunks themselves:
- Arm B sends about 494 more prompt tokens per answer (reliable, p < 0.001).
- 45 % of Arm B's chunks cut a code block, against 3 % for Arm A.
- The two arms fail on different questions for different, traceable reasons.

## 1. What changed

Only the chunker (ADR-0003 D7):

| | Arm A | Arm B |
|---|---|---|
| Chunker | header-aware (`header-1600`): split on H2/H3, max 1,600 chars, min 400 (small sections merge with the next), code fences and tables atomic, 200-char overlap only inside a split oversized section, heading-only chunks dropped (D3a) | fixed-size (`fixed-1600`): 1,600-char windows, 200-char overlap, no regard for headings or code fences |
| Exact-duplicate chunks | dropped at chunking (D1): 447 dropped, all in the version-repeating docs #11/#13/#17/#23 | 0 (windows never repeat exactly) |
| Collection | `arm-a.jsonl`, 733 chunks, SHA-256 `9c3bcc6c…` | `arm-b.jsonl`, 859 chunks, SHA-256 `2bde1a0e…` |

Held constant (from both `run.json` files; `compare_arms.py` refuses to run if any of these differ between the runs):

| Setting | Value |
|---|---|
| Normalization (D1) and contextual heading header in the embedded text (D5) | same code for both arms |
| Embedding model / dimension | `gemini-embedding-001` / 768 |
| Distance | cosine (`chroma_store.py` `DISTANCE`, ADR-0005 D17) |
| top-k / overfetch | 5 / 10 (then `passage_hash` dedup) |
| Gate threshold (top-1 score) | 0.686 (OD-9) |
| Answer prompt | `answer_v2`, SHA-256 `dfe37f53…` |
| Answer model | `gemini-3.5-flash-lite`, fallback off |
| Judge model / prompt | `gemini-3.5-flash-lite` / `judge_v1` |
| Question set | `eval-v1.jsonl` SHA-256 `3436870e…` (tag `eval-freeze-v1`), split `eval`, 36 cases |
| Code | commit `491f137`, `git_dirty: false` in both runs |

## 2. How each arm was evaluated

- **Same frozen questions, same runner, same metrics.** Both arms answered the 36 eval cases:
  - 32 answerable, 16 EN and 16 VI;
  - 7 EN/VI parallel pairs;
  - 4 corpus-insufficient cases.

  Runs: `20260928-eval-A-full-491f137` and `20260928-eval-B-full-491f137` (EVAL-004a). Scoring is `scoring.py`'s
  per-record rows in each `summary.json`, and nothing is re-scored here. Ground truth (expected `source_id` + heading
  path, evidence quotes) was frozen before any index existed.
- **Paired design.** The same question goes to both arms, so each case is compared with itself. Question difficulty
  cancels out, and only the chunker differs. The tests are therefore paired:
  - binary metrics use the exact McNemar test on the discordant pairs; the tables show `b` = cases only A got right and
    `c` = cases only B got right, not only p;
  - continuous metrics (MRR, latency, tokens, citation rates) use the exact Wilcoxon signed-rank test;
  - the 95 % CI of Δ = B − A is a paired bootstrap (10,000 resamples, seed 42).

  All three tests come from the existing, unit-tested `application/evaluation/stats.py`; nothing is re-implemented.
- **Paired n per row.** A metric is compared only over the cases where both arms have a value, so every row carries
  its own n:
  - **Retrieval rows** use all 32 answerable cases.
  - **Answer-level rows** use the cases labelled in both arms. `Q-EVAL-002:B` is unlabelled: the judge returned a
    format error twice, so that case is out of every answer-level pair. That leaves 35 labelled cases: 31 answerable
    for accuracy, lenient accuracy and false refusal, and 4 corpus-insufficient for correct refusal and hallucination.
    Groundedness (27) and citation rows (27/28) need an answer check in both arms.
  - **Generate latency and tokens** use the 30 cases where the LLM was called in both arms.
  - Because of this pairing, Arm A's accuracy in the table is 22/31 = 0.710, while `summary.json`'s unpaired figure
    is 23/32 = 0.719: `Q-EVAL-002:A` is correct but has no B partner.
- **Wording rule.** p ≥ 0.05 is reported as "no statistically reliable difference at n = X", never as one arm being
  better.

### Threats to validity

**The gate threshold was tuned on Arm A.** The threshold 0.686 was chosen on Arm A's dev-set scores (OD-9) and then
applied unchanged to both arms. The arms produce different score distributions: a 1,600-char window and an 848-char
section embed differently even when they hold the same sentence. A gate decision near the threshold is therefore partly
a measure of how well 0.686 fits each arm, not of chunk quality. `Q-EVAL-001` is exactly this case (§4). The
false-refusal row should be read with this in mind.

**Dedup acts only on Arm A.** The retriever's `passage_hash` dedup drops same-passage copies. Only Arm A has any, from
the version-repeating docs; Arm B has no duplicate groups. Arm A dropped copies on 4 cases (`Q-EVAL-003` 1, `004` 1,
`024` 3, `027` 1), but every dropped copy ranked 6–15, outside the top 5. The duplicate rule therefore changed 0 metric
values on either arm (`duplicate_rule_changed` = 0 in both summaries; confirmed by the EVAL-004a verify).

**The judge is the answer model.** Both arms' answers were judged by `gemini-3.5-flash-lite`, the model that wrote
them (self-preference risk; ADR-0004 D12). The owner's blind spot-check of 10 verdicts gave:
- 8 of 10 label agreement when the owner's per-point grades are run through the same `map_result` rule (κ 0.69);
- 9 of 10 by the owner's holistic "agree with the judge?".

n = 10 is small. Judge format errors: 2 of 61 calls, both on `Q-EVAL-002:B`. The judge copied the source id `22` into
the citation-marker field; the EVAL-004a verifier confirmed this by rebuilding the prompt offline. §4 lists further
judge-side effects that touch this comparison.

**n = 36 is small.** With 31 labelled answerable pairs, only large effects can reach p < 0.05. McNemar looks only at
discordant pairs, and accuracy has 5 of them (`020`, `027` A-only; `001`, `012`, `022` B-only). Even a 5–0 split would
give p = 2 × (1/2)^5 = 0.0625. So "no statistically reliable difference at n = 31" here means "too few disagreements
to tell", not "the arms are equal". The bootstrap CIs show the plausible range. For accuracy, Δ = +0.032 with CI
[−0.097, +0.161].

**Latency is confounded by run order and the cache.** Arm A ran first and computed all 36 query embeddings live. Arm
B's were all cache hits (EVAL-004a: B made 0 embedding requests), so B's `embed_query` p50 is 0.1 ms against A's
352 ms. `embed_query` and `total` are therefore shown per arm but not tested. `retrieve` is tested, but its gap is
milliseconds and reflects run order: A's mean of 15.7 ms is dominated by its first query, a 414.6 ms cold start
(`Q-EVAL-001`, the first record of the first run), with p50 3.9 vs 2.4 ms. Neither latency number is a chunker effect worth acting on. `generate` depends on the API. Both arms have p50
≈ 1.5 s and a p95 of about 37–39 s from a few very slow calls.

**One run per arm.** Each arm was run once, and the tags on some questions (e.g. `fixed_size_code_split`) were chosen
beforehand to probe known weaknesses. A single-case label change can include run-to-run generation variance, which
this design cannot separate from the chunker.

## 3. Results

Overall. Retrieval rows: n = 32 answerable. Answer rows: paired n as stated. Latency rows show the mean with p50/p95.

<!-- AUTO:results-overall -->
| Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test | p | n |
|---|---|---|---|---|---|---|---|
| source_hit@1 | 0.875 | 0.875 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 32 |
| source_hit@1:strict | 0.875 | 0.844 | -0.031 | [-0.094, 0.000] | McNemar b=1 c=0 | 1.000 | 32 |
| source_hit@3 | 0.938 | 0.906 | -0.031 | [-0.094, 0.000] | McNemar b=1 c=0 | 1.000 | 32 |
| source_hit@3:strict | 0.938 | 0.906 | -0.031 | [-0.094, 0.000] | McNemar b=1 c=0 | 1.000 | 32 |
| source_hit@5 | 0.969 | 0.938 | -0.031 | [-0.094, 0.000] | McNemar b=1 c=0 | 1.000 | 32 |
| source_hit@5:strict | 0.969 | 0.938 | -0.031 | [-0.094, 0.000] | McNemar b=1 c=0 | 1.000 | 32 |
| section_hit@1 | 0.812 | 0.844 | 0.031 | [-0.062, 0.156] | McNemar b=1 c=2 | 1.000 | 32 |
| section_hit@1:strict | 0.781 | 0.719 | -0.062 | [-0.188, 0.062] | McNemar b=3 c=1 | 0.625 | 32 |
| section_hit@3 | 0.906 | 0.906 | 0.000 | [-0.094, 0.094] | McNemar b=1 c=1 | 1.000 | 32 |
| section_hit@3:strict | 0.906 | 0.844 | -0.062 | [-0.188, 0.062] | McNemar b=3 c=1 | 0.625 | 32 |
| section_hit@5 | 0.938 | 0.938 | 0.000 | [-0.094, 0.094] | McNemar b=1 c=1 | 1.000 | 32 |
| section_hit@5:strict | 0.938 | 0.938 | 0.000 | [-0.094, 0.094] | McNemar b=1 c=1 | 1.000 | 32 |
| evidence_hit@1 | 0.594 | 0.406 | -0.188 | [-0.406, 0.062] | McNemar b=11 c=5 | 0.210 | 32 |
| evidence_hit@3 | 0.875 | 0.781 | -0.094 | [-0.250, 0.062] | McNemar b=5 c=2 | 0.453 | 32 |
| evidence_hit@5 | 0.938 | 0.844 | -0.094 | [-0.188, 0.000] | McNemar b=3 c=0 | 0.250 | 32 |
| mrr | 1.000 | 0.984 | -0.016 | [-0.047, 0.000] | Wilcoxon (n≠0 = 1) | 1.000 | 32 |
| mrr:strict | 0.964 | 0.928 | -0.035 | [-0.098, 0.027] | Wilcoxon (n≠0 = 5) | 0.375 | 32 |
| accuracy | 0.710 | 0.742 | 0.032 | [-0.097, 0.161] | McNemar b=2 c=3 | 1.000 | 31 |
| lenient_accuracy | 0.871 | 0.935 | 0.065 | [0.000, 0.161] | McNemar b=0 c=2 | 0.500 | 31 |
| false_refusal | 0.129 | 0.065 | -0.065 | [-0.161, 0.000] | McNemar b=2 c=0 | 0.500 | 31 |
| groundedness | 0.926 | 1.000 | 0.074 | [0.000, 0.185] | McNemar b=0 c=2 | 0.500 | 27 |
| correct_refusal | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 4 |
| hallucination | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 4 |
| citation_support_rate | 0.981 | 0.963 | -0.019 | [-0.074, 0.037] | Wilcoxon (n≠0 = 3) | 1.000 | 27 |
| citation_section_precision | 0.964 | 0.988 | 0.024 | [-0.024, 0.089] | Wilcoxon (n≠0 = 3) | 0.500 | 28 |
| latency_retrieve_ms | 15.7 (p50 3.9 / p95 11.2) | 2.6 (p50 2.4 / p95 3.8) | -13.1 | [-36.3, -1.2] | Wilcoxon (n≠0 = 36) | <0.001 | 36 |
| latency_generate_ms | 3945.6 (p50 1502.8 / p95 36583.7) | 4211.2 (p50 1495.0 / p95 39423.2) | 265.6 | [-4643.0, 5344.9] | Wilcoxon (n≠0 = 30) | 0.700 | 30 |
| latency_embed_query_ms (median) | 351.8 | 0.1 | — | — | not tested: not comparable: arm B's query embeddings were cache hits | — | 36 |
| latency_total_ms (median) | 1856.7 | 1484.5 | — | — | not tested: not comparable: includes embed_query | — | 36 |
| tokens_prompt | 1628.6 | 2122.6 | 494.0 | [418.8, 567.2] | Wilcoxon (n≠0 = 30) | <0.001 | 30 |
| tokens_output | 149.8 | 162.7 | 12.9 | [1.6, 28.1] | Wilcoxon (n≠0 = 30) | 0.113 | 30 |
| tokens_total | 1778.3 | 2285.2 | 506.9 | [432.6, 579.1] | Wilcoxon (n≠0 = 30) | <0.001 | 30 |
<!-- /AUTO:results-overall -->

**Strict vs lenient.** Lenient counts an owner-approved alternate section as a hit; strict counts expected sections
only. Only rows where strict and lenient differ are shown. The flip is in **section hit@1**:
- lenient Δ = +0.031 (B ahead: A-only 015; B-only 017, 022);
- strict Δ = −0.062 (A ahead: A-only 005, 013, 015; B-only 022).

B's top-1 hits on 005 and 013 are lenient only: B ranks the expected section's chunk second and an alternate first.
For accuracy the flip runs the other way:
- strict: 020 and 027 are A-only;
- lenient: both become ties (B's answers there are `partially_correct`), leaving only B-only cases (001, 022).

Neither difference is statistically reliable (all p ≥ 0.375).

<!-- AUTO:strict-lenient -->
| Lenient / strict | A (len / str) | B (len / str) | Δ (len / str) | p (len / str) | A-only cases (len / str) | B-only cases (len / str) |
|---|---|---|---|---|---|---|
| source_hit@1 / source_hit@1:strict | 0.875 / 0.875 | 0.875 / 0.844 | 0.000 / -0.031 | 1.000 / 1.000 | none / 013 | none / none |
| section_hit@1 / section_hit@1:strict | 0.812 / 0.781 | 0.844 / 0.719 | 0.031 / -0.062 | 1.000 / 0.625 | 015 / 005, 013, 015 | 017, 022 / 022 |
| section_hit@3 / section_hit@3:strict | 0.906 / 0.906 | 0.906 / 0.844 | 0.000 / -0.062 | 1.000 / 0.625 | 032 / 006, 017, 032 | 022 / 022 |
| mrr / mrr:strict | 1.000 / 0.964 | 0.984 / 0.928 | -0.016 / -0.035 | 1.000 / 0.375 | — | — |
| lenient_accuracy / accuracy | 0.871 / 0.710 | 0.935 / 0.742 | 0.065 / 0.032 | 0.500 / 1.000 | none / 020, 027 | 001, 022 / 001, 012, 022 |
<!-- /AUTO:strict-lenient -->

Per language (ADR-0003 D9: every VI question retrieves English chunks):

<!-- AUTO:results-en -->
| Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test | p | n |
|---|---|---|---|---|---|---|---|
| source_hit@1 | 0.875 | 0.875 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@1:strict | 0.875 | 0.812 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| source_hit@3 | 0.938 | 0.938 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@3:strict | 0.938 | 0.938 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@5 | 1.000 | 0.938 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| source_hit@5:strict | 1.000 | 0.938 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| section_hit@1 | 0.812 | 0.812 | 0.000 | [-0.188, 0.188] | McNemar b=1 c=1 | 1.000 | 16 |
| section_hit@1:strict | 0.812 | 0.625 | -0.188 | [-0.375, 0.000] | McNemar b=3 c=0 | 0.250 | 16 |
| section_hit@3 | 0.938 | 0.938 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| section_hit@3:strict | 0.938 | 0.875 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| section_hit@5 | 1.000 | 0.938 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| section_hit@5:strict | 1.000 | 0.938 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| evidence_hit@1 | 0.625 | 0.312 | -0.312 | [-0.688, 0.062] | McNemar b=8 c=3 | 0.227 | 16 |
| evidence_hit@3 | 0.938 | 0.938 | 0.000 | [-0.188, 0.188] | McNemar b=1 c=1 | 1.000 | 16 |
| evidence_hit@5 | 1.000 | 0.938 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| mrr | 1.000 | 0.969 | -0.031 | [-0.094, 0.000] | Wilcoxon (n≠0 = 1) | 1.000 | 16 |
| mrr:strict | 0.969 | 0.906 | -0.062 | [-0.188, 0.062] | Wilcoxon (n≠0 = 4) | 0.625 | 16 |
| accuracy | 0.812 | 0.812 | 0.000 | [-0.188, 0.188] | McNemar b=1 c=1 | 1.000 | 16 |
| lenient_accuracy | 0.938 | 1.000 | 0.062 | [0.000, 0.188] | McNemar b=0 c=1 | 1.000 | 16 |
| false_refusal | 0.062 | 0.000 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| groundedness | 0.933 | 1.000 | 0.067 | [0.000, 0.200] | McNemar b=0 c=1 | 1.000 | 15 |
| correct_refusal | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 2 |
| hallucination | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 2 |
| citation_support_rate | 0.967 | 0.933 | -0.033 | [-0.133, 0.067] | Wilcoxon (n≠0 = 3) | 1.000 | 15 |
| citation_section_precision | 0.933 | 1.000 | 0.067 | [0.000, 0.167] | Wilcoxon (n≠0 = 2) | 0.500 | 15 |
| latency_retrieve_ms | 27.5 (p50 3.9 / p95 414.6) | 2.5 (p50 2.3 / p95 3.9) | -25.0 | [-71.2, -1.4] | Wilcoxon (n≠0 = 18) | <0.001 | 18 |
| latency_generate_ms | 3617.9 (p50 1396.3 / p95 36583.7) | 3873.8 (p50 1433.2 / p95 39423.2) | 255.9 | [-6465.3, 7198.3] | Wilcoxon (n≠0 = 16) | 0.782 | 16 |
| latency_embed_query_ms (median) | 353.6 | 0.1 | — | — | not tested: not comparable: arm B's query embeddings were cache hits | — | 18 |
| latency_total_ms (median) | 1814.0 | 1451.5 | — | — | not tested: not comparable: includes embed_query | — | 18 |
| tokens_prompt | 1588.7 | 2089.6 | 500.9 | [401.7, 596.9] | Wilcoxon (n≠0 = 16) | <0.001 | 16 |
| tokens_output | 143.4 | 149.4 | 5.9 | [-4.6, 17.8] | Wilcoxon (n≠0 = 16) | 0.641 | 16 |
| tokens_total | 1732.1 | 2239.0 | 506.9 | [406.6, 601.8] | Wilcoxon (n≠0 = 16) | <0.001 | 16 |
<!-- /AUTO:results-en -->

<!-- AUTO:results-vi -->
| Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test | p | n |
|---|---|---|---|---|---|---|---|
| source_hit@1 | 0.875 | 0.875 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@1:strict | 0.875 | 0.875 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@3 | 0.938 | 0.875 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| source_hit@3:strict | 0.938 | 0.875 | -0.062 | [-0.188, 0.000] | McNemar b=1 c=0 | 1.000 | 16 |
| source_hit@5 | 0.938 | 0.938 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| source_hit@5:strict | 0.938 | 0.938 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 16 |
| section_hit@1 | 0.812 | 0.875 | 0.062 | [0.000, 0.188] | McNemar b=0 c=1 | 1.000 | 16 |
| section_hit@1:strict | 0.750 | 0.812 | 0.062 | [0.000, 0.188] | McNemar b=0 c=1 | 1.000 | 16 |
| section_hit@3 | 0.875 | 0.875 | 0.000 | [-0.188, 0.188] | McNemar b=1 c=1 | 1.000 | 16 |
| section_hit@3:strict | 0.875 | 0.812 | -0.062 | [-0.250, 0.125] | McNemar b=2 c=1 | 1.000 | 16 |
| section_hit@5 | 0.875 | 0.938 | 0.062 | [0.000, 0.188] | McNemar b=0 c=1 | 1.000 | 16 |
| section_hit@5:strict | 0.875 | 0.938 | 0.062 | [0.000, 0.188] | McNemar b=0 c=1 | 1.000 | 16 |
| evidence_hit@1 | 0.562 | 0.500 | -0.062 | [-0.312, 0.188] | McNemar b=3 c=2 | 1.000 | 16 |
| evidence_hit@3 | 0.812 | 0.625 | -0.188 | [-0.438, 0.062] | McNemar b=4 c=1 | 0.375 | 16 |
| evidence_hit@5 | 0.875 | 0.750 | -0.125 | [-0.312, 0.000] | McNemar b=2 c=0 | 0.500 | 16 |
| mrr | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | Wilcoxon (n≠0 = 0) | 1.000 | 16 |
| mrr:strict | 0.958 | 0.950 | -0.008 | [-0.025, 0.000] | Wilcoxon (n≠0 = 1) | 1.000 | 16 |
| accuracy | 0.600 | 0.667 | 0.067 | [-0.133, 0.267] | McNemar b=1 c=2 | 1.000 | 15 |
| lenient_accuracy | 0.800 | 0.867 | 0.067 | [0.000, 0.200] | McNemar b=0 c=1 | 1.000 | 15 |
| false_refusal | 0.200 | 0.133 | -0.067 | [-0.200, 0.000] | McNemar b=1 c=0 | 1.000 | 15 |
| groundedness | 0.917 | 1.000 | 0.083 | [0.000, 0.250] | McNemar b=0 c=1 | 1.000 | 12 |
| correct_refusal | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 2 |
| hallucination | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 2 |
| citation_support_rate | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | Wilcoxon (n≠0 = 0) | 1.000 | 12 |
| citation_section_precision | 1.000 | 0.974 | -0.026 | [-0.077, 0.000] | Wilcoxon (n≠0 = 1) | 1.000 | 13 |
| latency_retrieve_ms | 3.8 (p50 3.7 / p95 5.5) | 2.6 (p50 2.4 / p95 3.7) | -1.2 | [-1.7, -0.6] | Wilcoxon (n≠0 = 18) | 0.001 | 18 |
| latency_generate_ms | 4320.1 (p50 1671.4 / p95 37020.2) | 4596.8 (p50 1595.5 / p95 42441.8) | 276.7 | [-7583.3, 8686.6] | Wilcoxon (n≠0 = 14) | 0.502 | 14 |
| latency_embed_query_ms (median) | 345.3 | 0.1 | — | — | not tested: not comparable: arm B's query embeddings were cache hits | — | 18 |
| latency_total_ms (median) | 1923.6 | 1506.0 | — | — | not tested: not comparable: includes embed_query | — | 18 |
| tokens_prompt | 1674.1 | 2160.2 | 486.1 | [371.6, 596.9] | Wilcoxon (n≠0 = 14) | <0.001 | 14 |
| tokens_output | 157.0 | 177.9 | 20.9 | [2.4, 49.6] | Wilcoxon (n≠0 = 14) | 0.070 | 14 |
| tokens_total | 1831.1 | 2338.1 | 506.9 | [389.4, 615.1] | Wilcoxon (n≠0 = 14) | <0.001 | 14 |
<!-- /AUTO:results-vi -->

Parallel subset: the 14 cases in the 7 EN/VI pairs, `Q-EVAL-001`…`014`.

<!-- AUTO:results-parallel -->
| Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test | p | n |
|---|---|---|---|---|---|---|---|
| source_hit@1 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| source_hit@1:strict | 1.000 | 0.929 | -0.071 | [-0.214, 0.000] | McNemar b=1 c=0 | 1.000 | 14 |
| source_hit@3 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| source_hit@3:strict | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| source_hit@5 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| source_hit@5:strict | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| section_hit@1 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| section_hit@1:strict | 0.929 | 0.786 | -0.143 | [-0.357, 0.000] | McNemar b=2 c=0 | 0.500 | 14 |
| section_hit@3 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| section_hit@3:strict | 1.000 | 0.929 | -0.071 | [-0.214, 0.000] | McNemar b=1 c=0 | 1.000 | 14 |
| section_hit@5 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| section_hit@5:strict | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| evidence_hit@1 | 0.643 | 0.643 | 0.000 | [-0.429, 0.429] | McNemar b=4 c=4 | 1.000 | 14 |
| evidence_hit@3 | 0.857 | 0.929 | 0.071 | [-0.143, 0.286] | McNemar b=1 c=2 | 1.000 | 14 |
| evidence_hit@5 | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | McNemar b=0 c=0 | 1.000 | 14 |
| mrr | 1.000 | 1.000 | 0.000 | [0.000, 0.000] | Wilcoxon (n≠0 = 0) | 1.000 | 14 |
| mrr:strict | 0.952 | 0.871 | -0.081 | [-0.188, 0.000] | Wilcoxon (n≠0 = 3) | 0.250 | 14 |
| accuracy | 0.769 | 0.923 | 0.154 | [0.000, 0.385] | McNemar b=0 c=2 | 0.500 | 13 |
| lenient_accuracy | 0.923 | 1.000 | 0.077 | [0.000, 0.231] | McNemar b=0 c=1 | 1.000 | 13 |
| false_refusal | 0.077 | 0.000 | -0.077 | [-0.231, 0.000] | McNemar b=1 c=0 | 1.000 | 13 |
| groundedness | 0.917 | 1.000 | 0.083 | [0.000, 0.250] | McNemar b=0 c=1 | 1.000 | 12 |
| correct_refusal | — | — | — | — | — | — | 0 |
| hallucination | — | — | — | — | — | — | 0 |
| citation_support_rate | 0.958 | 0.958 | 0.000 | [-0.125, 0.125] | Wilcoxon (n≠0 = 2) | 1.000 | 12 |
| citation_section_precision | 0.962 | 0.974 | 0.013 | [-0.077, 0.115] | Wilcoxon (n≠0 = 2) | 1.000 | 13 |
| latency_retrieve_ms | 35.1 (p50 5.2 / p95 414.6) | 2.3 (p50 2.1 / p95 3.8) | -32.8 | [-91.7, -2.7] | Wilcoxon (n≠0 = 14) | <0.001 | 14 |
| latency_generate_ms | 1712.0 (p50 1502.8 / p95 3658.8) | 4633.1 (p50 1464.0 / p95 42441.8) | 2921.1 | [-561.8, 9411.4] | Wilcoxon (n≠0 = 13) | 0.542 | 13 |
| latency_embed_query_ms (median) | 367.0 | 0.1 | — | — | not tested: not comparable: arm B's query embeddings were cache hits | — | 14 |
| latency_total_ms (median) | 1910.5 | 1532.7 | — | — | not tested: not comparable: includes embed_query | — | 14 |
| tokens_prompt | 1594.6 | 2112.8 | 518.2 | [385.5, 648.7] | Wilcoxon (n≠0 = 13) | <0.001 | 13 |
| tokens_output | 157.0 | 162.4 | 5.4 | [-4.2, 16.8] | Wilcoxon (n≠0 = 13) | 0.880 | 13 |
| tokens_total | 1751.6 | 2275.2 | 523.6 | [390.9, 652.3] | Wilcoxon (n≠0 = 13) | <0.001 | 13 |
<!-- /AUTO:results-parallel -->

Chunk statistics (recomputed from the chunk files; equal to `data/processed/chunks/stats-arm-{a,b}.json`). A chunk
"cuts a code fence" when it contains part, but not all, of a fenced block (`cuts_code_fence`, INGEST-002):

<!-- AUTO:chunk-stats -->
| Chunk statistic | Arm A | Arm B |
|---|---|---|
| chunks | 733 | 859 |
| size p50 (chars) | 1178 | 1600 |
| size p90 (chars) | 1527 | 1600 |
| chunks cutting a code fence | 24 | 387 |
| % chunks cutting a code fence | 3.27 | 45.05 |
| chunks of tiny doc #09 | 4 | 1 |
| chunks of tiny doc #22 | 3 | 2 |
| chunks of tiny doc #29 | 3 | 1 |
<!-- /AUTO:chunk-stats -->

## 4. Why they differ

### What the chunk data shows

1. **Arm A keeps a section whole; Arm B keeps neighbours together.**
   - A's p50 chunk is 1,178 chars and follows headings, so a single-section answer usually sits in one chunk.
   - B's chunks are all 1,600 chars (p50 = p90) and start wherever the window lands: mid-sentence, mid-code, or across
     a heading.
   - The effect shows in **evidence hit@1**, "does the top chunk contain every required point's quote?": A 0.594 vs
     B 0.406, Δ −0.188, CI [−0.406, +0.062], McNemar b = 11, c = 5, p = 0.21. There is no statistically reliable
     difference at n = 32, but the 16 discordant cases split along one line:
     - **A wins when the answer is one section.** In 005, 009, 010, 013, 015, 016, 018, 019, 021, 027 and 031 (the 11
       A-only cases), A's rank-1 chunk covers every required point, and B's rank-1 window holds only part of the section or a neighbour. For 009/010, B's
       rank-1 `03:fixed-1600:0012` cuts a fence and the section's points sit in `0011` at rank 3.
     - **B wins when the answer spans two adjacent short sections.** In 003, 004, 011, 012 and 023 (the 5 B-only cases), B's rank-1 window
       covers P1–P3, while A has P1–P2 in one section chunk and P3 in the next. Tiny doc #29 is the clearest case: A
       has 3 chunks ("title table" 201 chars, "Cause" 681, "How to fix" 396), and B has 1 chunk of 1,282 chars that
       holds everything.
2. **At rank 5 the arms retrieve the same sections.** section hit@5 is 0.938 in both arms (b = 1, c = 1: 031 A-only,
   022 B-only), and lenient MRR is 1.000 vs 0.984. The expected section is almost always somewhere in the top 5 for
   both chunkers. This is plausible for two reasons:
   - Many sections are close to 1,600 chars already: A's p90 is 1,527, so a B window often covers about the same text
     as an A chunk.
   - Both arms embed the same heading-path prefix (D5), which carries most of the "which section is this" signal.

   So the chunker changes *where in the top 5* the evidence lands and *how complete* each chunk is, more than whether
   it is retrieved.
3. **Arm B costs more tokens, reliably.** Prompt tokens are +494 per answer (A 1,629 vs B 2,123 mean, CI [+419, +567],
   Wilcoxon p < 0.001, n = 30). Five full 1,600-char windows are longer than five header chunks with a p50 of 1,178. It
   is the only reliable difference in the tables besides the confounded `retrieve` latency.
4. **Code is cut far more often in B.** 387 of 859 B chunks (45.05 %) cut a code fence, against 24 of 733 A chunks
   (3.27 %). This is the mechanism behind 018:B and 027:B below. It did not produce a reliable answer-level difference
   at this n.

### Every discordant case

23 cases differ between the arms on the answer label, groundedness, or any retrieval metric (lenient or strict,
hit@1/3/5, evidence hit, MRR). Chunk-level evidence for each is in `data/experiments/exp-001/discordant-chunks.md`
(top-3 chunks per arm; top 5 in the JSON). Notation: "A r1 = P1,P2" means A's rank-1 chunk contains whole quotes for
required points P1 and P2.

| Case | What differs (A → B) | Chunk-level explanation |
|---|---|---|
| 001 | label `false_refusal` → `correct` | Same section (#22 "Querying Data") at rank 1 in both, with both evidence quotes. A's chunk is the 848-char section: top-1 **0.6779 < 0.686**, gate refused. B's chunk is the first 1,600 chars of the doc (the section plus the start of "Loading all data"): top-1 **0.6908 ≥ 0.686**, answered correctly. The gate, not retrieval, decided this case (threat 1). |
| 003, 004 | evidence hit@1/@3 0 → 1 | All top-5 chunks are #13/#12 "Developer exception page" variants in both arms. A r1 = P1,P2, and P3 is first seen at A r5 (003) / r4 (004). B r1 = P1,P2,P3: its window spans the end of one block and the next. Both answers are correct. |
| 005 | groundedness 0 → 1; section hit@1 strict 1 → 0; evidence hit@1 1 → 0; MRR strict 1 → 0.5 | A r1 = the "Recognize CPU-bound and I/O-bound" chunk with P1,P2. B r1 = `02:fixed-1600:0000` (the doc start, an alternate-section hit), and B's P1,P2 chunk is at rank 3. The groundedness flip is a judge artefact (see "Evaluation-side failures"). |
| 006 | section hit@3 strict 1 → 0; evidence hit@3 1 → 0; MRR strict 0.333 → 0.2 | Same section as 005. A's P1,P2 chunk is at rank 3, B's at rank 5 (B r3–r4 are #01 and a fence-cutting "Review the complete example" window). Both correct. |
| 009, 010 | evidence hit@1 1 → 0 | A r1 = the whole "Avoid multiple acts" section (P1–P3). B r1 `03:fixed-1600:0012` cuts a fence and holds 1 of 4 quotes; the section's quotes are in `0011` at rank 3. Labels are equal in both arms (009 correct, 010 partially_correct). |
| 011 | evidence hit@1 0 → 1 | Tiny doc #29: A splits it in 3 chunks (A r1 = P1,P2; A r2 = P3), B has one chunk (B r1 = P1–P3). Both correct. |
| 012 | label `partially_correct` → `correct`; evidence hit@1 0 → 1 | Same retrieval as 011 (VI twin). A had every quote in its top 2 (r1 = P1,P2; r2 = P3), but its answer omits "the generator silently skips validation" (P2). B's single chunk led to an answer that states it. The evidence was in both contexts, so A's failure is `generation` (§ failure analysis). The owner's spot-check (S03) grades A's P2 as `no`, harsher than the judge's `partial`, so the label is not a judge artefact. |
| 013 | source/section hit@1 strict 1 → 0; evidence hit@1 1 → 0; MRR strict 1 → 0.5 | A r1 = #10 "Service lifetimes" (P1–P3). B r1 = #11 `fixed-1600:0004` (an alternate source), and B's #10 chunk is at rank 2. Both correct. |
| 015 | section hit@1 1 → 0 (lenient and strict); evidence hit@1 1 → 0; MRR 1 → 0.5 | A r1 = the "Async/await vs ContinueWith" chunk (P1,P2,P3). B r1 `01:fixed-1600:0022` cuts a fence and misses the section; B's P1–P3 chunk is at rank 2. Both correct. |
| 016 | evidence hit@1/@3/@5 1 → 0 | Both arms gated (A 0.6269, B 0.6246). A r1 = #26 "Value types and reference types" with P1. B's windows over the same section hold no whole required-point quote. Recorded as a chunking signal on B; the case is a `refusal (gate)` in both arms. |
| 017 | section hit@1 0 → 1; section hit@3 strict 1 → 0; MRR strict 0.5 → 1 | Two-slot case. A r1 hits only S1; S2 first appears at A r3. B r1 `11:fixed-1600:0004` straddles both sections (hits S1 and S2), so section hit@1 = 1. Under strict, B's top 3 satisfies a slot only through an alternate section. Both `partially_correct` (P1 is only at A r3 / B r2). |
| 018 | evidence hit@1/@3/@5 1 → 0 | A r1 = the whole "Precedence and order of checking" section (P1,P2,P3 in one 1,464-char chunk). B r1 `21:fixed-1600:0010` starts mid-sentence ("…he `>= 'a' and <= 'z'` expression: // Correct pattern…"), cuts a fence and holds only P3; the explanation (P1) is in the previous window, not retrieved. Both gated (A 0.6753, B 0.6483). Worked example 3. |
| 019 | evidence hit@1 1 → 0 | A r1 = P1–P3. B's P1–P3 window is at rank 2, behind a fence-cutting window with P3 only. Both correct. |
| 020 | label `correct` → `partially_correct` | Retrieval is equivalent: both rank 1 = #16 "Integer literals" with P1–P3 (B's cuts a fence). The label difference comes from the judge grading B's P2 `partial`. The owner's own blind per-point grade for this record (spot-check S09) is `yes`, which maps to `correct`. So this discordance depends on one judge point grade and is weak evidence against B. |
| 021 | evidence hit@1 1 → 0 | A r1 = #20 "File-based apps" with P1,P2. B spreads them over r1 (P1) and r2 (P2). Both `partially_correct`. |
| 022 | label `false_refusal` → `correct`; section hit@1/@3/@5 0 → 1 | Two slots: S1 = "UseStatusCodePagesWithRedirects", S2 = "…WithReExecute". **All five A chunks are #13 version variants of S2 only** (the near-duplicate failure mode). S1 never enters A's context, and the LLM refused. B's windows straddle the boundary between the two sections ("…Shouldn't preserve and return the original status code… ### UseStatusCodePagesWithReExecute…"), so every B chunk hits both slots, and B answered correctly. Worked example 4. |
| 023 | evidence hit@1 0 → 1 | Same pattern as 003: A r1 = P1, and P2/P3 are at A r2–r3. B r1 (a fence-cutting window) = P1–P3. Both correct. |
| 026 | groundedness 0 → 1 | Retrieval is equivalent (A r1 = P1, P2 at r3; B r1 = P1, r2 = P2). A's "unsupported claim" is a download link that is in A's retrieved chunk 3. This is a judge artefact (see "Evaluation-side failures"). |
| 027 | label `correct` → `partially_correct`; evidence hit@1/@3/@5 1 → 0 | A r1 = the whole 1,145-char "Validation failure error response" section, with all three quotes. B r1 `12:fixed-1600:0016` starts mid-sentence ("h an implementation that also supports formatting responses as XML…") and cuts a fence. The P1 sentence ("MVC responds with a ValidationProblemDetails response…") is in the previous window, which was not retrieved. B's answer omits ValidationProblemDetails. Worked example 2. |
| 031 | source/section hit@5 1 → 0; evidence hit@1 1 → 0 | Two slots: #04 "`default` expressions" and #26 "Value types and reference types". A finds S2 at rank 4. B's top 5 contain two #04 windows (one fence-cutting) and no #26 chunk. Both answers are correct (the judge accepted the answer without the S2 evidence). |
| 032 | source/section hit@3 1 → 0; evidence hit@3 1 → 0 | Two slots: #13 "IExceptionHandler" and #10. B's ranks 1–3 are three #13 version variants of the same section (`0009`, `0043`, `0075`, all fence-cutting), which push #10 to rank 4. A has #10 at rank 1. Both correct. |

### Failure analysis (EXP-001 §2)

**Which records count.** A failure is a record whose result is not a success (`correct`, or `correct_refusal` on a
corpus-insufficient case) or whose section hit@5 = 0.

**How a stage is chosen.** `experiment.classify_failure` gives every failure one primary stage, first rule that applies:
1. `retrieval_miss`: section hit@5 = 0. On a two-slot case this means one slot has no top-5 chunk.
2. **gate refusal → `refusal`** (owner addendum item 4). A false refusal where the threshold gate fired. The LLM never
   saw the chunks, so this rule comes before `chunking`. A chunking signal on the same record is kept as a secondary
   tag (016:B, 018:B).
3. `chunking`: the section was hit but evidence hit@5 = 0, or the only section-hitting chunk cuts a code fence.
4. `ranking`: the first section hit is at rank ≥ 3 and the answer cites a wrong chunk ranked above it.
5. `refusal`: a false refusal by the LLM, or a hallucination.
6. `generation`: the right chunk was in context but the answer is incomplete or wrong.
7. `citation`: the answer is correct but a citation is missing, unsupported or on the wrong section.

**The citation stage cannot fire.** Under this trigger a correct answer is a failure only when section hit@5 = 0, and
rule 1 takes it first. The three correct answers with a citation defect are therefore listed separately instead:
- 005:A: section precision 0.5, judge support 0.5;
- 015:A: section precision 0.5;
- 009:B: judge support 0.5.

These are in `comparison.json` `citation_defects_on_correct_answers`.

**Other tags and the manual read.** The secondary tag `language` marks a VI case that fails while its EN twin passes.
I read all 18 failure rows against the chunk facts, and no label needed an override (`failure-overrides.json` is `{}`).
`Q-EVAL-002:B` is unlabelled and is not classified (see below).

<!-- AUTO:failure-counts -->
| Stage | Arm A | Arm B |
|---|---|---|
| retrieval_miss | 2 | 2 |
| chunking | 0 | 1 |
| ranking | 0 | 0 |
| refusal | 3 | 2 |
| generation | 4 | 4 |
| citation | 0 | 0 |
| **total** | 9 | 9 |
<!-- /AUTO:failure-counts -->

<!-- AUTO:failures -->
| Case | Arm | Lang | Result | Stage | Rule | Secondary |
|---|---|---|---|---|---|---|
| Q-EVAL-001 | A | en | false_refusal | refusal | gate: top-1 score 0.6779 < threshold 0.686 | — |
| Q-EVAL-010 | A | vi | partially_correct | generation | partially_correct: expected section and evidence in context | language |
| Q-EVAL-012 | A | vi | partially_correct | generation | partially_correct: expected section and evidence in context | language |
| Q-EVAL-016 | A | vi | false_refusal | refusal | gate: top-1 score 0.6269 < threshold 0.686 | — |
| Q-EVAL-017 | A | en | partially_correct | generation | partially_correct: expected section and evidence in context | — |
| Q-EVAL-018 | A | vi | false_refusal | refusal | gate: top-1 score 0.6753 < threshold 0.686 | — |
| Q-EVAL-021 | A | en | partially_correct | generation | partially_correct: expected section and evidence in context | — |
| Q-EVAL-022 | A | vi | false_refusal | retrieval_miss | section_hit@5 = 0 (slot fraction 0.5) | — |
| Q-EVAL-030 | A | vi | partially_correct | retrieval_miss | section_hit@5 = 0 (slot fraction 0.5) | — |
| Q-EVAL-010 | B | vi | partially_correct | generation | partially_correct: expected section and evidence in context | language |
| Q-EVAL-016 | B | vi | false_refusal | refusal | gate: top-1 score 0.6246 < threshold 0.686 | chunking |
| Q-EVAL-017 | B | en | partially_correct | generation | partially_correct: expected section and evidence in context | — |
| Q-EVAL-018 | B | vi | false_refusal | refusal | gate: top-1 score 0.6483 < threshold 0.686 | chunking |
| Q-EVAL-020 | B | vi | partially_correct | generation | partially_correct: expected section and evidence in context | — |
| Q-EVAL-021 | B | en | partially_correct | generation | partially_correct: expected section and evidence in context | — |
| Q-EVAL-027 | B | en | partially_correct | chunking | section hit but evidence_hit@5 = 0 (no required-point quote whole in one chunk) | — |
| Q-EVAL-030 | B | vi | partially_correct | retrieval_miss | section_hit@5 = 0 (slot fraction 0.5) | — |
| Q-EVAL-031 | B | en | correct | retrieval_miss | section_hit@5 = 0 (slot fraction 0.5) | — |
<!-- /AUTO:failures -->

Reading:
- **Most failures are shared.** 010, 016, 017, 018, 021 and 030 fail in both arms with the same stage (016 and 018 at
  the gate; 030 misses slot S1, #03 "Follow test naming standards", in both arms: all five chunks are #28; 010, 017 and 021 are `generation`
  with the evidence in context).
- **Arm A's own failures** are:
  - 001, a gate refusal (threat 1);
  - 012, `generation` and `language` (EN twin 011 is correct);
  - 022, a `retrieval_miss` caused by near-duplicate version variants.
- **Arm B's own failures** are:
  - 020, `generation` (judge-dependent, see the table);
  - 027, `chunking`: the window cut the evidence;
  - 031, a `retrieval_miss` on the second slot. The answer was still judged correct.

  Each arm has 9 failures.
- **`ranking` never fired.** Where a section hit was at rank ≥ 3, the answer did not cite a wrong higher-ranked chunk.

### ADR-0003 expected failure modes → real cases

Signals per record are in `comparison.json` `failure_mode_signals`, computed over the top 5 of every record in both arms.

| Expected failure mode | Observed? | Evidence |
|---|---|---|
| Mixed-version answers (#13/#17/#23) | **Retrieval yes, answers not observed.** | The top 5 are filled with version variants of one section: 003/004 (#13 "Developer exception page", 2–3 repeated headings), 007/008/025 (#23, 2–3 repeated headings), 023 (#13 IExceptionHandler). The judge found no contradiction with ground truth on any of them, and every one of these is `correct` in both arms. Checked cases: 003, 004, 007, 008, 023, 025. |
| Near-duplicate chunks filling top-k | **Yes.** | 022:A: all five chunks are #13 variants of the S2 section, S1 is crowded out, false refusal (worked example 4). 032:B: three #13 IExceptionHandler variants take ranks 1–3 and push #10 to rank 4. Same-heading repeats in the top 5, summed over 36 cases: A 46, B 48. D1 dedup removes only exact copies; near-duplicates remain by design (ADR-0003 D1). |
| Fixed-size chunks separating code from its explanation | **Yes, in Arm B.** | 45.05 % of B chunks cut a fence (A 3.27 %). 027:B: the section is split and the explanation sentence is lost (`chunking`). 018:B: B r1 starts inside the code and holds only P3, with the binding-order explanation in the unretrieved previous window (gated anyway; `chunking` secondary). 016:B: no whole required-point quote in any window. 015:B and 009/010:B: a fence-cutting window outranks the section's main chunk. |
| Link-list sections (#08, #09) retrieved as noise | **Not observed.** | 0 chunks from #08/#09 in any top 5 in either arm (36 cases × 2 arms). Checked cases include the three tagged `link_list_noise` (019, 021, 035). |
| Tiny docs (#09, #22, #29) as a single chunk | **Yes, and it helped B.** | Chunks per tiny doc, A / B: #09 4 / 1, #22 3 / 2, #29 3 / 1. 011/012 (#29): B's single chunk holds P1–P3, while A splits them over two chunks (012:A omits P2). 001 (#22): B's 1,600-char window scores above the gate, A's 848-char section does not. |
| Large docs outranking small docs | **Only as low-rank noise.** | #13/#17/#23 chunks in the top 5 of cases that expect none of them: A 9, B 13, mostly at ranks 4–5 or on corpus-insufficient cases (033, 034). On answerable cases (002, 011:B, 027) the expected small doc still held rank 1, and no section hit was lost. Checked cases: 027 and 029 (tagged `large_doc_outranks_small`), both section hit@5 = 1 in both arms. |

### Worked examples (chunk text from the run records)

**1. Q-EVAL-001: same sentence, different score, different gate decision.**

The question asks whether EF Core still queries the database when the entities are already loaded. Both arms'
rank-1 chunk contains "Queries are always executed against the database even if the entities returned in the result
already exist in the context."
- A (`22:header-1600:0000`, 848 chars, the "Querying Data" section only) scored **0.6779**, and the gate refused.
- B (`22:fixed-1600:0000`, 1,600 chars: the same section plus "## Loading all data …") scored **0.6908**, so the gate
  passed and the answer was `correct`.

The retrieval quality is equal. The 0.686 threshold, tuned on A's dev scores, sits between the two.

**2. Q-EVAL-027: a fixed window cuts the evidence.**

The question asks what an API controller returns on a validation failure and how to change it.
- A's rank 1 is the whole section: "### Validation failure error response  For web API controllers, MVC responds with a
  [ValidationProblemDetails] … response type when model validation fails. … MVC uses the results of
  [InvalidModelStateResponseFactory] …". It contains all three quotes, and A's answer was `correct`.
- B's rank 1 starts mid-sentence: "h an implementation that also supports formatting responses as XML, in `Program.cs`:
  ``` builder.Services.AddControllers() .ConfigureApiBehaviorOptions(options …". The ValidationProblemDetails sentence
  is in the preceding window, which was not retrieved. B's answer says "controllers automatically return `400 Bad
  Request`" and never names ValidationProblemDetails (P1), so it is `partially_correct`, stage `chunking`.

**3. Q-EVAL-018 (VI): code separated from its explanation.**

The question is why `c is not >= 'a' and <= 'z'` misbehaves.
- A's rank 1 is the whole "### Precedence and order of checking" section. It holds the binding order ("The `not`
  pattern binds to its operand first…"), the wrong parse and the fix.
- B's rank 1 starts "…he `>= 'a' and <= 'z'` expression: ``` // Correct pattern. Force `and` before `not` …". It has
  the fix (P3) but not the explanation (P1, P2).

Both arms were gated (top-1 A 0.6753, B 0.6483 < 0.686). The case shows the mechanism, but the gate hides its effect
on the answer.

**4. Q-EVAL-022 (VI): section boundaries cut both ways.**

The question compares `UseStatusCodePagesWithRedirects` and `…WithReExecute`.
- A's five chunks are all "### UseStatusCodePagesWithReExecute …" from different #13 versions: header-aware chunking
  keeps the two sibling sections apart, and the version variants fill every slot. A's LLM answered "Bộ tài liệu hiện
  có không chứa đủ thông tin…" (insufficient).
- B's rank 1 reads "…Shouldn't preserve and return the original status code with the initial redirect response.
  ### UseStatusCodePagesWithReExecute The [UseStatusCodePagesWithReExecute] …". The window crosses the heading, so each
  B chunk carries the end of one section and the start of the other, and B answered `correct`.

**5. Q-EVAL-012 (VI): tiny doc #29.**
- A's context is "## Cause The … attribute is applied to a type that the validation source generator can't access…"
  (681 chars) and "## How to fix violations Make the attributed type and each of its containing types public or internal…"
  (396 chars) as two chunks. A's answer covers the cause and the fix but not "the generator silently skips validation"
  (P2), so it is `partially_correct`, stage `generation`, tag `language` (EN twin 011 is `correct`).
- B's single 1,282-char chunk holds the title table, Cause and fix together. B's answer includes "Bộ tạo nguồn sẽ tự
  động bỏ qua validation cho kiểu này một cách âm thầm" ("the generator silently skips validation for this type").

### Evaluation-side failures (not system failures)

These are errors or noise in the measurement, not in the assistant.
- **Spot-check S03 (`Q-EVAL-012:A`): the judge credited a claim the answer doesn't make.** The judge graded P2 ("the
  generator silently skips validation") `partial`. The owner graded it `no`: A's answer never says this. The mapped
  label is `partially_correct` either way, so no count changes, but it shows the judge can be generous on a point.
- **Marker-22 format error (`Q-EVAL-002:B`).** The judge's verdict gave citation marker `22` where the answer's only
  marker is `[1]`. `22` is the source id printed next to `[1]` in the judge prompt ("[1] #22 — Querying Data"). The
  strict parser rejected it twice (temperature 0 reproduced it), so the record is unlabelled and out of every
  answer-level pair.
- **Both groundedness discordances are judge artefacts.** Groundedness is A 0.926 vs B 1.000 (b = 0, c = 2, p = 0.5,
  n = 27), and both A "not grounded" verdicts come from the judge's reasoning:
  - On 005:A the judge lists "avoid using the Task Parallel Library" as unsupported, while its own reason text ends
    "(wait, the table actually does say 'Avoid using the Task Parallel Library' for I/O-bound, so the claim is
    supported)".
  - On 026:A it flags a .NET 8 download link as unsupported "according to strict ground truth boundaries", though the
    link comes from A's retrieved chunk 3.

  Groundedness as scored here therefore says nothing reliable about the chunkers.
- **Two label differences depend on single judge point grades.** 020 (`correct` → `partially_correct`, S09) and, in
  both arms, 017:B (S10): the owner's blind per-point grades map to `correct` where the judge gave `partially_correct`.

## 5. What was learned and what to try next

**Learned**

- **The choice matters less than expected for finding the section, and more for what one chunk holds.** Both arms put
  the expected section in the top 5 on 30 of 32 answerable cases. They differ in whether one chunk carries the whole
  answer: A when the answer is one section, B when it spans adjacent short sections or a tiny doc. No answer-level
  difference is statistically reliable at n = 31. Accuracy: A 0.710 vs B 0.742, Δ +0.032, CI [−0.097, +0.161], p = 1.0.
- **The one reliable cost is tokens.** B sends about 494 more prompt tokens per answer (+30 %). Its chunks also cut
  code fences 14× as often, which caused the one `chunking` failure (027:B).
- **Several "arm differences" are really threshold or judge effects:**
  - 001: the gate threshold was tuned on Arm A;
  - 020: one judge point grade;
  - 005/026 groundedness: judge reasoning errors.

  Without the chunk-level read, these would have been credited to the chunker.

**Decisions I would make now** (none applied here: the rule for this task is no parameter change; any change needs an
ADR):
- Keep **Arm A (header-aware)** as the default. Answer quality is equivalent at this n, and A is cheaper per answer
  (−494 prompt tokens), keeps code blocks whole (3 % vs 45 % fence cuts) and gives section-aligned citations. B does avoid one A failure by design: its windows cross the
  boundary between sibling sections (022). A's own failures (001 gate, 012 generation, 022 near-duplicate variants) are
  addressed by the next experiments (per-arm threshold, diversified hybrid retrieval), not by switching chunkers.
- Treat the gate threshold as **per-arm**. A threshold tuned on one arm's score distribution should not be used to
  judge another arm.
- Do not use groundedness from this judge as a headline metric without a second grader. Both disagreements examined
  here were judge errors.

**Next experiments** (each with the metric that would show success):

1. **Gate threshold recalibration on a larger dev set, per arm.** Collect at least 30 dev cases per arm (answerable +
   corpus-insufficient) and pick each arm's threshold on its own score distribution.
   - *Success:* false-refusal rate on answerable cases below the current 0.129 (A) / 0.065 (B), with correct refusal on
     corpus-insufficient cases staying 100 %.
   - Report both on the eval split once, with the paired McNemar b/c.
2. **Hybrid retrieval (BM25 + dense) with version-variant diversification.** Exact API names such as
   `UseStatusCodePagesWithRedirects` and `IExceptionHandler` are lexical, and version variants crowd the top 5 (022:A,
   032:B).
   - *Success:* the two-slot cases (017, 022, 030, 031, 032) reach section hit@5 = 1 in both slots, and strict MRR
     rises (A 0.964, B 0.928), with evidence hit@5 not dropping.
3. **VI → EN query rewriting before retrieval** (ADR-0003 D9 optional).
   - *Success:* the VI-minus-EN gap on the parallel subset shrinks (accuracy, evidence hit@1), and the `language`-tagged
     failures (010, 012:A) disappear.
   - VI top-1 scores should also rise above the gate: the VI gate refusals 016 and 018 have top-1 0.62–0.68.

   Measure on the 7 parallel pairs plus the 9 VI-only cases, with the paired tests used here.

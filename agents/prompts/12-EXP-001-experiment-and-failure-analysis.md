# EXP-001 — Arm A vs Arm B: experiment report + failure analysis (gate G6)

Read `agents/prompts/_common.md` first and follow it.
Read: ADR-0003 (D7, D8, "Expected failure modes"), EPIC-05 evaluation report, `summary-*.json`, both run folders, `stats-arm-a.json`, `stats-arm-b.json`.
Entry: EVAL-004 done. **Rule: no parameter may change in this task.** New ideas go to "what to try next".

## 1. Comparison script `scripts/experiments/compare_arms.py --run-a RUN --run-b RUN` → `data/experiments/exp-001/`
- `comparison.json` + Markdown tables (inserted via AUTO markers into the report):
  | Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test p | n |
  for: source/section/evidence hit@1/3/5, MRR, accuracy, lenient accuracy, groundedness, false-refusal, hallucination, citation support/section precision, latency p50/p95 per stage, tokens per question. Rows repeated per language and for the parallel subset.
- **Paired statistics** (same cases in both arms):
  - binary metrics → exact McNemar test on the discordant pairs (report b and c counts, not only p);
  - continuous (MRR, latency, tokens) → Wilcoxon signed-rank;
  - 95 % CI of Δ → paired bootstrap, 10 000 resamples, seed 42.
  - Use `scipy` only if already installed; otherwise implement exact McNemar (binomial) and bootstrap in plain Python and unit-test them. No new heavy dependency without asking.
  - Wording rule: p ≥ 0.05 → "no statistically reliable difference at n = X", never "A is better".
- `per_case_diff.csv`: case_id, language, tags, A/B section_hit@5, A/B rank of first hit, A/B result → plus lists `a_only_hits`, `b_only_hits`, `both_miss`.
- Chunk-level explanation data: for every discordant case, the top-3 chunks of each arm (chunk_id, heading path, score, first 200 chars, whether it contains the evidence quote, whether it cuts a code fence).

## 2. Failure analysis — `data/experiments/exp-001/failures.csv` + report section
Every record with `result ≠ correct` or `section_hit@5 = 0` (per arm) gets ONE primary stage, decided in this order (first that applies):
1. `retrieval_miss` — no top-5 chunk overlaps the expected section;
2. `chunking` — the evidence quote is not fully inside any single retrieved chunk although the section was hit (evidence_hit = 0, section_hit = 1), or the only hit chunk cuts a code fence;
3. `ranking` — section hit only at rank ≥ 3 and the answer used/cited higher-ranked wrong chunks;
4. `refusal` — false_refusal (show gate vs LLM reason) or hallucination;
5. `generation` — right chunk in context, answer incomplete/wrong;
6. `citation` — answer correct, citation missing/unsupported/wrong section;
plus a secondary tag `language` when the EN pair of a VI case passes and the VI one fails.
Classification is done by a script from the record fields (deterministic rules above); you then read 100 % of the failures and may override a label only with a written reason in an `override_reason` column.
Report: counts per stage × arm table; then map real case IDs to **each ADR-0003 expected failure mode** (mixed versions #13/#17/#23, near-duplicate top-k, code separated from explanation, link-list noise #08/#09, tiny docs #09/#22/#29, large-doc dominance) — or "not observed (checked cases: …)". Add 3–5 worked examples with the actual chunk text snippets from both arms.

## 3. Report `docs/reports/epics/EPIC-06-experiment.md` — exactly the brief's 5 points
1. **What changed:** only the chunker (A header-aware ≤ 1,600 vs B fixed 1,600/200); table of everything held constant with its value (embedding model + dim, distance, top-k, threshold, prompt version, answer model, judge model, question-file hash).
2. **How evaluated:** same frozen question set, same runner/metrics, run ids, paired design and why paired.
3. **Results:** AUTO tables + chunk stats side by side (count, size p50/p90, % code-fence cuts, tiny-doc chunk counts).
4. **Why they differ:** each claim tied to evidence (chunk stats, case IDs, worked examples). Where there is no reliable difference, explain why that is plausible too (e.g. header sections already ≈ 1,600 chars, the D5 heading prefix helps both arms equally).
5. **What was learned + next:** decisions you would make now, and 2–3 follow-up experiments (e.g. hybrid search, VI→EN rewriting, 1,200 vs 3,200 chars) each with the metric that would show success.
Snapshot → `docs/snapshots/experiments/exp-001.md`.

## Acceptance
Every number in the report traces to a file in `data/experiments/exp-001/` or a run folder; stats functions unit-tested on hand examples; no parameter/config changed (`git diff` on `config/` is empty).

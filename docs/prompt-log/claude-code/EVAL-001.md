# EVAL-001 — Design evaluation dataset (addendum to the existing prompt)

Read `agents/prompts/_common.md` first and follow it.
The full prompt already exists: `docs/prompt-log/claude-code/EVAL-001 — Design Evaluation Dataset.md`. Execute it exactly, plus this addendum.

## Addendum
1. **OD-4 / OD-5 proposals** (ask the user, then write into `docs/specs/evaluation-spec.md`):
   - Recommended mix: ~36 blueprints = ~26 answerable single-source, ~4 cross-document, ~4–6 corpus-insufficient; ~18 EN / ~18 VI; 6–8 parallel EN/VI groups.
   - Recommended `result` values: `correct`, `partially_correct`, `incorrect`, `correct_refusal` (unanswerable, system refused), `false_refusal` (answerable, system refused), `hallucination` (unanswerable, system answered).
2. **Corpus-insufficient cases** must be *near-miss*: topically adjacent to the corpus (same stack) so they actually test the refusal rule. Prove absence: grep all 24 accepted docs for the key terms and record the grep commands + zero-hit result in `evidence-map.yaml`. Never base them on excluded docs 14/19/24/27.
3. Every answerable blueprint must carry a **verbatim evidence quote** (≤ 300 chars) copied from the source, plus `source_id` and a heading path that exists in `data/processed/documents/section-inventory.jsonl`.
4. Add a small **dev set** (5–6 extra blueprints, disjoint from the eval set, marked `split: dev`) — later used to tune the insufficient-information threshold and the prompt without touching the eval set (prevents test-set leakage).

# EPIC-05 evaluation report (generated)

## Retrieval metrics

<!-- AUTO:retrieval -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| metric | lenient (headline) | strict |
| --- | --- | --- |
| source_hit@1 | – (n=0) | – (n=0) |
| section_hit@1 | – (n=0) | – (n=0) |
| source_hit@3 | – (n=0) | – (n=0) |
| section_hit@3 | – (n=0) | – (n=0) |
| source_hit@5 | – (n=0) | – (n=0) |
| section_hit@5 | – (n=0) | – (n=0) |
| mrr | – (n=0) | – (n=0) |
| source_mrr | – (n=0) | – (n=0) |
| slot_fraction@5 | – (n=0) | – |
| source_slot_fraction@5 | – (n=0) | – |
| evidence_hit@1 | – (n=0) | – |
| any_evidence_hit@1 | – (n=0) | – |
| evidence_hit@3 | – (n=0) | – |
| any_evidence_hit@3 | – (n=0) | – |
| evidence_hit@5 | – (n=0) | – |
| any_evidence_hit@5 | – (n=0) | – |
| evidence_hit_via_alternate_only@5 | – (n=0) | – |

- duplicate rule changed 0 of 0 scored case x arm value(s).
- evidence_hit_via_alternate_only@5 cases: (none).
- corpus-insufficient cases have no expected spans and are excluded from every row above.

- answerable cases refused by the retrieval gate: (none).
<!-- /AUTO:retrieval -->

## Answer metrics

<!-- AUTO:answer -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| metric (denominator: labelled answerable records) | value |
| --- | --- |
| accuracy | 1.000 (2/2) |
| lenient_accuracy | 1.000 (2/2) |
| groundedness_rate | 1.000 (2/2) |
| points_covered_mean | 1.000 (n=2) |
| false_refusal_rate | 0.000 (0/2) |

- labels (answerable): correct=2, partially_correct=0, incorrect=0, false_refusal=0.
- runner-error records (no answer to label; excluded from every denominator in this report): (none).
- unlabelled records (judge missing or judge_error; excluded from every denominator in this report): (none).

- answerable cases refused by the retrieval gate: (none).
<!-- /AUTO:answer -->

## Refusal metrics

<!-- AUTO:refusal -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| metric (denominator: labelled unanswerable/corpus-insufficient records) | value |
| --- | --- |
| correct_refusal_rate | 1.000 (1/1) |
| hallucination_rate | 0.000 (0/1) |

- labels (unanswerable): correct_refusal=1, hallucination=0.
- runner-error and unlabelled records are listed once, in the answer table above (the list covers both answerable and unanswerable records).
<!-- /AUTO:refusal -->

## Citation metrics

<!-- AUTO:citation -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| metric (denominator: answered answerable records, n=0) | value |
| --- | --- |
| presence_rate | – (n=0) |
| source_precision | – (n=0) |
| section_precision | – (n=0) |
| support_rate (judge support check, n=0) | – (n=0) |

- auto_class (automatic span check): correct_evidence=0, correct_source_wrong_evidence=0, unsupported_citation=0, citation_missing=0.
- judge_class (judge support check, n=0): correct_evidence=0, correct_source_wrong_evidence=0, unsupported_citation=0, citation_missing=0.
- related_citation_count (citations on an insufficient answer; counted only, not scored): 0.
- answered_unanswerable_with_citations (diagnostic, not scored): 0.
<!-- /AUTO:citation -->

## Latency

<!-- AUTO:latency -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| stage | n | mean_ms | p50_ms | p95_ms | max_ms |
| --- | --- | --- | --- | --- | --- |
| main embed_query | 6 | 0.1 | 0.1 | 0.1 | 0.1 |
| main retrieve | 6 | 18.5 | 2.6 | 98.8 | 98.8 |
| main generate | 2 | 2141.3 | 1716.2 | 2566.3 | 2566.3 |
| main total | 6 | 732.4 | 2.9 | 2568.5 | 2568.5 |
| judge main generate | 2 | 12200.0 | 2051.7 | 22348.3 | 22348.3 |
| judge main total | 2 | 13311.0 | 3152.3 | 23469.8 | 23469.8 |

- percentile method: nearest-rank (`evaluation-spec.md` § Latency): no interpolation, every percentile is a value that was actually measured.
- answer calls: 6 clean record(s) (retry_count==0, no fallback model); retried/fallback: 0.
- judge calls: 2 clean call(s); retried/fallback: 0.
<!-- /AUTO:latency -->

## Cost (estimate)

<!-- AUTO:cost -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| stage | calls | models | prompt_tokens | output_tokens | thoughts_tokens | estimate |
| --- | --- | --- | --- | --- | --- | --- |
| answer | 2 | gemini-3.5-flash-lite | 3235 | 327 | 0 | $0.0018 |
| judge | 2 | gemini-3.5-flash-lite | 2180 | 435 | 0 | $0.0017 |

- estimate: list price per 1M tokens; the runs used the free tier and were not billed
- pricing source: https://ai.google.dev/gemini-api/docs/pricing?hl=en (retrieved 2026-09-27).
<!-- /AUTO:cost -->

## Per language

<!-- AUTO:per_language -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| group | records | accuracy | lenient_accuracy | correct_refusal_rate | hallucination_rate | source_hit@5 (lenient) | section_hit@5 (lenient) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| language=en | 4 | 1.000 (1/1) | 1.000 (1/1) | 1.000 (1/1) | 0.000 (0/1) | – (n=0) | – (n=0) |
| language=vi | 2 | 1.000 (1/1) | 1.000 (1/1) | – (n=0) | – (n=0) | – (n=0) | – (n=0) |
<!-- /AUTO:per_language -->

## Parallel EN/VI subset

<!-- AUTO:parallel -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| group | records | accuracy | lenient_accuracy | correct_refusal_rate | hallucination_rate | source_hit@5 (lenient) | section_hit@5 (lenient) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| overall | 6 | 1.000 (2/2) | 1.000 (2/2) | 1.000 (1/1) | 0.000 (0/1) | – (n=0) | – (n=0) |
| parallel EN/VI subset | 0 | – (n=0) | – (n=0) | – (n=0) | – (n=0) | – (n=0) | – (n=0) |
<!-- /AUTO:parallel -->

## Per case

<!-- AUTO:per_case -->
Runs: `20260927-dev-A-full-05680f9` (arm A, mode full, split dev, 3 record(s)); `20260927-dev-A-retrieval-05680f9` (arm A, mode retrieval, split dev, 3 record(s)). Total scored records: 6. Excluded from retrieval and citation scoring (answerable, but outside `expected-spans-v1.json`, which covers the eval split only): Q-DEV-001:A, Q-DEV-002:A. **20260927-dev-A-full-05680f9, 20260927-dev-A-retrieval-05680f9 use the dev split - dry-run/tooling data only, never reported as evaluation results (`evaluation-spec.md` § Dataset mix).**

| case_id | arm | mode | split | language | status | result | points_covered | citation_auto_class | gate_fired | latency_total_ms | spans_unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-DEV-001 | A | full | dev | en | ok | correct | 1.000 | – | no | 2568.5 | yes |
| Q-DEV-001 | A | retrieval | dev | en | ok | – | – | – | no | 99.0 | yes |
| Q-DEV-002 | A | full | dev | vi | ok | correct | 1.000 | – | no | 1719.4 | yes |
| Q-DEV-002 | A | retrieval | dev | vi | ok | – | – | – | no | 2.7 | yes |
| Q-DEV-005 | A | full | dev | en | ok | correct_refusal | – | – | yes | 2.9 | no |
| Q-DEV-005 | A | retrieval | dev | en | ok | – | – | – | yes | 2.1 | no |
<!-- /AUTO:per_case -->

## Judge spot-check agreement (owner)

<!-- AUTO:judge_agreement -->
*(Owner judge spot-check not yet run. After the owner fills `human_result` in `docs/reviews/evaluation/judge-spot-check-<run>.md`, run `scripts/evaluation/score_spot_check.py <file>` to fill this section: agreement %, Cohen's kappa, the confusion matrix and the list of disagreements.)*
<!-- /AUTO:judge_agreement -->

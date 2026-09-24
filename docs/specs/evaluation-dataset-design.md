# Evaluation dataset design (EVAL-001)

Status: **proposed**, waiting for the owner's review. Date: 2026-09-24. Task: EPIC-05 / EVAL-001.
Machine-readable files: [`blueprint.yaml`](../../data/evaluation/questions/blueprint.yaml) (authoritative), [`coverage-matrix.yaml`](../../data/evaluation/questions/coverage-matrix.yaml) (generated), [`evidence-map.yaml`](../../data/evaluation/questions/evidence-map.yaml).
Decisions it rests on: `evaluation-spec.md` (OD-4 mix and OD-5 labels, decided by the owner 2026-09-24), ADR-0003 (D1–D9), ADR-0004, `generation-spec.md`, `citation-spec.md`.

A **blueprint** is the plan for one evaluation question: what it tests, where the answer is, what a correct answer must contain, and what a valid citation must show. The final question wording is written later, in EVAL-002.

## 1. Purpose
The dataset has to show two things with evidence: that the assistant works (answers are correct, grounded and cited, and it refuses when the documents don't know), and whether the two chunking approaches (Arm A header-aware, Arm B fixed-size; ADR-0003 D7) behave differently. So each case is chosen for what it can *reveal*, not because it is an interesting question.

## 2. Target size
36 evaluation cases (OD-4): 28 single-source + 4 cross-document answerable (32 answerable) + 4 "not in the documents". The brief needs at least 30 records with an expected source, so up to 2 answerable cases can be dropped when the questions are checked in EVAL-002. A separate **dev set** of 6 cases is for tuning the prompt and the refusal rule. It never appears in reported results, which keeps the evaluation set unseen.

## 3. Languages
18 English and 18 Vietnamese (ADR-0003 D9). Answers must be in the question's language; citation excerpts stay English (`generation-spec.md`, `citation-spec.md`).
Per-language difficulty is not identical (EN: 3 easy / 10 medium / 5 hard; VI: 4 / 7 / 7). So **compare languages mainly on the parallel subset** (next section), where difficulty is the same by construction. Overall per-language numbers are still reported, with this caveat.

## 4. Parallel EN/VI groups
7 groups (PG-001…PG-007, 14 cases). In a group, the EN and VI case share the same expected sources, answer points and acceptance criteria; a test checks that they are identical. The groups are spread so the language effect isn't confused with difficulty or document size: difficulty 2 easy / 3 medium / 2 hard, document size 2 tiny / 3 medium / 2 huge.
Proposed wording rule for EVAL-002: the Vietnamese question is natural Vietnamese, but API names and identifiers stay as written (`DbContext`, `UseExceptionHandler`). That choice affects cross-lingual retrieval, so it is written down.

## 5. Source coverage
- **Tiny documents with real content:** #22 (3 cases), #29 (2), #18 (1).
- **Version-heavy documents (ADR-0003):** #13 (5 cases), #23 (3), #17 (1).
- **Medium documents:** #01, #02, #03, #04, #10, #11, #12, #15, #16, #20, #21, #26, #28.
- **No expected-source case, on purpose:** #05, #08, #09 are hub pages: links with at most one-line captions. Measured on content lines: #08 has 48 link items out of 50, #09 13 of 15, and #05 is links, icons and short captions. They appear as **distractors** instead (link-list noise). #06 and #07 are covered by the dev set, so no evaluation case expects their sections. #07 'C# classes' and 'Create objects' appear only as acceptable alternates for 016 (reference assignment), a different fact from the dev case's 'Static classes'.
- No single document dominates: the most used is #13 with 5 of 32 answerable cases (16%). A huge document is the only expected source in 8 of 32 answerable cases (25%) and one of two sources in 1 more (032), although huge documents hold 73% of the text.

## 6. Retrieval difficulty
Only 3 answerable cases are plain semantic matches (`direct_semantic`: 001, 002, 021). The rest carry at least one challenge (full counts in the matrix):
- evidence in one specific subsection (9);
- the same topic in another document (11);
- version variants (9);
- two sources needed (4);
- tables or code next to the explanation (6);
- link-hub distractors (3);
- long sections (3);
- paraphrased symptoms instead of API names (5).

## 7. Cognitive levels
recall 6 · explain 6 · apply 9 · analyze 4 · compare 3 · diagnose 8. Recall is 17% of the set, so the dataset is not mostly look-ups.

## 8. Difficulty
easy 7 · medium 17 · hard 12. Difficulty means how hard the retrieval and reasoning are (competing copies, two sources, code to interpret), not how obscure the fact is.

## 9. Single vs cross-document
28 single-source, 4 cross-document. Each cross-document case joins two premises that are **each stated in one document**, and neither document alone answers:
- #10 + #22: default DbContext lifetime + loading one entity.
- #03 + #28: naming standard + the tutorial's test name.
- #04 + #26: `default` gives null for reference types + string is a reference type. #04 alone shows the value (`string? defaultString = default; // null`) but not why; #20 'Familiar C# features' can stand in for #26 (`stands_in_for`, §18).
- #13 + #10: IExceptionHandler is a singleton + DbContext is scoped + the lifetime rule.

Two of them use the same #10 section on purpose; each uses a different sentence from it and pairs it with a different document.

## 10. Failure-mode coverage (ADR-0003)
| Failure mode | Cases |
|---|---|
| Mixed-version answers | 003, 004 (developer exception page), 023 (.NET 10 vs .NET 8/9 diagnostics; every variant states both) |
| Near-duplicate chunks filling the top 5 | 020 (#04 vs #16), 022 (7 copies each), 024 (5 identical copies) |
| Fixed-size split of code/table from its explanation | 005, 006 (table), 016, 018 |
| Link-list / navigation noise | 019, 021 (#08 links), 035 (link-only section) |
| Tiny document as one chunk | 001, 002, 011, 012, 028 |
| Large document outranking a small correct one | 027 (#13 vs #12), 029 (#10 vs #22) |
| Evidence under one specific heading | 009, 010, 013, 014, 015, 025 |
| Repeated sections across variants | 007, 008, 017 |

The design does not assume which arm will win. For example, D1 removes chunks whose text exactly repeats an earlier chunk of the same document; whether the 5 identical copies in case 024 get removed depends on where each arm cuts the text. The case measures that instead of predicting it.

A structural finding from this task: in version-heavy pages the **intro of each later variant sits under the previous variant's last heading**, because variants have no H1 of their own. In #11, the intros of variants 2 and 3 are under "Additional resources". So correct text can carry a misleading heading path. Case 017 lists that heading as an acceptable alternate. EPIC-02 and the failure analysis should know about it.

## 11. "Not in the documents" cases
4 cases (033–036), 2 EN and 2 VI, all **near-miss**: close to what the corpus covers, so they really test the refusal rule.
- EF Core queries without tracking (near #22).
- Rate limiting (near the middleware pages).
- Scope validation: #10 has a section with that exact heading but only links.
- Verifying calls with Moq (near #03's mock terminology).

Each has an absence proof in `evidence-map.yaml`: the search terms, a case-insensitive search over the 24 accepted documents, and zero hits. Words that matched unrelated text are noted too ("track" in a URL, "limiter" in "delimiter"). A test re-runs every search. None is based on the excluded documents.
Scoring: `correct_refusal` or `hallucination` (OD-5). They are left out of source/section hit and MRR (proposal in `evaluation-spec.md`). The refusal rule itself is OD-9 (EPIC-03), and the dev set has 2 more near-miss cases for tuning it.

## 12. How the ground truth was made
- Sections were chosen from the EPIC-01 section inventory and topic map; then each chosen section was read in full.
  - Read completely: the tiny documents #09, #18, #22 and #29.
  - #08: the first 9 of its 21 sections were read; all 21 are link lists (measured above).
  - #05: its non-link lines were read (captions only).
  - #15: the question, the accepted answer and the follow-up replies were read.

  That is how the task's "inspect all 24 documents" was met: the structure of every document from the inventory (headings, sizes, variant counts), and full reads where a case was considered. The rest of the huge documents was not read line by line.
- Every answer point comes from the text of the cited section. No web search, no model memory, no outside best practice.
- Every answerable case carries verbatim evidence quotes (≤ 300 chars) with `source_id` and a heading path that exists in the inventory. Each quote lists the answer points it `supports`; a test fails if any required point has no supporting quote.
- Quotes keep the original Markdown, including link markup such as `[text](url)`. So the EVAL-002 validator and the citation judge must match quotes against a chunk's `display_text`, which keeps links (ADR-0003 D5), after the same whitespace/line-ending normalization. They must not match against `embed_text`, where links are reduced to their text. A test checks that each quote appears inside that section's text (any variant), and, when a case sets `evidence_variant`, inside that variant.
- Variants are never labelled with guessed versions (ADR-0003). When a case depends on one variant, the blueprint records `evidence_variant` by inventory number. No case does at present: 023 used it until the independent review showed that variants 2 and 3 state the .NET 10 behavior too, in other words.
- Ground truth is written before any chunk or index exists (CLAUDE.md rule 9). Nothing here depends on retrieval results.

## 13. Answer quality
Each blueprint has answer points marked required or optional, `acceptable_variations`, and `must_not_claim` statements. `must_not_claim` merges the prompt's "unacceptable claims" and "must not claim", and is used for grounding checks. The result label and the points-covered score follow OD-5 (`evaluation-spec.md`). The judge is `gemini-3.5-flash-lite`, with a manual spot-check (ADR-0004 D12).

## 14. Citation quality
Each blueprint says what a valid citation must show: the right document, the right section (any variant unless `evidence_variant` is set), and text that actually supports the claim. The four outcomes in the brief map to the proposed labels `correct_evidence`, `correct_source_wrong_evidence`, `citation_missing` and `unsupported_citation`; the method is still OD-12.
Citations are judged on the chunk text, not on heading strings, for two reasons. Arm A labels a merged small section with the first section's heading (ADR-0003 D3), and Arm B uses the nearest preceding heading (D5). So a correct chunk may carry a different heading path. No page numbers are used.

## 15. Latency metadata
Latency is measured by the runner (EVAL-003), never estimated. Each case carries what's needed to slice it: language, scope, expected sources, difficulty, size class and, in EVAL-002, question length in characters. The expected chunk count becomes known after EPIC-02; the runner can record it.

## 16. Duplicate control
No two blueprints share the same information need, evidence and retrieval challenge. Pairs that look close were kept on purpose:
- 003/004 and 023 are both mixed-version cases in #13, but on different sections and facts.
- 013/014 (#10, middleware constructor) and 017 (#11, comparing middleware kinds) touch the same topic with different evidence and levels. They overlap more than first written: #10 'Service lifetimes', the expected section of 013/014, also answers 017's P1 and P2, so it is listed as an alternate for 017, and #11 sections are alternates for 013/014.
- 029 and 032 share one #10 section but use different sentences and different second documents.
- The parallel pairs are intentional repeats (language effect).
- The dev set uses no section that an evaluation case expects (test-checked).

## 17. Bias controls
- The set mixes cases where section boundaries should help (specific headings, tables, code next to prose) with cases where plain similarity should be enough, plus repeated, long and short sections.
- No case is worded to favor one arm. EVAL-002 notes ask for symptom-style wording rather than copying heading words.
- Expected behavior is stated as what a correct system does, never as "Arm X wins".
- Parameters stay frozen (ADR-0003); the question set is identical for both arms.

## 18. Schema
Ground truth and generated output are kept in **separate files**, because one question set is run through two arms and each arm produces its own answer.
- **Question file** (EVAL-002, `data/evaluation/questions/eval-v1.jsonl`, one line per case): `id`, `blueprint_id`, `split`, `question`, `language`, `parallel_group_id`, `scope`, `expected_answer` (short prose from the required points), `answer_points[{id,text,required}]`, `expected_sources[{source_id,heading_path,evidence_variant?}]`, `acceptable_alternate_sources[{source_id,heading_path,stands_in_for?,note}]` (`stands_in_for` is required in cross-document cases: the expected source the alternate replaces under the "all expected sources" hit rule; proposed, test-checked), `evidence[{source_id,heading_path,quote}]`, `acceptable_variations`, `must_not_claim`, `citation_criteria`, `cognitive_level`, `difficulty`, `size_class`, `failure_mode`, `retrieval_challenges`, `concepts`, `question_chars`. Insufficient cases have empty sources and points and `expected_behavior`.
- **Result file per arm** (EVAL-003/004, `data/evaluation/results/`): `case_id`, `arm`, `retrieved[{rank,chunk_id,source_id,heading_path,char_start,char_end,score}]`, `generated_answer`, `generated_citations[{chunk_id,source_id,heading_path,excerpt}]`, `latency_ms{embed_query,retrieve,generate}`, `model_used`, `retries`, `fallback_used`, `result`, `points_covered`, `citation_label`, `judge_notes`, `spot_checked`.
- The brief's five fields per record (question, expected answer, expected source, generated answer, result) come from joining the two files by `id`, per arm.

## 19. Coverage matrix
Generated by `scripts/evaluation/build_coverage_matrix.py`; a test fails if the file doesn't match the blueprints. It holds counts per scope, language, level, difficulty, size class, failure mode and retrieval challenge; cross-tables (language × scope/difficulty/level, difficulty × level); per-source use (expected / alternate / near-miss); and dominance checks:
- EN share 50%.
- Recall 17%, easy 19%.
- Huge documents 25% of answerable cases.
- Plain semantic matches 6%.
- Top source 16%.

Summary of all cases (`blueprint.yaml` is authoritative):

| ID | Lang | Group | Scope | Expected source(s) | Level | Difficulty | Failure mode |
|---|---|---|---|---|---|---|---|
| BP-EVAL-001 | en | PG-001 | single-source | #22 Querying Data | recall | easy | tiny_doc_single_chunk |
| BP-EVAL-002 | vi | PG-001 | single-source | #22 Querying Data | recall | easy | tiny_doc_single_chunk |
| BP-EVAL-003 | en | PG-002 | single-source | #13 Developer exception page | explain | hard | mixed_version |
| BP-EVAL-004 | vi | PG-002 | single-source | #13 Developer exception page | explain | hard | mixed_version |
| BP-EVAL-005 | en | PG-003 | single-source | #02 Recognize CPU-bound and I/O-bound scenarios | apply | medium | fixed_size_code_split |
| BP-EVAL-006 | vi | PG-003 | single-source | #02 Recognize CPU-bound and I/O-bound scenarios | apply | medium | fixed_size_code_split |
| BP-EVAL-007 | en | PG-004 | single-source | #23 Route constraints | diagnose | medium | repeated_version_sections |
| BP-EVAL-008 | vi | PG-004 | single-source | #23 Route constraints | diagnose | medium | repeated_version_sections |
| BP-EVAL-009 | en | PG-005 | single-source | #03 Avoid multiple Act tasks | explain | easy | specific_heading |
| BP-EVAL-010 | vi | PG-005 | single-source | #03 Avoid multiple Act tasks | explain | easy | specific_heading |
| BP-EVAL-011 | en | PG-006 | single-source | #29 Rule description, #29 How to fix violations | diagnose | medium | tiny_doc_single_chunk |
| BP-EVAL-012 | vi | PG-006 | single-source | #29 Rule description, #29 How to fix violations | diagnose | medium | tiny_doc_single_chunk |
| BP-EVAL-013 | en | PG-007 | single-source | #10 Service lifetimes | diagnose | hard | specific_heading |
| BP-EVAL-014 | vi | PG-007 | single-source | #10 Service lifetimes | diagnose | hard | specific_heading |
| BP-EVAL-015 | en | — | single-source | #01 Why async/await is preferred | compare | medium | specific_heading |
| BP-EVAL-016 | vi | — | single-source | #26 Value types and reference types | apply | easy | fixed_size_code_split |
| BP-EVAL-017 | en | — | single-source | #11 intro, #11 IMiddleware | compare | hard | repeated_version_sections |
| BP-EVAL-018 | vi | — | single-source | #21 Precedence and order of checking | diagnose | hard | fixed_size_code_split |
| BP-EVAL-019 | en | — | single-source | #21 List patterns | apply | medium | link_list_noise |
| BP-EVAL-020 | vi | — | single-source | #16 Integer literals | analyze | hard | near_duplicate_topk |
| BP-EVAL-021 | en | — | single-source | #20 File-based apps | recall | easy | link_list_noise |
| BP-EVAL-022 | vi | — | single-source | #13 UseStatusCodePagesWithRedirects, #13 UseStatusCodePagesWithReExecute | compare | hard | near_duplicate_topk |
| BP-EVAL-023 | en | — | single-source | #13 IExceptionHandler | explain | hard | mixed_version |
| BP-EVAL-024 | vi | — | single-source | #17 Disable shadow copying | apply | medium | near_duplicate_topk |
| BP-EVAL-025 | en | — | single-source | #23 Short-circuit middleware after routing | apply | medium | specific_heading |
| BP-EVAL-026 | vi | — | single-source | #15 (Q&A thread, single section) | diagnose | hard | none |
| BP-EVAL-027 | en | — | single-source | #12 Validation failure error response | recall | medium | large_doc_outranks_small |
| BP-EVAL-028 | vi | — | single-source | #18 Introduction | recall | easy | tiny_doc_single_chunk |
| BP-EVAL-029 | en | — | cross-document | #10 Entity Framework contexts, #22 Loading a single entity | apply | medium | large_doc_outranks_small |
| BP-EVAL-030 | vi | — | cross-document | #03 Follow test naming standards, #28 Add more tests | analyze | medium | none |
| BP-EVAL-031 | en | — | cross-document | #04 `default` expressions, #26 Value types and reference types | analyze | medium | none |
| BP-EVAL-032 | vi | — | cross-document | #13 IExceptionHandler, #10 Entity Framework contexts | analyze | hard | none |
| BP-EVAL-033 | en | — | corpus-insufficient | none (near #22, #10) | recall | medium | none |
| BP-EVAL-034 | vi | — | corpus-insufficient | none (near #11, #23, #10) | apply | medium | none |
| BP-EVAL-035 | en | — | corpus-insufficient | none (near #10, link-only section) | explain | hard | link_list_noise |
| BP-EVAL-036 | vi | — | corpus-insufficient | none (near #03) | apply | medium | none |

Dev set (tuning only): BP-DEV-001 #07 static classes (en) · 002 #04 native-sized integers (vi) · 003 #06 contextual keywords (en) · 004 #02 async void (vi) · 005 refresh tokens, insufficient (en) · 006 API versioning, insufficient (vi).

## 20. Open decisions and blockers
| Item | Status | Needed by |
|---|---|---|
| Owner review of the 42 blueprints | **Required before EVAL-002** | EVAL-002 |
| Citation-quality method (OD-12) and labels | Labels proposed in `evaluation-spec.md`; method open | EVAL-003 |
| Source hit for cross-document cases (all vs any) | Proposed: "all" primary, "any" secondary; an alternate counts for the expected source named in its `stands_in_for` | EVAL-003 |
| Correct-variant check for mixed-version cases | Proposed: section hit@5 counts any variant (D8); failure analysis also reports whether the `evidence_variant` was retrieved when a case sets one (none does at present) | EVAL-003 / EPIC-06 |
| Refusal rule for "insufficient information" (OD-9) | Open; dev set prepared for tuning it | EPIC-03 |
| Vietnamese wording rule (identifiers stay English) | Proposed | EVAL-002 |
| Questions may include short code taken from the page (016, 018) | Proposed | EVAL-002 |
| Mapping heading paths to character spans in normalized text (section hit@5) | Depends on EPIC-02: the inventory has raw line ranges, D8 needs normalized offsets | EPIC-02 / EVAL-003 |
| `size_class` thresholds (tiny < 3K chars, huge = #13/#17/#23) | Descriptive only; no metric depends on it | — |

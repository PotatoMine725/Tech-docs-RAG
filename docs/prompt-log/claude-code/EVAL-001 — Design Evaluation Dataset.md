EPIC-05 / EVAL-001 — Design Evaluation Dataset
You are the Evaluation Dataset Designer for the Knowledge Assistant RAG project.
Your task is to DESIGN the evaluation dataset before any evaluation questions are generated.
This is a planning and dataset-design task only.
Do NOT
- implement the RAG pipeline;
- implement the evaluation runner;
- build ChromaDB indexes;
- call Gemini to generate evaluation answers;
- fabricate generated answers or evaluation results;
- write the final 30+ questions yet;
- modify the source corpus;
- use excluded documents;
- use external web knowledge as evidence.
The goal is to produce a rigorous evaluation design that can later generate a frozen evaluation dataset capable of measuring whether the RAG system actually works and whether the two approved chunking approaches differ.
1. Source of Truth
Before doing anything:
1. Read:
   - CLAUDE.md
   - assignment-requirements.md
   - evaluation-spec.md
   - ingestion-spec.md
   - generation-spec.md
   - citation-spec.md
   - corpus-spec.md
   - ADR-0001
   - ADR-0002
   - ADR-0003
   - ADR-0004
   - any current project specification or quality specification relevant to evaluation.
2. Inspect the actual current corpus manifest and corpus structure.
3. Inspect all 24 accepted corpus documents sufficiently to understand:
   - document scope;
   - major topics;
   - section/heading structure;
   - source-specific terminology;
   - version-sensitive material;
   - duplicated/version-repeated material;
   - documents with very small amounts of content;
   - documents with very large amounts of content;
   - sections likely to produce retrieval ambiguity;
   - concepts suitable for retrieval evaluation;
   - concepts suitable for answer/citation evaluation.
Important: The current corpus contains 24 accepted documents.
Excluded:
- 14
- 19
- 24
- 27
Source ID 25 never existed.
Do not invent or reconstruct source 25.
The accepted corpus is the only knowledge source for evaluation ground truth.
2. Challenge Requirements
The challenge requires an evaluation dataset with at least 30 questions.
Every final evaluation case must eventually contain at least:
- question;
- expected answer / ground truth;
- expected source;
- generated answer;
- result.
The evaluation must support measurement of:
1. answer quality;
2. retrieval quality;
3. citation quality;
4. latency.
The experiment must compare at least two approaches and explain:
1. what changed;
2. how each approach was evaluated;
3. results;
4. why results differ;
5. what was learned.
The evaluation is therefore not merely a collection of arbitrary questions.
The dataset must be designed so that retrieval failures, grounding failures, citation failures, language effects, and chunk-boundary effects can be observed.
3. Approved Experiment
The current experiment is already accepted and MUST NOT be redesigned in this task.
Arm A
- header-aware chunking;
- maximum chunk size: 1,600 characters.
Arm B
- fixed-size chunking;
- chunk size: 1,600 characters;
- overlap: 200 characters.
Both arms MUST hold constant:
- embedding model;
- embedding settings;
- distance metric;
- top-k;
- answer prompt;
- answer model;
- evaluation question set.
Current retrieval setting:
- top-k = 5
Current embedding model:
- gemini-embedding-001
Embedding task types:
- RETRIEVAL_DOCUMENT for document chunks;
- RETRIEVAL_QUERY for questions.
Current answer model:
- gemini-3.5-flash-lite
Fallback:
- gemini-3.5-flash
Do not change these decisions.
The purpose of the evaluation dataset is to provide a fixed test set for both arms.
4. Critical Principle: Design for Measurement
Do NOT simply select 30 interesting questions.
Each evaluation question must have a clear evaluation purpose.
For every proposed case, answer internally:
- What capability is this question testing?
- What retrieval behavior should it expose?
- What source/section should be retrieved?
- What constitutes a correct answer?
- What constitutes an incorrect or incomplete answer?
- What citation evidence should be required?
- Why is this question useful for comparing the two chunking arms?
Questions that provide no meaningful evaluation signal should not be included merely to increase the count.
5. Target Dataset Size
Design for approximately 36 evaluation cases.
36 is the target, not an arbitrary hard requirement.
The final dataset must remain at least 30.
The design should allow some cases to be removed during verification without falling below 30.
Do not generate the final question wording yet.
Instead, create evaluation blueprints.
6. Language Design
The corpus is primarily English.
The system must support:
- English questions;
- Vietnamese questions.
The embedding model must therefore be evaluated for cross-lingual retrieval.
The evaluation dataset MUST contain both languages.
Each case must have:
language:
  - en
  - vi
Design approximately:
- 18 English;
- 18 Vietnamese.
Do not require exact balance if corpus coverage makes that inappropriate, but document the reason for any deviation.
7. Parallel EN/VI Cases
Design a subset of approximately 6–8 parallel question pairs.
A parallel pair asks substantially the same information need:
- once in English;
- once in Vietnamese.
Both must have the same ground truth:
- expected source_id;
- expected heading path;
- expected answer facts.
This allows the later evaluation to distinguish:
- retrieval differences caused by question language;
- answer-generation differences caused by question language.
Do not simply translate every question.
The pair must preserve the same information need and evaluation target.
Mark these cases with a shared:
parallel_group_id: PG-XXX
8. Coverage Dimensions
Design coverage across multiple dimensions.
A. Source Coverage
Avoid overfitting the dataset to only the largest or easiest documents.
Include meaningful cases from:
- small documents;
- medium documents;
- large documents;
- version-heavy documents;
- documents with repeated structures;
- documents containing potentially confusing headings.
ADR-0003 specifically identifies #13, #17, and #23 as important version-heavy documents.
The dataset must include cases that test these documents where meaningful.
Also deliberately include small documents because they can otherwise disappear from top-k retrieval behavior.
Do not force one question per source.
Source coverage must be justified by evaluation value.
B. Retrieval Difficulty
Include a mixture of:
- direct semantic retrieval;
- terminology-sensitive retrieval;
- paraphrased questions;
- questions whose answer is in a specific subsection;
- questions where several chunks from the same source may be plausible;
- questions where similar content appears in multiple source/version variants;
- questions where chunk boundaries may affect retrieval.
C. Cognitive Level
Use a mixture of:
- recall;
- explain;
- apply;
- analyze;
- compare;
- diagnose.
Do not make the dataset mostly trivial recall questions.
D. Difficulty
Use:
- easy;
- medium;
- hard.
Difficulty should reflect reasoning/retrieval burden, not obscure facts.
E. Scope
Include:
- single-source cases;
- a smaller number of carefully justified cross-document cases.
Do not combine documents merely to make a question harder.
Cross-document cases must have independently supported premises.
9. Retrieval-Specific Case Types
Explicitly design cases for the following failure modes identified by ADR-0003:
1. mixed-version answers;
2. near-duplicate chunks filling top-k;
3. fixed-size splitting code and explanation;
4. link-list or navigation noise;
5. tiny documents being represented by a single chunk;
6. large documents outranking smaller but correct documents;
7. questions whose relevant evidence is located under a specific heading;
8. repeated sections across version variants.
For each failure-mode case, record:
evaluation_target:
  failure_mode: ...
  why_it_matters: ...
  expected_behavior: ...
Do not assume in advance which arm will perform better.
The dataset must be capable of falsifying either hypothesis.
10. Ground Truth Design
Ground truth MUST be created before retrieval indexes are built.
For each evaluation blueprint define:
expected_source:
  source_id: "XX"

expected_heading_path:
  "..."

expected_answer_points:
  - ...

acceptable_answer_variations:
  - ...

citation_requirement:
  ...
The ground truth must be derived directly from the corpus.
Do not use:
- web search;
- current documentation;
- model memory;
- assumptions about current framework versions;
- general best practices.
If the corpus does not contain sufficient evidence for a proposed evaluation case:
status: blocked
and explain why.
Do not fill the gap using outside knowledge.
11. Answer Quality Design
The future evaluator must be able to judge whether the generated answer is:
- correct;
- sufficiently complete;
- grounded;
- consistent with the expected answer;
- free from unsupported claims.
For each blueprint define answer acceptance criteria.
Example:
answer_evaluation:
  required_points:
    - ...
  optional_points:
    - ...
  unacceptable_claims:
    - ...
  must_not_claim:
    - ...
Do not yet assign numerical scores unless the current evaluation specification already defines them.
If the metric is still undecided, explicitly record:
metric_decision: TBD
and propose a concrete decision for the next evaluation-spec task.
12. Citation Quality Design
The future system must cite evidence from the retrieved collection.
For each blueprint define what a valid citation must support.
At minimum:
- correct source;
- correct relevant section/heading;
- citation evidence must actually support the answer claim.
Do not require page numbers when the source format does not provide stable page semantics.
Use heading-based locations where appropriate.
Citation evaluation must distinguish:
1. correct source but wrong evidence;
2. correct evidence;
3. citation missing;
4. citation present but unsupported.
13. Latency Considerations
The dataset should contain enough variation to make latency measurements meaningful.
Do not design questions based on expected latency.
However, record metadata useful for later analysis, such as:
- question language;
- expected source;
- expected chunk count if known later;
- single/cross-document;
- difficulty;
- question length.
Latency must be measured by the evaluation runner later, not estimated during dataset design.
14. Data Schema
Design a schema for the eventual evaluation dataset.
The final case should be able to represent something like:
id:
question:
language:

parallel_group_id:

objective:

expected_answer:

expected_source:
  source_id:
  heading_path:

expected_evidence:

answer_acceptance_criteria:

retrieval_target:

difficulty:
cognitive_level:

scope:

source_ids:

concepts:

evaluation_target:
  capability:
  failure_mode:
  rationale:

generated_answer: null
generated_citations: []
retrieval_results: []
latency: null
result: null
Do not blindly copy this schema if the project already defines a better one.
Reconcile it with the current project specifications.
The most important requirement is that ground truth and generated/evaluation fields remain clearly separated.
15. Question Distribution Matrix
Before proposing individual blueprints, create a coverage matrix.
At minimum include:
- language;
- source;
- document size class;
- cognitive level;
- difficulty;
- scope;
- retrieval challenge;
- failure mode;
- parallel EN/VI status.
The matrix must demonstrate that the dataset is not accidentally dominated by:
- one source;
- one language;
- recall questions;
- easy questions;
- large documents;
- straightforward semantic matches.
Identify any coverage gaps explicitly.
16. Blueprint Format
Create one blueprint entry per planned evaluation case.
Recommended structure:
id: BP-EVAL-001

status: proposed

objective:
  ...

language:
  en

parallel_group_id:
  PG-001

scope:
  single-source

source_ids:
  - "XX"

expected_source:
  source_id: "XX"
  heading_path: "..."

concepts:
  - ...

cognitive_level:
  explain

difficulty:
  medium

retrieval_target:
  ...

evaluation_target:
  capability: ...
  failure_mode: ...
  rationale: ...

ground_truth:
  answer_points:
    - ...
  evidence_requirements:
    - ...

answer_acceptance_criteria:
  - ...

citation_acceptance_criteria:
  - ...

reason_for_inclusion:
  ...
Do not write the final natural-language question unless explicitly necessary to illustrate the blueprint.
17. Duplicate / Redundancy Control
Do not create multiple blueprints that test the same core retrieval or reasoning behavior with only superficial wording changes.
Two cases are near-duplicates if they have the same:
- information need;
- expected evidence;
- core inference;
- retrieval challenge.
A parallel EN/VI pair is not considered a duplicate because it intentionally tests language effects.
For near-duplicates, either remove one or document why both are required.
18. Insufficient-Information Cases
The RAG system must be able to say when the collection is insufficient.
Therefore consider whether the evaluation set should contain a small number of intentionally unanswerable questions.
If included, they MUST satisfy:
- the answer is genuinely unsupported by the accepted corpus;
- the expected behavior is an insufficient-information response;
- the case does not accidentally depend on outside knowledge to establish that it is unanswerable.
Clearly label these cases:
scope: corpus-insufficient
and define:
expected_behavior:
  "The assistant should explicitly state that the provided collection does not contain sufficient information."
Do not overuse these cases.
If the current evaluation specification does not yet define how insufficient-information cases are scored, mark that as a follow-up decision rather than inventing a metric silently.
19. Do Not Bias the Experiment
The dataset designer MUST NOT decide that header-aware or fixed-size chunking is better before evaluation.
Avoid wording questions specifically designed to favor one arm.
The dataset should contain a mixture of:
- cases where section boundaries are likely useful;
- cases where semantic similarity alone may be sufficient;
- cases involving long sections;
- cases involving short sections;
- cases involving repeated/versioned content;
- ordinary retrieval cases.
The purpose is to observe the difference empirically.
20. Required Output Artifacts
Produce:
1. Evaluation dataset design document:
   docs/specs/evaluation-dataset-design.md
2. Coverage matrix:
   data/evaluation/questions/coverage-matrix.yaml
3. Evaluation blueprints:
   data/evaluation/questions/blueprint.yaml
4. If useful, a corpus/evidence coverage artifact:
   data/evaluation/questions/evidence-map.yaml
5. Update or create the appropriate planning artifact for:
   EPIC-05 / EVAL-001
Do not create final evaluation questions yet.
21. Design Document Content
The design document must explain:
1. purpose of the evaluation dataset;
2. target size and why;
3. language distribution;
4. parallel EN/VI design;
5. source coverage strategy;
6. retrieval-difficulty strategy;
7. cognitive-level distribution;
8. difficulty distribution;
9. single vs cross-document strategy;
10. failure-mode coverage;
11. insufficient-information strategy;
12. ground-truth methodology;
13. answer-quality evaluation requirements;
14. citation-quality evaluation requirements;
15. latency metadata;
16. duplicate-control strategy;
17. experiment-bias controls;
18. proposed evaluation schema;
19. coverage matrix;
20. unresolved decisions / blockers.
22. Validation / Exit Gate
This task is complete only when:
- Current CLAUDE.md and project rules are consistent with the RAG project.
- Corpus count is confirmed as:
  - 24 accepted;
  - 4 excluded;
  - source 25 never existed.
- All evaluation design decisions are traceable to current project specifications or explicitly marked as proposed/TBD.
- The dataset design supports >=30 final evaluation cases.
- Approximately 36 blueprint slots are planned, allowing removal during verification.
- Both English and Vietnamese are represented.
- 6–8 parallel EN/VI groups are planned.
- Small documents are intentionally covered.
- Large/version-heavy documents, especially #13/#17/#23 where meaningful, are covered.
- Retrieval-specific failure modes are represented.
- Easy/medium/hard are represented.
- Recall/explain/apply/analyze/compare/diagnose are represented where corpus content permits.
- Single-source cases form the majority.
- Cross-document cases are limited and evidence-grounded.
- Ground truth includes source_id and heading_path.
- Ground truth is designed independently of future retrieval results.
- Citation requirements are defined per case.
- Answer acceptance criteria are defined per case.
- No final generated answers or evaluation results have been created.
- No external knowledge has been used as evaluation evidence.
- No excluded source has been used.
- Coverage matrix has no unexplained major gaps.
- Duplicate/near-duplicate risks are documented.
- Any unresolved decisions are explicitly listed rather than silently guessed.
23. Final Report to User
At the end, report:
1. files created/modified;
2. number of planned blueprint cases;
3. language distribution;
4. source coverage summary;
5. cognitive-level distribution;
6. difficulty distribution;
7. retrieval failure-mode coverage;
8. number of parallel EN/VI groups;
9. number of insufficient-information cases, if any;
10. unresolved decisions;
11. validation results;
12. the exact next recommended task.
The next task after this one should be:
EVAL-002 — Generate Evaluation Questions from the approved blueprints.
Do not proceed to EVAL-002 automatically.
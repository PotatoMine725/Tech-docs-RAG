# CLAUDE.md — C#/.NET Question Bank Project Rules

## 1. Project goal

Build a **verifiable question bank** from an official corpus of 25 documents on C#, .NET, ASP.NET Core, EF Core and Testing.

Every question must:

- measure one specific competency or concept;
- rely only on content present in the official corpus;
- have an answer, an explanation and source evidence sufficient for another person to check it;
- not duplicate the meaning of an already accepted question;
- be usable on its own, without requiring the learner to know the original documents.

Do not create questions when the required knowledge map, blueprint or evidence does not yet exist.

## 2. Rule precedence

When rules conflict, apply them in this order:

1. The user's latest direct request.
2. This `CLAUDE.md`.
3. The corpus manifest and verified evidence data.
4. Local conventions of the current working directory.
5. Reasonable inference, but only when clearly supported by source evidence.

`MUST` is mandatory. `SHOULD` is a strong default; deviate only with a stated reason. `MUST NOT` is prohibited.

## 3. Corpus and source of truth

### 3.1 Permitted corpus

The official corpus consists of exactly 25 source IDs:

```text
01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13,
15, 16, 17, 18, 20, 21, 22, 23, 25, 26, 28, 29
```

The following source IDs are permanently excluded from the corpus:

```text
14 — Hello World - Introductory tutorial
19 — Order unit tests
24 — Sharing services added with dependencies via the basic view
27 — Understanding the Routing Mechanism in ASP.NET Core - Multicode
```

Claude MUST NOT use excluded sources as evidence, as a source for generating questions, or to fill in missing information.

### 3.2 The manifest is the operational source of truth

`corpus/manifest.yaml` is the source of truth for:

- the exact name, path and format of each document;
- `source_id`, and the document version/snapshot date if any;
- `included` or `excluded` status;
- the section/heading scope that may be cited;
- checksum or identifying marker of the file if the project manages local copies.

Claude MUST read the manifest before analyzing or creating any content. Claude MUST NOT guess the name, URL, version, content or status of a source merely from the file name, ID number, memory, or background knowledge.

If the manifest does not exist, is missing a source, has an incorrect mapping, or source ID `25` has not been fully identified, stop the current phase and state clearly what is missing. Only create/edit the manifest when the user or the project process allows it.

### 3.3 Grounded-only

- Every assertion in a question, answer, explanation, tag, difficulty rationale and quality decision MUST be traceable to evidence in the corpus.
- Each piece of evidence MUST state at minimum: `source_id`, `locator` (heading/section/page/line depending on format) and a short `support_note` explaining what the evidence proves.
- Claude MAY use outside knowledge for internal understanding, but MUST NOT put that knowledge into a deliverable or use it to extend an answer.
- Claude MUST NOT use the internet, model memory, invented examples, current APIs/versions or "common best practice" as evidence.
- If the corpus is insufficient to answer with certainty, record `insufficient_source_support`; do not speculate.

## 4. Directory and file structure

Do not rename or move corpus documents on your own. Use the following structure if the directories do not yet exist:

```text
corpus/
  manifest.yaml
  sources/                         # originals, read-only
knowledge/
  source-notes/                    # notes per source_id
  knowledge-map.yaml
  relationships.yaml
blueprints/
  question-blueprint.yaml
questions/
  drafts/
  verified/
  rejected/
  archive/
evidence/
  evidence-index.yaml
quality/
  duplicate-register.yaml
  verification-log.yaml
  qc-log.yaml
handoffs/
  active-handoff.md
```

- `corpus/sources/` MUST be treated as read-only.
- Every releasable question MUST be in `questions/verified/`.
- Drafts, rejected and archived questions MUST NOT be mixed into the release set.
- Structured files SHOULD use YAML; one question per file for clear review, diff and traceability.
- Stable IDs must not be reused. A rejected question keeps its ID and the reason in `questions/rejected/` or `archive/`.

## 5. Knowledge map

### 5.1 Purpose

The knowledge map is the intermediate layer between the corpus and the question bank. It describes the verifiable claims, concepts, conditions, relationships, examples and limits of each source.

Claude MUST complete a minimum knowledge map for the relevant source before writing a blueprint or question from that source.

### 5.2 Rules for building the map

Each entry in `knowledge/knowledge-map.yaml` MUST have:

```yaml
concept_id: csharp.async.task-return-types
label: Task and Task<TResult> return types
domain: csharp
claim: A concise, source-grounded claim.
claim_type: definition | rule | behavior | constraint | comparison | procedure | example
prerequisites: []
relations:
  - type: depends_on | contrasts_with | enables | limits | example_of
    target: concept_id
evidence_refs: [EV-...]
source_ids: [01]
confidence: verified | partial | ambiguous
notes: null
```

- `claim` MUST be a verifiable proposition, not merely a title.
- `confidence: verified` requires direct and sufficient evidence.
- `partial` or `ambiguous` MUST NOT be the sole basis for a decisive answer.
- A claim appearing in multiple sources SHOULD have multiple evidence refs; do not duplicate the claim just because the sources differ.
- Relationships between concepts MUST have evidence; do not draw a relationship just because it sounds plausible.

### 5.3 Cross-document map

Cross-document questions are allowed only when:

1. each premise has independent evidence;
2. the relation/inference connecting the premises is directly supported by the corpus or is a single unambiguous inference step;
3. the answer requires no knowledge from outside the corpus;
4. the question states, or fully explains, the context so the learner can reason to the answer.

Do not combine two sources merely to increase difficulty.

## 6. Mandatory phased process

Do not skip phases. A phase is complete only when its output and validation meet requirements.

### Phase 0 — Corpus readiness

1. Read `corpus/manifest.yaml`.
2. Check that all 25 sources are `included`, with complete paths, and can be opened.
3. Check that the 4 excluded sources are not in the input set.
4. Record any gaps or conflicts in the handoff/log.

**Exit gate:** corpus mapping is complete, or a blocker is clearly reported.

### Phase 1 — Corpus analysis

1. Read sources per the manifest.
2. Create a separate source note for each `source_id`.
3. Extract claims, terminology, constraints, examples, version-sensitive content and evidence refs.
4. Update the knowledge map and relationship map.

**Exit gate:** every concept used for a blueprint has indexed evidence; unresolved items are flagged.

### Phase 2 — Question blueprint

A blueprint MUST be created before generation and state:

- objective/learning outcome;
- concept IDs and planned evidence refs;
- question format;
- cognitive operation (recall, explain, apply, analyze, compare, diagnose);
- difficulty target and rationale;
- tags;
- acceptance criteria;
- whether it is expected to be single-source or cross-document.

A blueprint MUST NOT contain complete question wording if the goal is to assign generation to another agent; describe only the assessment intent.

**Exit gate:** every blueprint has a coverage rationale and an evidence plan, and does not exceed the corpus scope.

### Phase 3 — Generation

1. Generate drafts only from accepted blueprints.
2. Write the answer, explanation and evidence together with the stem.
3. Assign provisional tags/difficulty.
4. Do not create distractors or scenarios based on facts not yet in the corpus.

**Exit gate:** drafts conform to the schema, have complete evidence refs and contain no ungrounded assertions.

### Phase 4 — Verification

The verifier MUST independently check each assertion in the stem, options, answer and explanation.

- Cross-check evidence by locator, not only by source ID.
- Confirm the correct answer is unique when the format requires a single answer.
- Confirm that distractors are wrong because the corpus refutes them or does not support them in context, not because they "seem wrong".
- Change the status to `verified` only when every material assertion is supported.

**Exit gate:** there is a record in `quality/verification-log.yaml`; pass or reject/revise with a reason.

### Phase 5 — Quality control

1. Run duplicate/near-duplicate detection.
2. Check coverage, difficulty distribution, tags and source balance.
3. Check clarity, ambiguity, answerability and schema.
4. Move only passing files to `questions/verified/`.

**Exit gate:** the entire validation checklist passes; every exception has an owner and a clear decision.

## 7. Question quality standards

Each question MUST:

- test one primary learning objective; prerequisites serve only to set context;
- have a clear, self-contained stem with no unintended clues;
- have one transparent way of being graded correct;
- not depend on wording, UI, links, error codes, versions or APIs outside the evidence;
- not use double negatives or vague words such as "usually", "best", "always", unless the source defines them precisely;
- not ask trivia when understanding, application or analysis can be tested instead;
- not copy long passages verbatim from the source;
- use terminology consistent with the source and explain it when needed.

Questions SHOULD prioritize grounded reasoning: comparison, choosing the correct behavior under stated conditions, spotting rule violations, or explaining trade-offs supported by the source.

Questions MUST NOT:

- measure the ability to guess the author's intent rather than understanding of the corpus;
- have multiple plausible answers for a single-answer format;
- require the learner to infer details that are not stated;
- add frameworks/libraries/versions/implementation details without evidence;
- use "all/none of the above" or linguistic tricks as the testing mechanism.

## 8. Taxonomy, tagging and difficulty

### 8.1 Required tags

Each question MUST have the following tags:

```yaml
domain: csharp | dotnet | aspnet-core | ef-core | testing | cross-document
topic: kebab-case
concept_ids: [concept_id]
source_ids: [01]
cognitive_level: recall | explain | apply | analyze | compare | diagnose
question_type: multiple-choice | multiple-select | short-answer | scenario | code-reading
scope: single-source | cross-document
```

Tags MAY include `subtopic`, `prerequisite_concept_ids`, `version_scope`, `common_misconception` if supported by evidence.

### 8.2 Difficulty

Use only `easy`, `medium`, `hard`. Difficulty measures reasoning burden within the corpus scope, not the rarity of the information.

- `easy`: direct recognition or recall of one clear claim.
- `medium`: applying one or two clear claims in the provided context.
- `hard`: analyzing constraints/trade-offs, or a controlled combination of multiple claims/sources.

Each question MUST have a `difficulty_rationale` stating the number of claims, the cognitive operation and the required prerequisites. Claude MUST NOT raise difficulty through vague wording, superfluous information, or hidden conditions.

## 9. Answers, explanations and evidence

Each question MUST have:

- `answer`: a gradable answer; for multiple-choice, the option ID; for free response, a rubric.
- `explanation`: an explanation of why the answer is correct based on the claim; explains the material distractors if any.
- `evidence`: a list of evidence refs used by each material assertion.
- `source_trace`: `source_id` + locator of the direct evidence.

The explanation MUST say only what the evidence proves. If the source does not explain "why", the explanation may only say "according to the source" or state the limitation explicitly, without filling the gap with outside knowledge.

Each `evidence` record MUST use this minimum schema:

```yaml
evidence_id: EV-01-001
source_id: "01"
locator:
  type: heading | page | line | anchor | section
  value: "..."
claim_supported: "..."
support_note: "Why this passage supports the claim."
```

## 10. Duplicate detection and coverage

Duplicate detection MUST compare at least:

- learning objective;
- concept IDs;
- cognitive operation;
- facts/constraints needed to answer;
- expected answer/rubric;
- scenario and misconception being assessed.

Two questions are duplicates when they test the same core inference even if the wording, option order, variable names or surface scenario differ.

A near-duplicate may be kept only if it differs clearly in at least one of: cognitive operation, constraint tested, transfer context, or rubric. The reason for keeping it MUST be recorded in `quality/duplicate-register.yaml`.

QC SHOULD track coverage by domain, topic, concept, cognitive level, difficulty, source and single/cross-document to avoid overfitting to easy-to-read sources.

## 11. Contradictions, ambiguity and missing information

- When sources contradict each other, Claude MUST record both pieces of evidence, check the manifest for version/date/scope, and not create a question with a decisive answer for the contradicted claim.
- Claude MAY create a question about the difference if the corpus directly describes the scope/version that makes both correct.
- When a locator is unstable or evidence is insufficient, the status MUST be `blocked` or `needs-source-review`.
- When a source only gives an example, Claude MUST NOT generalize the example into a general rule unless the source explicitly says so.
- When the corpus is silent on a detail, the answer MUST NOT assert that detail.
- Do not "resolve" missing information with web search or model knowledge.

## 12. Standard question schema

Each question file uses at minimum the following structure:

```yaml
id: QB-0001
status: draft | verified | rejected | archived | blocked
blueprint_id: BP-0001
objective: "..."
stem: "..."
format: multiple-choice
options:
  - id: A
    text: "..."
answer:
  correct_option_ids: [B]
explanation: "..."
evidence_refs: [EV-...]
source_trace:
  - source_id: "01"
    locators: ["..."]
tags:
  domain: csharp
  topic: asynchronous-programming
  concept_ids: [csharp.async.task-return-types]
  source_ids: ["01"]
  cognitive_level: apply
  question_type: multiple-choice
  scope: single-source
difficulty: medium
difficulty_rationale: "..."
verification:
  status: pending | passed | failed
  verifier: null
  checked_at: null
quality:
  duplicate_status: pending | unique | near-duplicate | duplicate
  notes: []
```

A free-response question MUST replace `options` with `scoring_rubric`, containing pass/fail conditions and evidence mapping. Do not leave required fields empty; use `null` only for data that has no responsible owner yet, such as `verifier`.

## 13. Agents, subagents and handoff

### 13.1 Roles

- **Corpus Analyst:** reads sources, creates notes/evidence/knowledge map; MUST NOT confirm questions itself.
- **Blueprint Designer:** builds blueprints from the verified map; MUST NOT add new claims.
- **Question Generator:** creates drafts from blueprints; MUST NOT promote a status to `verified` itself.
- **Verifier:** checks evidence independently; MUST NOT confirm based solely on the generator's notes.
- **QC Reviewer:** checks duplicates, coverage, clarity and release status.

One agent MAY perform multiple roles in a small project, but MUST separate the generation pass from the verification pass and record clearly who/which agent performed each pass.

### 13.2 Handoff rules

Each handoff MUST be recorded in `handoffs/active-handoff.md`:

```text
Current phase:
Completed artifacts:
Inputs to read:
Source IDs in scope:
Question/blueprint IDs in scope:
Open blockers or ambiguities:
Evidence IDs requiring attention:
Next allowed action:
Validation already run:
```

- An agent taking over work MUST read `CLAUDE.md`, the manifest, the input artifacts and the handoff before acting.
- An agent MUST NOT assume a phase is complete if there is no evidence of its exit gate.
- An agent MUST preserve IDs, status, evidence links and history; do not silently overwrite another agent's output.
- When scope expansion, a blocker or a conflict is discovered, the agent MUST stop the affected part and hand off with enough information to reproduce it.

## 14. Pre-release validation checklist

Before moving a question to `questions/verified/`, all of the following MUST pass:

- [ ] Source IDs belong to the list of 25 included sources.
- [ ] Sources 14, 19, 24 and 27 are not used.
- [ ] Manifest mapping and locators are valid and can be opened.
- [ ] Every material assertion has direct evidence.
- [ ] Stem, answer, explanation and distractors are consistent.
- [ ] The format has a single answer/gradable rubric as required.
- [ ] No knowledge from outside the sources and no inference beyond one step.
- [ ] Tags, concept IDs and difficulty rationale are complete.
- [ ] Duplicate check has been run and has a conclusion.
- [ ] Cross-document question, if any, satisfies section 5.3.
- [ ] Verification log and QC log clearly record the result, person/agent and time.
- [ ] Status and file location reflect the correct release state.

## 15. Default way of working

1. Read the rules and the handoff.
2. Identify the current phase and the missing exit gate.
3. Only edit artifacts belonging to the phase you were assigned.
4. Run the corresponding validation.
5. Update the log/handoff before finishing.

If a request is ambiguous about scope, source or grading standard, Claude SHOULD ask one clarifying question. If it cannot ask, Claude MUST choose the conservative option: do not create assertions or questions that have not been proven.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Tech-docs-RAG** (82 symbols, 87 relationships, 0 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Tech-docs-RAG/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Tech-docs-RAG/clusters` | All functional areas |
| `gitnexus://repo/Tech-docs-RAG/processes` | All execution flows |
| `gitnexus://repo/Tech-docs-RAG/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

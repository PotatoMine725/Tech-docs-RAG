# EVAL-001 blueprint review (independent)

Date: 2026-09-24. Reviewer: independent agent (did not write the dataset). Status: findings only. Nothing in the blueprint files was changed.
Reviewed: `data/evaluation/questions/blueprint.yaml` (36 eval + 6 dev blueprints), `data/evaluation/questions/evidence-map.yaml`, and `docs/specs/evaluation-dataset-design.md`. Every item below was checked against `corpus/sources/*.md` only.

Two terms are used throughout:
- **Source hit@5**: the expected *document* appears among the 5 retrieved chunks. For cross-document cases, *all* expected documents must appear.
- **Section hit@5**: a retrieved chunk overlaps the expected *section*, measured by character span.

A hit on an `acceptable_alternate_sources` entry counts for both metrics (`evaluation-spec.md`). So a missing alternate in **another document** can make source hit@5 wrong, and a missing alternate in **another section of the same document** can make section hit@5 wrong.

## 1. Scope and method

**What I read**
- The task prompt `docs/prompt-log/claude-code/EVAL-001 — Design Evaluation Dataset.md` and its addendum `agents/prompts/01-EVAL-001-design-dataset.md`.
- The project rules (`CLAUDE.md`), `docs/specs/evaluation-dataset-design.md`, and the metric rules in `docs/specs/evaluation-spec.md`.
- The data files: all of `blueprint.yaml` and all of `evidence-map.yaml`.
- Every corpus section named in an `expected_sources`, `acceptable_alternate_sources` or `evidence` entry, read in full. For #13, #17 and #23 I also read every variant of the cited section.
- Whole documents: #18, #22 and #29, which are tiny.

Nothing under `corpus/excluded/` was opened, listed or searched.

**Tools.** I wrote two read-only helper scripts in the session scratchpad. Both read only `corpus/sources/*.md` and `data/processed/documents/section-inventory.jsonl`.
- `cs.py grep <regex>` searches case-insensitively and prints each hit with its source, line, heading path and variant.
- `cs.py count <regex>...` prints hit counts per document.
- `cs.py sec <id> <heading>` prints one section's full text.
- `cs.py heads <id>` lists a document's sections.
- `mech.py` runs four checks:
  1. every expected, alternate and evidence heading path exists in the inventory;
  2. every quote occurs, after whitespace normalization, inside its cited section, and inside the right variant when `evidence_variant` is set;
  3. the two members of each parallel group match field by field;
  4. dev and eval cases do not share sections.

**Mechanical results**
- All heading paths exist.
- All quotes are found inside their cited sections and are at most 300 characters.
- Every required point has at least one quote attached.
- In each parallel group, the ground truth, sources and acceptance criteria are identical.
- No dev case uses a section that an eval case uses.

A passing mechanical check proves only that the quotes are verbatim. It does not prove that the ground truth is complete or correct. The findings below come from reading the text.

**Searches run.** All patterns are case-insensitive regular expressions over the 24 documents. They are grouped by the check they served.

- **Check 1, alternate sources:**
  - `against the database|already exist in`, `EF Core`, `Entity Framework`, `SingleAsync`, `FindAsync|FirstOrDefault|SingleOrDefault`
  - `developer exception page|UseDeveloperExceptionPage`
  - `CPU-bound|I/O-bound|Task\.Run`
  - `input validation|validate the inputs|disambiguate`, `validat` (in #23)
  - `\bAct\b|multiple asserts?|single act`
  - `ValidatableType`, `source generator`, `file-local`, `silently`
  - `middleware` (in #10), `scoped service|behave like a singleton|captive|from a singleton`
  - `ContinueWith|readab|call stack|faulted`
  - `reference type|same object|copies the data|value type`, `\bstring\b` and `default|null` (in #04, #07, #20, #26)
  - `binds|precedence|IsNotLowerCase`
  - `list pattern|slice|\[\.\.`
  - `unchecked|0xFF_FF_FF_FF|first of the following`
  - `file-based|dotnet run|shebang|C# 14`
  - `UseStatusCodePages|re-execut|address bar|302`, and `Does not alter the status code|Returns the original status code` (in #13)
  - `suppress|metrics|emitted`, `IExceptionHandler|TryHandleAsync` (outside #13)
  - `shadow|xunit.runner.json|Assembly.Location`
  - `ShortCircuit|short-circuit|robots.txt|favicon`
  - `NU1202|out of support|5\.0\.17|net5`
  - `InvalidModelStateResponseFactory|ValidationProblemDetails|ConfigureApiBehaviorOptions|model validation`
  - `assembly language|performance and size|compete`, `perform|fast|speed`
  - `IsPrime_|naming|Returns?[A-Z]`
  - `shorter than|singleton` (in #10, #11, #13, #17)
- **Check 3, absence proofs** (beyond the listed `zero_hit_terms`):
  - ABS-001: `AsNoTracking`, `no-tracking`, `change track`, `changetracker`, `AsTracking`, `QueryTrackingBehavior`, `tracking`, `\btrack`, `read-only quer`, `identity resolution`, `detach`, `untracked`.
  - ABS-002: `rate limit`, `ratelimit`, `RateLimiter`, `RequireRateLimiting`, `AddRateLimiter`, `throttl`, `\b429\b`, `too many requests`, `(?<!de)limiter`, `requests per`, `per minute`, `fixed window`, `sliding window`, `token bucket`, `quota`, `\blimit`.
  - ABS-003: `ValidateScopes`, `ValidateOnBuild`, `validate scopes`, `root provider`, `root scope`, `root container`, `CreateScope`, `IServiceScopeFactory`, `from a singleton`, `captive`, `ServiceProviderOptions`, `UseDefaultServiceProvider`.
  - ABS-004: `Moq`, `NSubstitute`, `FakeItEasy`, `Times\.Once`, `Verify\(`, `\bverif`, `Mock<`, `\.Setup\(`, `\.Returns\(`, `mocking framework`, `isolation framework`, `called (exactly )?once`, `call count`, `was called`, `\bmock`, `\bstub`, `\bfake`.
  - ABS-005: `refresh token`, `RefreshToken`, `\brefresh`, `ValidateLifetime`, `expir`, `access token`.
  - ABS-006: `API versioning`, `ApiVersion`, `Asp.Versioning`, `api-version`, `\bversioning`, `\bv1\b`, `\bv2\b`, `\{version`, `MapGroup`, `version.*route`.

## 2. Findings (most severe first)

Severity:
- **HIGH:** the ground truth is wrong, or a metric would be scored wrongly.
- **MEDIUM:** the ground truth is incomplete or ambiguous.
- **LOW:** a label or wording problem.

Checks: 1 = missing alternate source; 2 = correctness beyond the quote (other variants and sections); 3 = absence proof; 4 = a point that needs an unstated inference or has no supporting quote; 5 = a `must_not_claim` item that is actually true; 6 = dev/eval overlap; 7 = parallel groups; 8 = labels.

| # | Case ID | Check | Severity | Evidence (file + heading + exact quote) | Proposed fix |
|---|---|---|---|---|---|
| 1 | BP-EVAL-023 | 2, 8 | HIGH | The case says only variant 1 holds the .NET 10 statement. Its `why_it_matters` reads "Variants 2-3 describe IExceptionHandler without the .NET 10 change", and the citation rule says "a chunk from variants 2-3 = correct_source_wrong_evidence". This is false. #13 "Handle errors in ASP.NET Core > IExceptionHandler", **variant 2** (line 1267) and **variant 3** (line 2243) both say: "In .NET 8 and .NET 9, the exception handling middleware logs the exception and emits metrics even when an `IExceptionHandler` implementation returns `true` from `TryHandleAsync`." Lines 1279 and 2255 say: "Starting in .NET 10, diagnostics are suppressed by default for handled exceptions. See [SuppressDiagnosticsCallback](...)". The single-copy subsection "IExceptionHandler > SuppressDiagnosticsCallback" also states P2: "To revert to the .NET 8 and 9 behavior where diagnostics are always emitted for handled exceptions, set the callback to always return `false`". The evidence-map distractor note ("Variants 2 and 3 lack the .NET 10 diagnostics statement (only variant 1 has it)") and the design doc §10 ("023 ... only variant 1") repeat the error. | Drop `evidence_variant: 1`. Accept every variant, and the SuppressDiagnosticsCallback subsection, for P1 and P2. Remove the variant-2/3 penalty from the citation criteria. Fix the evidence-map note and design §10. Relabel `failure_mode`: all variants give the same answer, so this is not a mixed-version case. To keep a truly single-copy target, aim P3 at the SuppressDiagnosticsCallback subsection (`SuppressDiagnosticsCallback = context => false`), which exists once. |
| 2 | BP-EVAL-031 | 1, 2 | HIGH | Premise 2 ("string is a reference type") is also stated in #20 "A tour of the C# language > Familiar C# features": "value types like `int`, `double`, `char`, reference types like `string`, arrays, and other collections." This is not listed as an alternate. The cross-document metric needs *all* expected sources, so a system that retrieves #04 + #20 would be scored as a miss. Also, #04 "Built-in types and literals > `default` expressions" alone answers the "what holds it" part: "string? defaultString = default;   // null". | Add #20 "Familiar C# features" to `acceptable_alternate_sources` as an alternate for the #26 premise. Note in the blueprint that #04 alone gives the value, so only the "why" needs a second document. Schema gap: an alternate entry doesn't say *which* expected source it replaces, so the "all expected sources" rule can't use it. Add a field such as `replaces_source_id` for cross-document cases. |
| 3 | BP-EVAL-036 (ABS-004) | 3, 5 | HIGH | `must_not_claim` forbids "Any Moq API (setup/verify methods, call-count options) presented as from the documents". But #03 "Unit testing best practices for .NET > Best practices > Handle stub static references with seams" contains "var dateTimeProviderStub = new Mock<IDateTimeProvider>();" and "dateTimeProviderStub.Setup(dtp => dtp.DayOfWeek()).Returns(DayOfWeek.Monday);". A correct partial answer ("the documents show creating a `Mock<T>` and `.Setup(...).Returns(...)`, but not how to verify call counts") would be marked a hallucination. ABS-004's `closest_corpus_text` ("no library") is wrong, and its term list never tried `Mock<` or `.Setup(`, which each have 2 hits in #03. #03 "Unit testing terminology" also describes "common .NET usage where a test double can both return values and verify interactions" and shows a hand-written mock checked with `Assert.True(mockOrder.Validated);`. Verification of call counts is still absent: `Verify\(`, `Times\.Once` and `call count` all have 0 hits. | Narrow `must_not_claim` to call-verification and call-count APIs (Verify, Times.*). Add `Mock<` and `.Setup(` to ABS-004 as allowed hits with their location, and correct `closest_corpus_text`. Add the "seams" section to `near_miss_sources`. State that a refusal may mention what #03 shows (creating a mock, stubbing a return value) as long as it says verifying a call once isn't covered. |
| 4 | BP-EVAL-030 | 1, 4 | HIGH | `question_notes` says "Name the test method in the question". If the question contains `IsPrime_ValuesLessThan2_ReturnFalse`, then #03 "Follow test naming standards" alone answers it ("The name of your test should consist of three parts: ..."). The only #28 evidence is the method signature, which the question would already contain. The "all expected sources" metric would then count a miss whenever #28 is not retrieved, even for a fully correct answer. This breaks the design rule "neither document alone answers". | Word the question so that #28 must be retrieved (e.g. "the [Theory] test the xUnit tutorial writes for values below 2", without the name), or reclassify the case as single-source #03 with #28 optional. |
| 5 | BP-EVAL-005 / 006 (PG-003) | 1 | MEDIUM | #02 "Asynchronous programming scenarios > Explore the asynchronous programming model" (the H2 section) states the same split: "- **I/O-bound code** starts an operation represented by a `Task` or `Task<T>` object within the `async` method." and "- **CPU-bound code** starts an operation on a background thread with the [Task.Run](...) method." It is not in `acceptable_alternate_sources`; only the two example H3s are. | Add it as a partial alternate (supports P2, and P1 in part). |
| 6 | BP-EVAL-013 / 014 (PG-007) | 1 | MEDIUM | P2 is also stated in #10 "Dependency injection in ASP.NET Core > Lifetime and registration options": "Middleware can also resolve and use the same services. Scoped and transient services must be resolved in the `InvokeAsync` method." P3's sentence also appears in #11 "Factory-based middleware activation in ASP.NET Core > Additional resources" (variant 1 at line 157, variant 2 at line 322): "[IMiddleware](...) is activated per client request (connection), so scoped services can be injected into the middleware's constructor." #11 "IMiddleware" shows both patterns in code. Only #11's H1 section is listed. Case 017 already treats "Additional resources" as valid. | Add #10 "Lifetime and registration options" (P2), #11 "Additional resources" (P3) and #11 "IMiddleware" (P2/P3 by example) as partial alternates. |
| 7 | BP-EVAL-017 | 1 | MEDIUM | #10 "Dependency injection in ASP.NET Core > Service lifetimes" answers P1 and P2 of this compare case in another document: "Inject the service into the middleware's `Invoke` or `InvokeAsync` method." and "Use [factory-based middleware](...). Middleware registered using this approach is activated per client request (connection), which allows scoped services to be injected into the middleware's constructor." It is not listed. This also means 017 overlaps PG-007 on the same #10 sentences. | Add #10 "Service lifetimes" as a partial alternate (P1, P2). Record the overlap with PG-007 in the duplicate-control section of the design doc. |
| 8 | BP-EVAL-016 | 1 | MEDIUM | Another document supports the rule. #07 "C# classes" (H1): "Assigning a class variable to another variable copies the reference, so both variables point to the same object." #07 "C# classes > Create objects": "This reference-sharing behavior is one distinction between classes and <structs>. With structs, assignment copies the data." #20 "Familiar C# features": "reference types like `string`, arrays, and other collections". `acceptable_alternate_sources` is empty. | Add #07 "Create objects" (or its H1) and #20 "Familiar C# features" as partial alternates. #07's section differs from the dev case's "Static classes", so this does not leak. Also update the design doc §5 sentence saying the evaluation set "stays free of" #06/#07 sections. |
| 9 | BP-EVAL-016, BP-EVAL-031 | 4 | MEDIUM | Required points go beyond the planned question. 016's P2 (required: "Value types ... copy their data on assignment") is not asked by the planned question ("ask for list1.Count and why"). 031's P2 (required: "For value types default is a value, e.g. 0 ... false for bool") is not asked by "what `string s = default;` holds and why". A complete, focused answer would be labelled `partially_correct`. | Make these points optional, or add the contrast to the question (e.g. also ask about a struct, or about `int`). |
| 10 | BP-EVAL-009 / 010 (PG-005) | 4 | MEDIUM | P2 says "after one Assert fails, the rest of the test is treated as failing". The corpus says something different: #03 "... > Avoid multiple Act tasks": "In most unit testing frameworks, after an Assert task fails in a unit test, all subsequent tests are automatically considered as failing." The cited quote ("Multiple Act tasks need to be individually asserted, and you can't guarantee that all Assert tasks execute.") does not contain that sentence. A faithful answer could be judged inconsistent with P2. | Quote the "In most unit testing frameworks ..." sentence as evidence for P2 and reword P2 to follow it. Alternatively, keep only the "can't guarantee all Asserts execute" part as required. |
| 11 | BP-EVAL-022 | 2 | MEDIUM | P2's qualifier ("the original code is returned unless the new pipeline changes it") appears only in variants 1–4 of "UseStatusCodePages > UseStatusCodePagesWithReExecute": "The new pipeline execution may alter the response's status code...". Variants 5–6 (lines 4165, 4683) and the older H2 "UseStatusCodePagesWithReExecute" (line 5075, a listed alternate) say without qualification: "- Returns the original status code to the client." So this is also a mixed-version case, and a citation of a variant-5/6 or H2 chunk cannot support the qualifier. | Make the qualifier an optional point, keeping "does not alter / returns the original status code" as required. Record the version difference in `why_it_matters`. |
| 12 | BP-EVAL-027 | 1, 4 | MEDIUM | Two gaps. First, the same document has a missing alternate section: #12 "... > Additional error handling features > Key differences for controllers" says "**Automatic model validation**: Controllers automatically validate model state and return `400 Bad Request` responses for validation failures" and "**Custom error responses**: Override `InvalidModelStateResponseFactory` for custom validation error formatting". Second, there is another corpus-supported way to customize: #12 "Problem details > Implement `ProblemDetailsFactory`" says ProblemDetailsFactory produces "ValidationProblemDetails" and "is used for: ... Validation failure error responses". An answer that proposes it would be grounded but would miss required P2. | Add "Key differences for controllers" as an alternate (P1 partly, P2). Accept a custom `ProblemDetailsFactory` as an `acceptable_variation` for the "how to customize" part, or make P2 accept either route. |
| 13 | BP-EVAL-018 | 1 | MEDIUM | The listed alternate "... > Logical patterns" (the parent H2) contains none of P1–P3. It only defines not/and/or with examples, so a hit on it inflates section hit@5. The closer text is "... > Parenthesized pattern": "Typically, you use parentheses to emphasize or change the precedence in [logical patterns](#logical-patterns)". | Remove the parent H2 alternate, or mark it as giving no evidence. Add "Parenthesized pattern" as a partial alternate (supports P3 in part). |
| 14 | BP-EVAL-003 / 004 (PG-002) | 4 | LOW | The only P3 quote comes from an alternate (older) section, "Developer Exception Page". The expected section itself states P3: #13 "Developer exception page" variant 1: "Don't enable the Developer Exception Page **unless the app is running in the `Development` environment**. Don't share detailed exception information publicly when the app runs in production." | Add the variant-1 warning as the P3 quote, so the expected section supports every required point. |
| 15 | BP-EVAL-025 | 2, 4 | LOW | P2 ("the rest of the pipeline ... doesn't run") leaves out the corpus caveat in the same section: "The `ShortCircuit` and `MapShortCircuit` methods do not affect middleware placed before `UseRouting`. Trying to use these methods with endpoints that also have `[Authorize]` or `[RequireCors]` metadata will cause requests to fail with an `InvalidOperationException`." | Reword P2 as "middleware after routing is skipped". Add the caveat as an optional point. |
| 16 | BP-EVAL-024 | 4 | LOW | P1 says shadow copying "breaks tests that load files relative to Assembly.Location". The corpus is softer: #17 "Disable shadow copying": "If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying." The P1 quote covers only the first sentence, not Assembly.Location. | Reword P1 ("can cause problems for tests that load files relative to Assembly.Location") and quote that sentence. |
| 17 | BP-EVAL-029 | 1, 4 | LOW | #23 "Routing in ASP.NET Core > Routing with special characters" (3 copies) shows another corpus way to load one entity by id: "var todoItem = await _context.TodoItems.FindAsync(id);". P2 requires `SingleAsync` only. | Accept FindAsync as an `acceptable_variation`, or tie the question clearly to the #22 Blogs example. |
| 18 | BP-EVAL-019 | 8 | LOW | The `acceptable_variation` "range/slice `..`" mixes up two constructs. The corpus uses "range" for a different one: #20 "A tour of the C# language > Distinctive C# features": "The `..` in a range expression denotes the range of elements to include." The same section calls `..` a "*spread element*". Neither is listed as a distractor. | Replace the variation with "slice pattern `..`". Add #20 "Distinctive C# features" to evidence-map distractors for 019. |
| 19 | BP-EVAL-028 | 1 | LOW | #20 "A tour of the C# language" (H1): "C# is a cross-platform general purpose language that makes developers productive while writing highly performant code." This can pull an answer toward "yes, C# aims to be fast" and is not recorded as a distractor. | Add it to evidence-map distractors for 028. Optionally add "saying C# is highly performant is fine if the C/assembly design goal is stated". |
| 20 | BP-EVAL-016 | 8 | LOW | `question_notes` says to include the page's list1/list2 snippet. Copied as-is, the snippet contains the answer: #26 "Value types and reference types": `Console.WriteLine($"list1 count: {list1.Count}"); // 4 — same object`. | Tell EVAL-002 to remove the `// 4 — same object` comment from the question. |
| 21 | BP-EVAL-016, BP-EVAL-018 | 8 | LOW | Both are labelled `fixed_size_code_split` because "a fixed-size cut may separate" code from prose. But both sections are longer than Arm A's 1,600-character limit (inventory: #26 "Value types and reference types" is 1,847 chars; #21 "Precedence and order of checking" is 1,842 chars), so **both** arms must split them. The label reads as if only Arm B is at risk. | State in `why_it_matters` that both arms split these sections, and that the case measures *where* each arm cuts. |
| 22 | BP-EVAL-001 / 002 (PG-001) | 7, 8 | LOW | The parallel pair's `retrieval_challenges` differ by more than language. 001 has `[tiny_document, direct_semantic]`; 002 has `[tiny_document, cross_lingual]`, so `direct_semantic` was dropped. Every other group only adds `cross_lingual`. | Use `[tiny_document, direct_semantic, cross_lingual]` for 002. |
| 23 | BP-DEV-002, BP-DEV-003 (dev) | 1 | LOW | DEV-002's citation criterion accepts "#16 'Native sized integers'". But the #16 sentence with the size is in "Integral numeric types (C# reference) > Characteristics of the integral types": "Native-sized integers are 32-bit integers when running in a 32-bit process, or 64-bit integers when running in a 64-bit process. Use them for interop scenarios, low-level libraries, and to optimize performance in scenarios where integer math is used extensively." Its last clause is a use not in DEV-002's P2. Neither section is in `acceptable_alternate_sources`. For DEV-003, #06 "C# keywords" (H1) also defines the term: "Contextual keywords have special meaning only in a limited program context and can be used as identifiers outside that context." | Dev-only: list these alternates so prompt tuning isn't confused by "wrong source" labels. |
| 24 | BP-DEV-006 (ABS-006, dev) | 3 | LOW | Partial adjacency: #23 "Routing in ASP.NET Core > Route groups": "The [MapGroup](...) extension method helps organize groups of endpoints with a common prefix". A model may suggest `MapGroup("/v1")` as versioning. The corpus never mentions versioning (`\bversioning`, `\bv1\b` and `api-version` have 0 hits), so a refusal is still correct. | Decide and note whether suggesting route-group prefixes counts as `hallucination` for this dev case. |

## 3. Cases checked with no finding

- **BP-EVAL-007, 008 (PG-004).** The warning appears in all 3 "Route constraints" variants and in "Route constraint reference". There is no contradicting text in #23.
- **BP-EVAL-011, 012 (PG-006).** The whole of #29 was read. The points and `must_not_claim` items are correct: Severity is Warning, and both public and internal are allowed.
- **BP-EVAL-015.** The cited section and its parent were read. The parent partly supports P1, so it is a fair alternate. `ContinueWith` has no other source.
- **BP-EVAL-020.** #04 "Integer literals" lacks the no-suffix rule and `unchecked`, as the case says.
- **BP-EVAL-021.** The "File-based apps" facts are verified. #08 and #20's "Next steps" are links only.
- **BP-EVAL-026.** The NU1202 message, the ".NET 5 is out of support" reply and the 5.0.17 reply were verified. It is a community thread.
- **BP-EVAL-032.** "The lifetime of an `IExceptionHandler` instance is singleton" appears in all 3 variants. The #10 rule and the scoped default are verified. Neither document alone answers.
- **BP-EVAL-033 (ABS-001), 034 (ABS-002), 035 (ABS-003).** The extended synonym searches found no content:
  - ABS-001: `tracking`, `change track`, `detach` and the others have 0 hits. `\btrack` hits only #02 "tracks various operations" (compiler state machine). A bare `track` also hits 4 #13 lines, all the `datatracker.ietf.org` URL.
  - ABS-002: `(?<!de)limiter`, `throttl`, `429`, `too many requests` and the others have 0 hits.
  - ABS-003: `ValidateOnBuild`, `ValidateScopes`, `root scope` and the others have 0 hits. "scope validation" occurs only in #10's link-only section.
  - No partial answer is possible, so refusal is the right expected behaviour.
- **BP-DEV-001, BP-DEV-004, BP-DEV-005 (ABS-005).** Quotes and points are verified. ABS-005 holds: #15 has only `ValidateLifetime = true` and `Expires = DateTime.UtcNow.AddDays(7)`, and there are no refresh tokens.
- **Check 6, dev/eval overlap.** No dev case shares a section or a tested fact with an eval case (script plus reading). Two adjacencies are not leakage:
  - BP-DEV-005 is a refusal near #15, while BP-EVAL-026 answers from #15. These are different facts.
  - BP-DEV-006 and BP-EVAL-034 are both "ASP.NET Core feature not in the corpus" refusals near #23. This is the intended use of a dev set.
- **Check 7, parallel groups.** For PG-001 to PG-007, the ground truth, sources, alternates and acceptance criteria are identical through YAML anchors (script-verified). The only difference is finding 22.

## 4. Could not check, and why

- **Final question wording** does not exist yet (EVAL-002). Findings 4, 9, 17 and 20 depend on how the questions are worded, and so does whether the EN/VI pairs truly ask the same thing.
- **Chunk boundaries.** No chunks or indexes exist yet (EPIC-02). Claims about how each arm splits a section, and whether ADR-0003 D1 dedup removes the 5 identical copies in 024, can't be verified yet.
- **Section boundaries** come from `section-inventory.jsonl` line ranges. I did not re-derive the inventory. I spot-checked it against the raw files for the sections used above.
- **Not reviewed:** `coverage-matrix.yaml` and `tests/unit/test_evaluation_blueprints.py`. They were outside the priority list. I did not run pytest, to stay read-only; it writes cache files.
- **Spec gap (not a blueprint error).** `acceptable_alternate_sources` entries have no field linking an alternate to the expected source it replaces. For cross-document cases scored with "all expected sources", alternates can't be applied until such a field exists (see finding 2).
- **Outside knowledge.** Any library name for the `Mock<T>`/`Setup` API in #03 is not used as evidence. Finding 3 rests only on the literal text `Mock<` / `.Setup(` in the corpus against the blueprint's own wording "setup/verify methods".

---

## 5. Response from the dataset author (added after the review; sections 1–4 above are the reviewer's text, unchanged)

Date: 2026-09-24. Author: Claude Opus 5.5 (the session that wrote EVAL-001). Before any change, every corpus quote in the findings table was checked with a script against `corpus/sources/` and the section inventory. All of them exist, in the sections named. The parent H2 in finding 13 was read in full (no binding-order text).

| # | Decision | Change made | Reason |
|---|---|---|---|
| 1 | Partly accepted | 023: `evidence_variant` removed. Retrieval target, citation criterion and `why_it_matters` rewritten. The variant-2/3 sentence "Starting in .NET 10, diagnostics are suppressed by default for handled exceptions." added for P1, and the SuppressDiagnosticsCallback "revert to the .NET 8 and 9 behavior" sentence added for P2/P3. `variant_specific_evidence` removed from `retrieval_challenges`. The wrong distractor entry was removed from the evidence map, and design §10/§12/§19/§20 were corrected. | The finding is right: all 3 variants state both behaviors. **`failure_mode` stays `mixed_version`.** ADR-0003 names "mixed-version answers", and this answer still depends on the version (.NET 8/9 vs .NET 10). What was wrong was only the claim that one variant holds the answer. |
| 2 | Accepted | 031: #20 "Familiar C# features" added as an alternate with the new field `stands_in_for: "26"`. The field is defined in design §18 and proposed in `evaluation-spec.md` for the "all expected sources" rule. A new test requires it on every alternate in a cross-document case. `why_it_matters` now says #04 alone gives the value, not the reason. | The schema gap is real: without the field, the "all" rule could not use any alternate. |
| 3 | Accepted | 036: `must_not_claim` narrowed to call-verification / call-count APIs (e.g. Verify, Times.Once). ABS-004 now lists `Mock<` and `.Setup(` as allowed hits, confined to #03 "Handle stub static references with seams" (test-checked: every hit is in that section). "call count" was added to the zero-hit terms, and `closest_corpus_text` was corrected. The refusal may now mention what the seams example shows. | A refusal is still the right expected behavior: `Verify(`, `Times.Once` and `call count` have 0 hits. But a correct partial remark about `Mock<T>`/`Setup` must not be scored as a hallucination. |
| 4 | Accepted (first option) | 030: `question_notes` now say not to give the full test name, and to ask about the test the tutorial adds for values below 2. Checked: `IsPrime_ValuesLessThan2_ReturnFalse` appears only in #28. | The case stays cross-document. The other option (making it single-source) would change the owner's OD-4 mix. |
| 5 | Accepted | 005/006: #02 "Explore the asynchronous programming model" added as a partial alternate. | Quote verified. |
| 6 | Accepted | 013/014: #11 "Additional resources", #11 "IMiddleware" and #10 "Lifetime and registration options" added as partial alternates. Citation criterion updated. | Quotes verified. |
| 7 | Accepted | 017: #10 "Service lifetimes" added as a partial alternate. The overlap with PG-007 is recorded in design §16. | Quotes verified. |
| 8 | Accepted | 016: #07 "C# classes", #07 "Create objects" and #20 "Familiar C# features" added as partial alternates. Design §5 sentence corrected. | #07's sections differ from the dev case's "Static classes", so nothing leaks. |
| 9 | Accepted | 016 P2 and 031 P2 are now optional. | The planned questions don't ask for the value-type contrast. |
| 10 | Accepted (both options) | 009/010: P2 is now only "Multiple Acts need to be asserted individually, and you can't guarantee that all Asserts execute." (required). The "In most unit testing frameworks …" sentence is an optional P4 with its own quote. | The answer point now follows the corpus text. |
| 11 | Accepted | 022: the "unless the new pipeline changes it" qualifier moved from required P2 to optional P5, with a quote from variants 1–4. `why_it_matters` records the version difference. | Checked: variants 5–6 and the older H2 say only "Returns the original status code to the client." |
| 12 | Accepted | 027: "Key differences for controllers" added as an alternate. A custom ProblemDetailsFactory is an accepted variation for the "how to customize" part. Citation criterion widened. | Both routes are in #12. |
| 13 | Accepted | 018: the parent H2 "Logical patterns" is removed as an alternate. "Parenthesized pattern" is added as a partial alternate (P3/P4). | Read in full: the H2 has no binding-order statement. |
| 14 | Accepted | 003/004: the "Don't enable the Developer Exception Page unless … Development …" sentence is the new P3 quote from the expected section. | It is in variants 1 and 2 of the 5. |
| 15 | Accepted | 025: P2 now says "middleware that would run after routing is skipped". The UseRouting/[Authorize]/[RequireCors] caveat is an optional P4 with a quote. | |
| 16 | Accepted | 024: P1 reworded to the corpus's softer claim ("may run into issues"). The quote now includes the Assembly.Location sentence. | |
| 17 | Accepted | 029: FindAsync by key is an accepted variation for P2. | |
| 18 | Accepted | 019: the variation now accepts "slice" and says "range" is a different construct. #20 "Distinctive C# features" added to the evidence-map distractors. | |
| 19 | Accepted | #20 H1 added to the evidence-map distractors for 028. | |
| 20 | Accepted | 016 `question_notes`: remove the output comments (e.g. `// 4 — same object`) from the snippet. | |
| 21 | Accepted | 016/018 `why_it_matters`: both arms split these sections. Arm A splits at paragraph/sentence boundaries and keeps code blocks whole (ADR-0003 D4); Arm B cuts at fixed positions. Label kept. | ADR-0003 D4 states the Arm A rule. |
| 22 | Accepted | 002: `direct_semantic` added. Matrix regenerated (`share_direct_semantic` 0.062 → 0.094). | |
| 23 | Accepted | DEV-002: #16 "Characteristics of the integral types" and #16 "Native sized integers" added as alternates. DEV-003: #06 H1 added. Criteria updated. | The #16 heading "Native sized integers" exists; the 32/64-bit sentence is in "Characteristics …". |
| 24 | Decided | DEV-006: presenting MapGroup or a `/v1` prefix as the documents' way to version an API = hallucination (`must_not_claim`). Mentioning route groups while saying versioning isn't covered is acceptable. | Dev case; the corpus never mentions versioning. |

**Found during triage, not in the review.** 32 prose values in `blueprint.yaml` were cut off by YAML: an unquoted value ends at " #", so "The introduction of #22 (…)" was read as "The introduction of". Separately, 024's variation `{ "shadowCopy": false }` was read as a mapping. The existing tests only check quotes, headings and counts, and the review's findings do not depend on these fields, so neither side saw it. It was fixed in commit `9e0ab15`, and two tests now fail on it: one against inline comments, one requiring prose fields to be non-empty strings. The new test also caught one of the new `question_notes` above before commit.

**Ground truth that changed (for the owner to re-check):** 009/010 (P2 narrowed, P4 added), 016 (P2 optional), 022 (P2 qualifier optional), 023 (any variant; P2/P3 quotes), 024 (P1), 025 (P2), 031 (P2 optional), 036 (`must_not_claim`). No case was added, dropped or re-scoped. The OD-4 mix (32 + 4, 18/18, 7 groups) is unchanged and test-checked.

# EVAL-001 owner re-check of changed ground truth

**For the owner to fill.** EVAL-002 MUST NOT start until every `owner verdict:` line below is filled (`agents/prompts/02-EVAL-002-write-and-freeze.md`, entry condition).

- **Baseline ("old")**: `blueprint.yaml` at `9e0ab15`. That is after the YAML parsing fix and before the independent-review fixes (`ce04909`) and owner decisions D1–D3 (`831d5a0`), so it is the version you reviewed.
- **"New"**: `blueprint.yaml` at `629b931` (current). Produced by a script that compares the parsed YAML of both versions. The only change to every case is the new `slot: S1/S2` field from owner decision D1; it is not repeated below.
- **Why each case changed**: `docs/reviews/evaluation/EVAL-001-blueprint-review.md` §2 (finding #) and §5 (response).
- Quotes are verbatim from the corpus (test-checked in `tests/unit/test_evaluation_blueprints.py`).
- Suggested verdicts: `ok` / `change: <what>` / `drop` (dropping an answerable case: at most 2, evaluation-spec § Dataset mix).

---

## BP-EVAL-009 (EN) / BP-EVAL-010 (VI, same group) — one Act per unit test
Source: #03 "Unit testing best practices for .NET > Best practices > Avoid multiple Act tasks". Review finding #10.
- **What changed:** P2 narrowed to what the corpus says. The "later tests count as failing" part became an optional P4 with its own quote.
- **Old P2 (required):** "With multiple Acts you can't guarantee that all Asserts execute: after one Assert fails, the rest of the test is treated as failing, which can make working functionality look broken."
- **New P2 (required):** "Multiple Acts need to be asserted individually, and you can't guarantee that all Asserts execute."
- **New P4 (optional):** "In most unit testing frameworks, after an Assert fails, all subsequent tests are considered failing, so working functionality can look broken."
- **Supporting quotes:** P2 "Multiple Act tasks need to be individually asserted, and you can't guarantee that all Assert tasks execute." · P4 "In most unit testing frameworks, after an Assert task fails in a unit test, all subsequent tests are automatically considered as failing."

owner verdict (009 and 010): 

## BP-EVAL-016 (VI) — assigning a list variable to another, then changing it
Source: #26 "The C# type system > Value types and reference types". Review findings #8, #9, #20.
- **What changed:** P2 made optional. Three partial alternate sources added (all slot S1). The code snippet in `question_notes` no longer includes the output comments.
- **Old P2 (required) → New P2 (optional):** "Value types (structs such as the Coords record struct, enums, built-in numeric types) copy their data on assignment, so changing one variable doesn't affect the other."
- **Unchanged P1 (required):** "list1.Count is 4: List<int> is a reference type, so list1 and list2 point to the same object and the Add through list2 is visible through list1."
- **Alternates added:** #07 "C# classes"; #07 "C# classes > Create objects"; #20 "A tour of the C# language > Familiar C# features". Each gives partial support for P1, so retrieving one of them counts as a source hit.
- **Supporting quotes (unchanged):** P1 "**Reference types** hold a reference to an object on the managed heap. When you assign a reference type to a new variable, both variables point to the same object." · P2 "**Value types** hold their data directly. When you assign a value type to a new variable, the runtime copies the data."

owner verdict: 

## BP-EVAL-022 (VI) — UseStatusCodePagesWithRedirects vs UseStatusCodePagesWithReExecute
Source: #13 "Handle errors in ASP.NET Core > UseStatusCodePages > …WithRedirects" (slot S1) and "…WithReExecute" (slot S2). Review finding #11.
- **What changed:** the "unless the new pipeline changes it" qualifier moved from required P2 to a new optional P5, because only variants 1–4 say it. The case now has **two evidence slots**, so both methods must be in the top 5 for a retrieval hit (D1).
- **Old P2 (required):** "… does not alter the status code, so the original code is returned unless the new pipeline changes it."
- **New P2 (required):** "UseStatusCodePagesWithReExecute re-executes the request pipeline with an alternate path to generate the response body and does not alter the status code, so the original code is returned."
- **New P5 (optional):** "Variants 1-4 add that the re-executed pipeline may change the status code; if it doesn't, the original code is sent."
- **Supporting quotes:** P2 "Does not alter the status code before or after re-executing the pipeline." · P5 "The new pipeline execution may alter the response's status code, as the new pipeline has full control of the status code. If the new pipeline does not alter the status code, the original status code will be sent to the client."

owner verdict: 

## BP-EVAL-023 (EN) — are logs/metrics emitted for exceptions an IExceptionHandler handles?
Source: #13 "Handle errors in ASP.NET Core > IExceptionHandler" (any variant) or "… > SuppressDiagnosticsCallback". Review finding #1 (partly accepted).
- **What changed:** the old version said only variant 1 holds the answer. All 3 variants state both behaviors, so `evidence_variant: 1` was removed and any variant now counts. Two quotes were added (variants 2–3 wording, and the SuppressDiagnosticsCallback subsection). The answer points themselves are unchanged. `failure_mode` stays `mixed_version`.
- **Old citation rule:** "P1/P2 must cite a chunk from variant 1 of 'IExceptionHandler'; a chunk from variants 2-3 = correct_source_wrong_evidence."
- **New citation rule:** "Any variant of 'IExceptionHandler' or the 'SuppressDiagnosticsCallback' subsection can support P1-P3; the cited chunk must contain the version statement it is cited for."
- **Answer points (unchanged):** P1 .NET 10 suppresses diagnostics for handled exceptions by default · P2 .NET 8 and 9 always emitted them · P3 changeable with SuppressDiagnosticsCallback.
- **Added quotes:** "Starting in .NET 10, diagnostics are suppressed by default for handled exceptions." (P1) · "To revert to the .NET 8 and 9 behavior where diagnostics are always emitted for handled exceptions, set the callback to always return `false`:" (P2, P3).

owner verdict: 

## BP-EVAL-024 (VI) — shadow copying in xUnit integration tests
Source: #17 "Integration tests in ASP.NET Core > Disable shadow copying". Review finding #16.
- **What changed:** P1 softened to the corpus's own claim ("may run into issues" instead of "breaks"). The quote was extended to include the Assembly.Location sentence.
- **Old P1 (required):** "Shadow copying runs the tests in a different directory than the output directory, which breaks tests that load files relative to Assembly.Location."
- **New P1 (required):** "Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may then run into issues, and disabling shadow copying is the fix."
- **Supporting quote:** "Shadow copying causes the tests to execute in a different directory than the output directory. If your tests rely on loading files relative to `Assembly.Location` and you encounter issues, you might have to disable shadow copying."

owner verdict: 

## BP-EVAL-025 (EN) — short-circuit robots.txt and favicon.ico
Source: #23 "Routing in ASP.NET Core > Short-circuit middleware after routing". Review finding #15.
- **What changed:** P2 now says that only middleware *after routing* is skipped. The UseRouting/[Authorize]/[RequireCors] caveat was added as an optional P4.
- **Old P2 (required):** "… end the request, so the rest of the pipeline (e.g. authentication or CORS middleware) doesn't run."
- **New P2 (required):** "Short-circuiting makes routing invoke the endpoint logic immediately and end the request, so middleware that would run after routing (e.g. authentication or CORS) is skipped."
- **New P4 (optional):** "Caveat: it doesn't affect middleware placed before UseRouting, and endpoints with [Authorize] or [RequireCors] metadata fail with InvalidOperationException."
- **Supporting quotes:** P2 "Use the [ShortCircuit](…) extension method to cause routing to invoke the endpoint logic immediately and then end the request." · P4 "The `ShortCircuit` and `MapShortCircuit` methods do not affect middleware placed before `UseRouting`. Trying to use these methods with endpoints that also have `[Authorize]` or `[RequireCors]` metadata will cause requests to fail with an `InvalidOperationException`."

owner verdict: 

## BP-EVAL-031 (EN, cross-document) — default value of a string, from the kind of type string is
Sources: slot S1 #04 "Built-in types and literals > `default` expressions"; slot S2 #26 "The C# type system > Value types and reference types" **or** #20 "A tour of the C# language > Familiar C# features" (new alternate). Review findings #2, #9; owner decision D1.
- **What changed:** P2 made optional. #20 added as an alternate for the #26 slot. The citation rule is now one citation per slot.
- **Old P2 (required) → New P2 (optional):** "For value types default is a value, e.g. 0 for numeric types and false for bool."
- **Unchanged P1 (required):** "`default` produces null for a string, because string is a reference type and default is null for reference types."
- **Old citation rule:** "One citation per premise; each from the matching document."
- **New citation rule:** "One citation per slot: S1 from #04 '`default` expressions'; S2 from #26 'Value types and reference types' or #20 'Familiar C# features'."
- **Supporting quotes (unchanged):** #04 (S1, P1 + P2) "The `default` expression produces the default value for a type: `0` for numeric types, `false` for `bool`, and `null` for reference types:" · #26 (S2, P1) "Classes, arrays, delegates, and strings are reference types."
- **#20 alternate, note (quote):** "reference types like `string`, arrays, and other collections".

owner verdict: 

## BP-EVAL-036 (VI, not in the documents) — verify with Moq that a method was called exactly once
Expected: refusal (corpus-insufficient). Review finding #3.
- **What changed:** `must_not_claim` narrowed. #03 does show `Mock<T>` and `.Setup(...).Returns(...)`, so mentioning that is now allowed, as long as the answer says call verification isn't covered.
- **Old must_not_claim:** "Any Moq API (setup/verify methods, call-count options) presented as from the documents."
- **New must_not_claim:** "Any call-verification or call-count API (e.g. Verify, Times.Once) presented as from the documents."
- **Old acceptable variation:** "The refusal may explain what #03 says about mocks in general."
- **New acceptable variation:** "The refusal may say what #03 does show (creating a `Mock<T>` and stubbing a return value with `.Setup(...).Returns(...)` in 'Handle stub static references with seams'), as long as it says that verifying how often a method was called is not covered."
- **Old citation rule:** "Citing #03 terminology as evidence for a Moq API = hallucination." → **New:** "Citing #03 (terminology or the seams example) as evidence for a call-verification API = hallucination."
- **Absence proof:** `Verify(`, `Times.Once` and `call count` have 0 hits in the 24 accepted documents (`evidence-map.yaml` ABS-004).
- **Scoring note:** under the REORIENT-001 C1 decision, a refusal that mentions `Mock<T>`/`.Setup` as related content goes to the judge's refusal check.

owner verdict: 

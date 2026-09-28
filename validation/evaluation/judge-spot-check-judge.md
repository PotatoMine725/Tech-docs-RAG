# Judge spot-check: the judge's verdicts (key)

Open only after grading `judge-spot-check.md`. One entry per S-id: the record it came from and the judge's
verdict as written in `judgements.jsonl` (prompt `judge_v1`). The label is the §3 mapping of that verdict.

## S01

- Case: `Q-EVAL-017`, arm A, run `20260928-eval-A-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **partially_correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Conventional middleware receives the scoped service as a parameter of InvokeAsync.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request.",
   "covered": "yes"
  },
  {
   "id": "P3",
   "point": "The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.",
   "covered": "partial"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 3,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 5,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 4,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer covers P1 and P2 fully, while P3 is only partially addressed as the answer omits how UseMiddleware checks and resolves via IMiddlewareFactory."
}
```

## S02

- Case: `Q-EVAL-035`, arm B, run `20260928-eval-B-full-491f137`
- Check: refusal; judge model `gemini-3.5-flash-lite`; label: **correct_refusal**

```json
{
 "presents_related_as_answer": false,
 "reason": "The response and note correctly state that the documents do not contain enough information to answer the question about scope validation."
}
```

## S03

- Case: `Q-EVAL-012`, arm A, run `20260928-eval-A-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **partially_correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "The validation source generator emits code in a separate file, so it can't access a type (or one of its containing types) that is private or file-local.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "In that case the generator silently skips validation for the type (diagnostic ASP0033).",
   "covered": "partial"
  },
  {
   "id": "P3",
   "point": "Fix: make the attributed type and each of its containing types public or internal.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer successfully covers the core cause and the fix, though it misses the specific detail about silently skipping validation for P2. All citations are accurate and there are no contradictions."
}
```

## S04

- Case: `Q-EVAL-035`, arm A, run `20260928-eval-A-full-491f137`
- Check: refusal; judge model `gemini-3.5-flash-lite`; label: **correct_refusal**

```json
{
 "presents_related_as_answer": false,
 "reason": "The response explicitly states that the documents do not contain enough information to answer the question and correctly notes that the documents only point to external resources without explaining what scope validation checks or when it is enabled."
}
```

## S05

- Case: `Q-EVAL-024`, arm A, run `20260928-eval-A-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "With xUnit, add an xunit.runner.json file in the test project directory containing \"shadowCopy\": false.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer correctly identifies the cause as shadow copying and provides the exact xUnit configuration to fix it, fully supported by the cited passage."
}
```

## S06

- Case: `Q-EVAL-025`, arm A, run `20260928-eval-A-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Use `app.MapShortCircuit(404, \"robots.txt\", \"favicon.ico\");` to short-circuit several URL prefixes at once.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "Short-circuiting makes routing invoke the endpoint logic immediately and end the request, so middleware that would run after routing (e.g. authentication or CORS) is skipped.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer accurately covers both required points and provides valid citations matching the ground truth and cited passages."
}
```

## S07

- Case: `Q-EVAL-024`, arm B, run `20260928-eval-B-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Shadow copying runs the tests in a different directory than the output directory; tests that load files relative to Assembly.Location may run into issues, and you might have to disable shadow copying.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "With xUnit, add an xunit.runner.json file in the test project directory containing \"shadowCopy\": false.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 3,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 4,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 5,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer fully addresses both required points correctly and is completely supported by the cited passages."
}
```

## S08

- Case: `Q-EVAL-022`, arm B, run `20260928-eval-B-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "UseStatusCodePagesWithRedirects sends a 302 Found to the client and redirects it to the error endpoint (which typically returns 200); the original status code is not preserved.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "UseStatusCodePagesWithReExecute re-executes the request pipeline with an alternate path to generate the response body and does not alter the status code, so the original code is returned.",
   "covered": "yes"
  },
  {
   "id": "P3",
   "point": "With redirects the browser address bar shows the error endpoint; with re-execute it shows the originally requested URL.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 4,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 5,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 3,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer accurately covers all required points and correctly cites the provided passages without any unsupported claims or contradictions."
}
```

## S09

- Case: `Q-EVAL-020`, arm B, run `20260928-eval-B-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **partially_correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Without a suffix, the literal's type is the first of int, uint, long, ulong that can represent the value.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "So `0xFF_FF_FF_FF` is the uint value 4,294,967,295, not int -1: literals are interpreted as positive values.",
   "covered": "partial"
  },
  {
   "id": "P3",
   "point": "To get -1 as int, cast in an unchecked context: `unchecked((int)0xFF_FF_FF_FF)`.",
   "covered": "yes"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer successfully covers the rule, the uint value of the literal, and the unchecked cast method. It only partially covers P2 because it omits explicitly mentioning that it is not int -1."
}
```

## S10

- Case: `Q-EVAL-017`, arm B, run `20260928-eval-B-full-491f137`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **partially_correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "Conventional middleware receives the scoped service (SampleDbContext in the example) as a parameter of InvokeAsync.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "Factory-activated middleware implements IMiddleware and receives the scoped service through its constructor, because IMiddleware is activated per client request (connection).",
   "covered": "yes"
  },
  {
   "id": "P3",
   "point": "The factory-activated middleware is registered as a scoped or transient service in the service container; UseMiddleware sees that the type implements IMiddleware and resolves it with the registered IMiddlewareFactory.",
   "covered": "partial"
  }
 ],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [
  {
   "marker": 2,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 1,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 4,
   "supports_attached_claim": "yes"
  },
  {
   "marker": 3,
   "supports_attached_claim": "yes"
  }
 ],
 "reason": "The answer correctly covers points 1 and 2, and partially covers point 3 by mentioning the service container registration but omitting the UseMiddleware factory resolution detail."
}
```

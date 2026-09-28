# Judge spot-check: the judge's verdicts (key)

Run `20260927-dev-A-full-05680f9`. Open only after grading the blind sheet. One entry per S-id: the record it came from and the judge's verdict as written in `judgements.jsonl` (prompt `judge_v1`). The label is the §3 mapping of that verdict.

## S01

- Case: `Q-DEV-001`, arm A, run `20260927-dev-A-full-05680f9`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "A static class can't be instantiated and contains only static members.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "A static class is implicitly sealed, so you can't derive from it.",
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
 "reason": "The answer correctly covers all required points and is fully supported by the ground truth and cited passages."
}
```

---

## S02

- Case: `Q-DEV-002`, arm A, run `20260927-dev-A-full-05680f9`
- Check: answer; judge model `gemini-3.5-flash-lite`; label: **correct**

```json
{
 "required_points": [
  {
   "id": "P1",
   "point": "nint and nuint are integers whose size matches the platform's native pointer size: 32 bits on a 32-bit platform, 64 bits on a 64-bit platform.",
   "covered": "yes"
  },
  {
   "id": "P2",
   "point": "They are for interop and low-level memory work; otherwise use int or long.",
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
 "reason": "The answer accurately covers all required points regarding the definition and usage of nint and nuint. All claims are fully supported by the cited passages."
}
```

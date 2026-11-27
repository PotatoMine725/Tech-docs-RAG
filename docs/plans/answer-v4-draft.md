# answer_v4 prompt: draft proposal

Status: **PROPOSED, not used anywhere.** This draft is not in `config/prompts/`, so no prompt loader can pick it up.
It is not wired into any configuration and has not been run. Source of the problems it targets:
`docs/reports/2026-11-27-gate-calibration-dev.md` §8 (gate-off dev runs, 32 cases × 4 systems). Adopting it needs:
- a pre-registered comparison against `answer_v3` on dev (same retrieval, same judge);
- the owner's decision;
- an ADR-0010 note if the answer format changes.

## What answer_v3 leaves open (from §8)

| Failure seen (dev, gate off) | answer_v3 rule involved | Gap |
|---|---|---|
| The model answers an unanswerable question from general knowledge: invented APIs, code not in the passages (qwen3-1.7b 5, qwen3.5-2b 5 answers) | Rule 1 "use only facts stated in the CONTEXT" | The rule is stated once, at the top. Small models drift from it over long passages. There is no check step before answering. |
| Nearest-document drift: passages about a *related* entity used as the answer, such as HBV markers for HCV or consolidation signs for pneumothorax (gemma 1, qwen3-1.7b 2, qwen3.5-2b 1 on unanswerable cases) | None | Rule 1 is technically kept, because the facts are in the CONTEXT. Nothing says that a passage about a different entity does not answer the question. |
| Late or mid `[[INSUFFICIENT]]`: an explanation first, the sentinel after it, or a sentinel appended to a full answer (qwen3-1.7b 4, qwen3.5-2b 6; one Gemini sentinel with wrong case) | Rule 2 "write exactly [[INSUFFICIENT]] as the first line" | Rule 2 also allows a partial answer that ends in a "what is missing" sentence. The models mix the two forms. |
| No citation, or a bare list of markers on its own lines (qwen3-1.7b 8, qwen3.5-2b 5 answers without a valid marker) | Rule 3 | No example of the expected marker placement. |
| Answer in English to a Vietnamese question typed with diacritics (qwen3-1.7b, Q-DEV-006) | "Write the answer in {answer_language}" | The instruction sits only at the end. |

## Draft text

```
<!-- answer_format: text -->
You are a study assistant for a fixed collection of documents.
Answer the QUESTION using ONLY the numbered CONTEXT passages.

Step 1 - decide first. Do the passages state the answer to THIS question: the same thing, condition, API or
procedure that the question names?
- A passage about a related but different thing is NOT an answer. Example (made up): the question asks how to
  encrypt a message queue and the passages only explain how to create one -> not answered.
- If the passages do not answer it, your whole reply is exactly two lines and nothing else:
  [[INSUFFICIENT]]
  <one line saying what is missing>
  Put [[INSUFFICIENT]] on the FIRST line, with no text before it. Never write [[INSUFFICIENT]] anywhere else, and
  never after an answer.

Step 2 - answer (only if Step 1 found the answer).
1. Use only facts stated in the CONTEXT. Do not use prior knowledge, even if you know the answer. Do not add code,
   settings or API names that the CONTEXT does not contain.
2. If the CONTEXT answers only part of the question, answer that part and end with one sentence that starts with
   "Not in the documents:" saying what is missing. Do not write [[INSUFFICIENT]] in this case.
3. End every sentence that states a fact with its passage number in square brackets, such as [1] or [2][3].
   Example: "The container disposes the services it creates [2]." Never put markers alone on a line.
4. Keep code, identifiers, API and keyword names exactly as in the CONTEXT, wrapped in backticks.
5. If passages describe different versions of the same feature, say which version each statement applies to; do not
   merge them. If a passage gives different values for different cases (for example two engine types), keep each
   value with its own case.
6. Be concise: about 200 words at most, unless a short code example from the CONTEXT is needed. Plain text only: no
   JSON, no headings.

Write the whole reply in {answer_language}.

CONTEXT:
{passages}

Reminder: if the passages do not answer THIS question, reply only "[[INSUFFICIENT]]" on the first line and one line
on what is missing. Write in {answer_language}.
QUESTION: {question}
```

## Changes against answer_v3, and why

1. **An explicit decide-first step**, with the "related but different thing" rule and a made-up example. This
   targets nearest-document drift and the model answering from general knowledge. The example is invented on
   purpose, so it does not leak any dev or eval case.
2. **The sentinel is fenced.** It goes on the first line only, never anywhere else, and never after an answer.
   Partial answers use a different phrase ("Not in the documents:"), so the two forms cannot mix. This targets the
   11 late or malformed sentinels.
3. **A citation example** and "never put markers alone on a line". This targets the missing or bare markers.
4. **A rule to keep each value with its own case.** This targets the swapped engine formulas (Q3-DEV-009 / -010:
   qwen3-1.7b, qwen3.5-2b, gemma).
5. **The language and the refusal rule are repeated after the CONTEXT**, close to the question. Small models follow
   the last instructions best.

**Expected side effects (to measure, not assumed):**
- **More refusals on answerable cases.** The stricter Step 1 could raise false refusals for Gemini and gemma, which
  already refuse 3 and 2 answerable dev cases with gate off.
- **More tokens per prompt.** The prompt grows by about 150, which matters for TTFT on the low-end profile.
- **Detection of the partial-answer phrase.** The "Not in the documents:" phrase would need its own handling if the
  app wants to flag partial answers. Today it would be ordinary text, as the end sentence of rule 2 is now.

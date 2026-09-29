# Demo video script (≤ 5 minutes)

Recorded by the owner. Total runtime target: 4:50 (290 s), inside the 5-minute submission limit. Every number and
quote below is copied from a committed report — nothing here is invented for the video. Section timestamps are
targets, not hard cuts; keep them ±10 s.

## 0:00–0:20 — Problem (20 s)

**Say:** "Generic chat with an LLM answers from its training data, with no way to check whether the answer is
actually supported by a source. For a fixed set of technical documents, that's not good enough — an answer needs to
trace back to a passage, and the system needs to admit when the documents don't cover the question."

**Show:** title card or the README's "Problem" section on screen.

## 0:20–0:40 — Dataset (20 s)

**Say:** "The corpus is 24 technical documentation pages — C#, .NET testing, ASP.NET Core, EF Core — about 1.2
million characters. 28 documents originally; 4 were excluded as index pages with no real content, and one ID never
existed. Questions can be asked in English or Vietnamese; the documents themselves stay English."

**Show:** `README.md` § Dataset (the counts table and topic table).

## 0:40–2:10 — Live GUI: EN, VI, refusal (90 s)

Launch: `python -m knowledge_assistant.presentation.desktop.app`.

1. **English, answerable (~30 s).** Ask: *"What is a static class in C#, and can another class inherit from it?"*
   Show the answer, the citation (document + heading path, not a page number), and point out the excerpt is the
   original English text.
2. **Vietnamese, answerable (~30 s).** Ask: *"nint và nuint trong C# là gì, và khi nào thì nên dùng chúng thay cho
   int hay long?"* Show the answer is generated in Vietnamese while the citation excerpts stay in English.
3. **Out-of-corpus refusal (~30 s).** Ask: *"How do I issue refresh tokens and use them to renew JWT access tokens
   in ASP.NET Core?"* Show the "insufficient information" state — no citations, no hallucinated answer. Say: "This
   was refused by the retrieval-score gate before the model was ever called — real output, live smoke check
   `validation/generation/smoke-2026-09-29.md`."

## 2:10–2:50 — Pipeline diagram (40 s)

**Show:** `README.md` § Architecture & workflow (the Mermaid diagram), or the rendered GitHub view of it.

**Say:** "Documents are parsed, normalized, and chunked two different ways — that's the experiment, more in a
moment. Chunks are embedded with Gemini's embedding model and stored in ChromaDB, one collection per chunking
strategy. A question is embedded the same way, the top matches are retrieved, and a score gate decides whether the
match is good enough to even call the LLM. If it is, Gemini answers only from the retrieved passages and cites them;
if the model itself decides the passages don't answer the question, it says so instead of guessing."

## 2:50–3:40 — Evaluation results (50 s)

**Show:** `docs/reports/epics/EPIC-05-evaluation.md` § Summary, scrolled to show the tables.

**Say:** "36 questions — 32 answerable, 4 designed to be unanswerable — scored on both chunking arms, 72 records
total. Lenient answer accuracy is 90.5%, strict is 73%; the gap is mostly partially-correct answers, not wrong ones.
Every answered question cited the right source 100% of the time, and the right section 97.7% of the time. All 8
unanswerable cases were correctly refused with zero hallucinations."

**Show:** `docs/reports/epics/EPIC-05-evaluation.md` § "Judge spot-check agreement (owner)".

**Say:** "Because the same model family both answers and judges, that's a self-preference risk — so I hand-graded 10
judge verdicts blind before seeing the judge's own labels. Rule-based agreement was 8 out of 10, Cohen's kappa 0.688;
holistic agreement was 9 out of 10. Small sample, but it's a real check, not a claim."

## 3:40–4:30 — Experiment + one failure case (50 s)

**Show:** `docs/reports/epics/EPIC-06-experiment.md` § "One-line answer" and the code-fence row of the results table.

**Say:** "The experiment compares header-aware chunking against fixed-size chunking on the same 36 questions with
paired statistics. The headline: no statistically reliable difference in final answer quality at this sample size.
But the chunks themselves are measurably different — fixed-size chunking cuts a code block out of its explanation in
45% of chunks, against 3% for header-aware chunking, and costs about 494 more prompt tokens per answer."

**Show:** the Q-EVAL-001 worked case (EPIC-06 § 4, or the README's "Worked failure case" box).

**Say:** "Here's a concrete failure this project would have missed without the paired analysis. Both chunking
strategies retrieve the exact same section, with the exact same evidence, for the same question. Header-aware
chunking's version of that chunk scores 0.6779 against a 0.686 gate threshold — just below — so it's refused.
Fixed-size chunking's version of the same chunk includes a bit more surrounding text and scores 0.6908 — just above
— so it's answered correctly. The retrieval quality is equal; the gate threshold, tuned on the other chunker's dev
scores, is what decided this case."

## 4:30–4:50 — Limitations & next steps (20 s)

**Say:** "The evaluation set is 36 questions — small enough that one or two cases flipping moves the headline number
by a couple of points. The gate threshold was tuned on only 6 dev questions and on one chunking arm. And the judge
grading the answers is the same model family as the model giving them, mitigated but not removed by that manual
spot-check. Full limitations and a 7-more-days plan are in the README and `AI_WORKLOG.md`."

**Show:** README § Limitations (a quick scroll).

---

## Shot list — screenshots/recordings the owner must capture before editing

1. GUI window, English question answered, citation panel visible (document name + heading path + excerpt, not a
   page number).
2. Same GUI window, Vietnamese question answered (answer text in Vietnamese, citation excerpt still in English).
3. Same GUI window, out-of-corpus question, showing the "insufficient information" state clearly (no answer text
   presented as fact, no citations).
4. The Mermaid pipeline diagram rendered (GitHub's README view renders it automatically; a local Markdown preview
   with Mermaid support also works).
5. `docs/reports/epics/EPIC-05-evaluation.md`, scrolled to the Summary bullets and the "Judge spot-check agreement"
   table.
6. `docs/reports/epics/EPIC-06-experiment.md`, scrolled to the "One-line answer" quote and the code-fence-percentage
   row of the results table.
7. The Q-EVAL-001 worked-case paragraph (either from EPIC-06 § 4 or the README's "Worked failure case" callout).
8. README § Limitations, full scroll (doesn't need narration over every line — just show it exists and is honest).

## Files this script draws from (every number traceable)

- `README.md` (Problem, Dataset, Architecture, Evaluation summary, Experiment summary, Limitations)
- `docs/reports/epics/EPIC-05-evaluation.md` (evaluation numbers, judge spot-check)
- `docs/reports/epics/EPIC-06-experiment.md` (experiment numbers, Q-EVAL-001 worked case)
- `validation/generation/smoke-2026-09-29.md` (the three live GUI questions, run and verified at QC-001)

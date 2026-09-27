# GUI manual check (GUI-001, real app + fake errors)

Owner checklist. Status of each row: **unverified until you tick it.** The agent ran the same three questions through
the real view-model and window *offscreen* (see the report), but nobody has looked at the real window yet: that is you.

Setup, from the repo root, PowerShell (one BLAS thread avoids the OpenBLAS memory error seen at process start):

```
$env:OPENBLAS_NUM_THREADS = "1"
$env:PYTHONPATH = "src"   # the package is not pip-installed in .venv; pytest gets this from pyproject.toml
.venv\Scripts\python.exe -m knowledge_assistant.presentation.desktop.app          # real app (Part A)
.venv\Scripts\python.exe -m knowledge_assistant.presentation.desktop.app --fake   # offline demo (Part B)
```

The real app reads `GEMINI_API_KEY` from `.env`, answers with `gemini-3.5-flash-lite` and falls back to
`gemini-3.5-flash` when it fails (`ALLOW_FALLBACK` is forced on in the app). The fake window's title says
"(fake data)".

**Budget for Part A: 2 LLM requests (rows A1, A2) + at most 3 embedding requests (0 if the vectors are cached).**
Row A3 must send 0 LLM requests. Use only these dev questions; do not type eval questions.

## Part A: real app (dev questions only)

| # | Do | Expect | OK |
|---|----|--------|----|
| A1 | Arm A. Ask `What is a static class in C#, and can another class inherit from it?` | Busy bar, then an English answer with `[n]` markers; citations list (document — heading path); status line "Total latency … s · model: gemini-3.5-flash-lite"; window stays movable while waiting | [ ] |
| A2 | Click a citation | Detail shows the **English** excerpt and the source URL (link) | [ ] |
| A3 | Ask `nint và nuint trong C# là gì, và khi nào thì nên dùng chúng thay cho int hay long?` | Answer in **Vietnamese**; citation excerpts still English | [ ] |
| A4 | Ask `How do I issue refresh tokens and use them to renew JWT access tokens in ASP.NET Core?` | Amber "Not enough information in the documents" with the message from `config/messages.json`; no citations; status "model: none (no model call)" (0 LLM requests: the retrieval gate refused) | [ ] |
| A5 | After A1 or A3, click "Copy answer", paste into Notepad | Pasted text equals the answer | [ ] |
| A6 | Optional, 0 LLM requests: close the app, start it with `$env:GEMINI_API_KEY = ""`, ask anything | Red banner "Could not get an answer" with "Something went wrong: GEMINI_API_KEY is not set"; window stays usable | [ ] |
| A7 | Optional, spends 1 more LLM request: switch to Arm B and ask the A1 question | Answer or refusal from Arm B; no crash | [ ] |

## Part B: `--fake` (offline, no Gemini, no Chroma)

Trigger words in the question choose the scenario (case-insensitive); Vietnamese is detected from diacritics.

| # | Do | Expect | OK |
|---|----|--------|----|
| B1 | `What is dependency injection?` | English answer, 2 citations, status "… · model: fake-model" | [ ] |
| B2 | `insufficient topic` and `chủ đề insufficient` | Amber banner, the **real** refusal text (EN / VI) from `config/messages.json`, "Not covered: …", no citations, Copy disabled | [ ] |
| B3 | `related topic` | Amber state plus list "Related content (not an answer)"; row ends "(related, not an answer)" | [ ] |
| B4 | `quota` | Red banner "Quota used up", readable message, no raw `429` text | [ ] |
| B5 | `503 please` | Red banner "Model service unavailable" | [ ] |
| B6 | `noindex` | Red banner "Search index not found" | [ ] |
| B7 | `what is dependency injection, fallback please` | Status line ends "model: fake-fallback-model (fallback)" | [ ] |
| B8 | `slow question`, then drag/resize/minimise during the 3 s | Window keeps repainting; busy bar animates; input disabled | [ ] |
| B9 | Empty box + Enter | Nothing happens | [ ] |

## Screenshot moments (for the README / video)

The agent could not take them: the offscreen Qt platform has no fonts (every glyph is a box), so no screenshot is
committed. Take them on your desktop (Win+Shift+S), real app unless noted:

1. **Grounded answer** (A1 after clicking a citation): answer with `[1]`, the citation list, the English excerpt + URL
   in the detail box, the model/latency line. Shows "grounded + cited".
2. **Refusal** (A4): the amber banner with no citations and "model: none (no model call)". Shows "insufficient information" handled without a model call.
3. **Vietnamese question** (A3) or **error state** (`--fake`, B4): pick one: language handling, or a readable error.

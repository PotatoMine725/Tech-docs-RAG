# GUI manual check (GUI-001-pre, fake use case)

Owner checklist. Nothing here calls Gemini or ChromaDB. Status of each row: **unverified until you tick it.**

Launch (from the repo/worktree root):

```
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m knowledge_assistant.presentation.desktop.app --fake
```

Trigger words in the question choose the fake scenario (case-insensitive). Vietnamese is detected from diacritics.

| # | Do | Expect | OK |
|---|----|--------|----|
| 1 | Type `What is dependency injection?` + Enter | Thin busy bar ~0.5 s, then an English answer with `[1] [2]`; 2 citations; status line "Total latency 1.1 s · model: fake-model"; "Copy answer" enabled | [ ] |
| 2 | Click citation `[1]` | Detail box shows the English excerpt and a source URL (example.invalid link) | [ ] |
| 3 | Type `Dependency injection là gì?` + Enter | Vietnamese answer; citation excerpt still in English | [ ] |
| 4 | Type `insufficient topic` | Amber banner "Not enough information in the documents", italic message, "Not covered: …"; NO citations list; Copy disabled | [ ] |
| 5 | Type `related topic` | Same amber state, plus list titled "Related content (not an answer)"; the row ends with "(related, not an answer)"; clicking it shows "Related, not an answer." | [ ] |
| 6 | Type `chủ đề insufficient` and `related ở đâu?` | Same as 4 / 5 with the Vietnamese message | [ ] |
| 7 | Type `quota` (only that word) | Red banner "Quota used up"; message below "The Gemini quota is used up…", no raw `429`/`RESOURCE_EXHAUSTED` text | [ ] |
| 8 | Type `503 please`, then `noindex` (each alone, no `quota` in the text) | Banner "Model service unavailable" + "…temporarily unavailable (503)…"; banner "Search index not found" + "…index was not found…" | [ ] |
| 9 | Type `slow question`; while the 3 s delay runs, drag/resize/minimise the window | Window keeps moving and repainting; busy bar animates; Ask/input/arm disabled; answer appears after ~3 s | [ ] |
| 10 | After an answer, click "Copy answer", paste into Notepad | Pasted text equals the answer text | [ ] |
| 11 | Switch selector to Arm B, ask any answerable question | Answer begins `[Arm B]` (fake echoes the arm); back on Arm A → `[Arm A]` | [ ] |
| 12 | Press Enter on an empty box | Nothing happens | [ ] |

Screenshots of rows 1, 4/5, 7 are welcome for the README/video.

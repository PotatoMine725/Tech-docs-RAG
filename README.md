# Knowledge Assistant

A desktop assistant that answers questions about a fixed collection of technical documents. Every answer must be **grounded** in those documents, with **citations**; when the documents don't contain the answer, it says so. The project also measures how well it works (≥ 30 evaluation questions) and compares two chunking approaches.

Pipeline: Documents → Parsing → Chunking → Embedding → ChromaDB → Retrieval → Gemini → Answer + Citation.
Stack: Python, PySide6, ChromaDB, Google Gemini API (`google-genai`), pytest.

> **Status:** in development; final submission 2026-10-01. Plan: [`docs/plans/master-plan.md`](docs/plans/master-plan.md).
> This README is a draft. Setup, usage and results sections are added in EPIC-07.

## Dataset

**What:** 24 English technical documentation pages about C#, .NET testing, ASP.NET Core and EF Core, saved as Markdown. 22 are Microsoft Learn pages, #29 is a Microsoft docs page hosted on GitHub, and #15 is a Microsoft Q&A thread. Questions to the assistant may be in English or Vietnamese; the documents stay English.

| | Count | Where |
|---|---|---|
| Original documents | 28 | IDs 1–29; **#25 never existed** (skipped during conversion) |
| Accepted (used by the assistant) | 24 | `corpus/sources/` |
| Excluded (never used) | 4 | `corpus/excluded/`: IDs 14, 19, 24, 27. They are index pages: mostly links to other pages, with no content useful to the assistant |

**Size:** about 1.2 million characters in total. Three pages are huge: #23 Routing (381K), #17 Integration tests (258K) and #13 Handle errors (239K). Together they are 73% of all text, because each repeats the same article once per ASP.NET Core version. Removing exactly repeated sections leaves about 0.86 million characters. The smallest page is #09 (1.1K).

**Topics:**

| Group | IDs |
|---|---|
| C# language: types and reference | 04, 06, 07, 16, 18, 21, 26 |
| C# asynchronous programming | 01, 02 |
| C# overview and hub pages | 05, 08, 09, 20 |
| .NET testing | 03, 17, 28 |
| ASP.NET Core | 10, 11, 12, 13, 23, 29 |
| ASP.NET Core community Q&A | 15 |
| EF Core | 22 |

Details: [`docs/knowledge/domain/corpus-topic-map.md`](docs/knowledge/domain/corpus-topic-map.md).

**Files:**
- [`corpus/manifest.json`](corpus/manifest.json): one entry per accepted document (ID, title, source URL, size, SHA-256, heading counts).
- [`data/processed/documents/section-inventory.jsonl`](data/processed/documents/section-inventory.jsonl): every H1–H3 section with its heading path, line range and size.
- [`corpus/links.txt`](corpus/links.txt): the original URL for every original ID.
- Both generated files are rebuilt with `.venv/Scripts/python.exe scripts/utilities/build_corpus_inventory.py`. Don't edit them by hand.

**Rules:** source files are read-only originals and are never renumbered, edited or deleted. Excluded documents are never used. Cleanup (removing page boilerplate, dropping duplicate chunks) happens in memory only.

## Setup, usage, evaluation and experiment results

TBD (EPIC-07).

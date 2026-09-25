# INGEST-002 spot-check (5 chunks per arm)

Date: 2026-09-25. Read by hand (Claude Code, INGEST-002 session) from `data/processed/chunks/arm-a.jsonl` and `arm-b.jsonl`; `display_text` head/tail and `embed_text` head of each chunk were printed and read. Covers #13/#17/#23 (large, versioned) and the tiny docs #09/#22/#29, as the prompt asks.

## Arm A (`header-1600`)

| Chunk | Heading path | Chars | What I saw |
|---|---|---|---|
| `13:header-1600:0005` | Handle errors in ASP.NET Core > Exception handler page | 1,358 | Second piece of a split section. Starts with the 200-char overlap at a word boundary, mid-sentence ("that is used in templates, only the request path…"), then a whole paragraph, a whole code fence and prose. Ends at a paragraph end. Heading path correct. In `embed_text` the `[UseExceptionHandler](/en-us/…)` link is reduced to its text. |
| `09:header-1600:0001` | C# language reference > C# language reference | 24 | **Heading-only chunk**: `## C# language reference`. The H2 is followed directly by H3 children, and D3 merges a small section only with its next *sibling*, so nothing merges into it. 19 such chunks in Arm A (`heading_only_chunks` in the stats). Retrieval noise candidate; changing it needs an ADR-0003 amendment (see report, open items). |
| `10:header-1600:0038` | Dependency injection in ASP.NET Core > Framework-provided services | 628 | Continuation of a table longer than 1,600 chars (split by rows). `display_text` starts at a row boundary and is the exact slice; `embed_text` repeats the header row `\| Service type \| Lifetime \|` + separator (owner decision 2026-09-25) and links in the rows are reduced to their text. |
| `22:header-1600:0000` | Querying Data | 848 | Tiny doc #22: H1 intro section as one chunk, ends at a paragraph end. `embed_text` = "Querying Data" + blank line + text, so the H1 appears twice (path line + `# Querying Data`); expected from D5. |
| `02:header-1600:0003` | Asynchronous programming scenarios > Explore the asynchronous programming model > I/O-bound example: Download data from web service | 719 | A whole H3 section: heading, explanation, the complete code fence and the sentence after it. Code and explanation stay together. |

## Arm B (`fixed-1600`)

| Chunk | Heading path | Chars | What I saw |
|---|---|---|---|
| `17:fixed-1600:0010` | Integration tests in ASP.NET Core > Customize WebApplicationFactory | 1,599 | Starts and ends inside a C# code block (`override void ConfigureWebHost…` … `services.Si`); no fence line in the chunk, so the code is detached from its explanation. Expected Arm B failure mode (ADR-0003 "fixed-size chunks separating code from its explanation"); 45% of Arm B chunks cut a fence vs 3.2% in Arm A. |
| `29:fixed-1600:0000` | ASP0033: `[ValidatableType]` is applied to an inaccessible type | 1,282 | Tiny doc #29 is a single chunk (whole document, 1,282 chars). Also #09. |
| `02:fixed-1600:0005` | Asynchronous programming scenarios > Recognize CPU-bound and I/O-bound scenarios | 1,600 | Starts mid-word ("n.") at the end of the previous section, so the heading path (nearest heading before the start, D5) names that section although most of the chunk is "Explore other examples" / "Extract data from a network". Ends mid-code. Citation location can be misleading for Arm B. |
| `13:fixed-1600:0040` | Handle errors in ASP.NET Core > Exception handler lambda | 1,600 | Starts mid-link (`-page) is to provide…`), contains an opening fence and ends inside the next code block. Version variants of #13 do not align with 1,400-char steps, so Arm B drops **0** duplicates (Arm A: 447). |
| `22:fixed-1600:0001` | Querying Data > Further readings | 207 | Last window of #22: the 200-char overlap plus 7 new chars. Starts mid-URL, so `embed_text` keeps the broken link tail `arp/programming-guide/…)`: link stripping cannot see a link whose `[text]` is in the previous window. |

## Summary
- Arm A behaves as specified: section-aligned, code/tables whole unless > 1,600, overlap only inside split sections, every heading path in the inventory (G2 check).
- Arm A issue to decide (not a bug against ADR-0003): 19 heading-only chunks and 79 chunks under 400 chars (the rest are the short last pieces of split sections and short sections without a sibling after them).
- Arm B shows the expected failure modes (fence cuts, misleading heading path, no dedup of version variants, broken links at window edges).

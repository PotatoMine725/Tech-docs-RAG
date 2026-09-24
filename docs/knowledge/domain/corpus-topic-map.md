# Corpus topic map

Distilled from `corpus/manifest.json` and the section inventory (`data/processed/documents/section-inventory.jsonl`), generated 2026-09-24. Topics come from each page's title and H2 headings, not from a full read. Sizes are characters of the whole file, with LF line endings.

## Topic groups (24 accepted documents)

| Group | IDs | Pages |
|---|---|---|
| C# language: types and reference | 04, 06, 07, 16, 18, 21, 26 | Built-in types and literals; C# keywords; C# classes; Integral numeric types; Language specification introduction; Pattern matching (`is`/`switch`); The C# type system |
| C# asynchronous programming | 01, 02 | Async and await; Async scenarios (CPU-bound vs I/O-bound) |
| C# overview and hub pages | 05, 08, 09, 20 | C# guide hub; C# docs landing page; Language reference hub; A tour of the C# language |
| .NET testing | 03, 17, 28 | Unit testing best practices; Integration tests in ASP.NET Core; Unit testing with `dotnet test` and xUnit |
| ASP.NET Core | 10, 11, 12, 13, 23, 29 | Dependency injection; Factory-based middleware activation; Handle errors in APIs; Handle errors (general); Routing; Analyzer rule ASP0033 |
| ASP.NET Core community Q&A | 15 | Microsoft Q&A thread: creating a backend with ASP.NET Core Web API (a question page, not official documentation) |
| EF Core | 22 | Querying data |

## Size classes

- **Huge (73% of all text):** #23 Routing (381K), #17 Integration tests (258K), #13 Handle errors (239K). Each repeats the same article once per ASP.NET Core version (largest repeat of one H2 heading path: #13 8×, #17 6×, #23 4×).
- **Tiny (under 3K):** #09 (1.1K), #29 (1.7K), #22 (1.9K), #18 (2.8K). #08 is 3K but has 21 small sections, mostly links.
- **Everything else:** 7K–43K.

## Overlaps to watch (question design and failure analysis)

| Overlap | IDs | Why it matters |
|---|---|---|
| Error handling | 12 vs 13 | Both have "Developer exception page", "Exception handler" and "Problem details" sections. A question may match either one. |
| Async | 01 vs 02 | Same topic at two levels of detail. |
| Unit testing | 03 vs 28 (and 17) | Best practices vs a hands-on tutorial; 17 covers integration tests. |
| Types | 04 vs 16 vs 26 | Built-in types, integral types and the type system overlap. |
| Tours and hubs | 05, 08, 09, 20 | Hub pages are mostly link lists and may be retrieved as noise (ADR-0003 failure modes). |
| Version variants | 10, 11, 12, 13, 17, 23 | The same heading path appears 2–8 times in one document. Any variant counts as a hit (ADR-0003 D8). |

## Low-value sections

Many pages end with navigation sections such as "Additional resources", "See also", "Related links" and "Stay in touch". They hold little or no answerable content, so ground-truth questions should not target them.

## Structural notes

- Every file starts with an export wrapper: `# <title> - Microsoft Learn` (or `| Microsoft Learn`), a `Source:` URL and `---`, then the page's own H1. The heading path root is that second H1 (ADR-0003 D2).
- #29 (GitHub) has a YAML front-matter block (`title:`, `author:`, `uid:` …) between the wrapper and its H1.
- #15 is a Q&A page whose H2s are "0 additional answers" and "Your answer".

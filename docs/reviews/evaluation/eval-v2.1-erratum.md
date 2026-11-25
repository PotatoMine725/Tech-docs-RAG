# Erratum eval-v2.1: C2-21 heading paths after the PDF `#` escape

Date: 2026-11-25. Status: **pending owner OK** (tag `eval-freeze-v2.1` not created yet).
Cause: owner decision 2026-11-25 (ADR-0008, open item 1). PDF conversion now escapes lines that start with `#`
(`\#`), so they stay text and are no longer read as Markdown headings
(`infrastructure/parsing/markitdown_parser.py`, PDF only).

## Effect on the corpus
Only C2-21 (`notetaking.pdf`) changes. No other converted document has a `#`-line in a PDF (checked: all 24
accepted documents).

| C2-21 manifest field | old | new |
|---|---|---|
| `converted_sha256` | `6168c7b0…6c5125` | `25311bcd…29ad60` |
| `chars` | 72973 | 72976 (3 backslashes) |
| `headings` | 3 | 0 |

The three escaped lines are `# number Please answer # 7.`, `# number` and `# no. number`. `#s numbers …` is
not heading-shaped and is unchanged. C2-21 is now heading-less, so its only section is the whole-document span
`""` (sections.jsonl: 188 -> 185 spans).

## Ground-truth change (heading paths only)
Every `heading_path` that pointed at a removed C2-21 heading becomes `""`, in `expected_sources` **and** in
`evidence` (the validator checks both). Edited in `drafts-v2/b-c-e-f.yaml`, rebuilt with `build_questions_v2.py`.

| case | old heading path | new | fields changed |
|---|---|---|---|
| Q2-EVAL-048 | `number` | `""` | expected_sources[0], evidence[0..1] |
| Q2-EVAL-049 | `number Please answer # 7.` | `""` | expected_sources[0], evidence[0..2] |
| Q2-EVAL-058 | `no. number` | `""` | expected_sources[0], evidence[0..1] |

**Q2-EVAL-058 was not named in the owner's note** (which listed 048/049). It cites C2-21 under `no. number`,
which no longer exists, so it must change too or the frozen validation fails. Needs owner OK.

Unchanged: questions, answers, answer points, quotes, sources, statuses, every other case, `dev-v2.jsonl`,
`evidence-map-v2.yaml` (a field-by-field diff against `eval-freeze-v2` shows exactly the 10 fields above).
`validate_questions_v2.py --frozen`: OK (72 eval / 6 dev).

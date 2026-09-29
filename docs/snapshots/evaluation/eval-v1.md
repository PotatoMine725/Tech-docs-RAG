# eval-v1 — frozen ground truth (M1 / G5A)

Point-in-time snapshot. Approved by the owner on 2026-09-26 ("approve with fixes": Q-EVAL-024, 017, 028 wording; G1; A1–A10 approved; see [review sheet](../../reviews/evaluation/eval-v1-review.md)).

| Item | Value |
|---|---|
| Frozen on | 2026-09-26 |
| Merge commit (PR #8, `eval-002` → `dev`) | `1dd3b88d255cd9c6b3914330f1edb2ca0c244ceb` |
| Tag | `eval-freeze-v1` (on the freeze commit that adds this file) |
| `data/evaluation/questions/eval-v1.jsonl` SHA-256 | `3436870ef02dfc2c25bd9d403ec6c8dd44cb46dfacbf02d586161dedd1252937` (36 cases) |
| `data/evaluation/questions/dev-v1.jsonl` SHA-256 | `37d349e5a7fa43a179755d1c7993ef5a8438954f995bedcaee07bcfbf4da21d6` (6 cases) |
| `data/chroma/` at freeze | only `.gitkeep`: no index existed before the freeze |

After this point any change to either file is a logged amendment (what, why, date), never a quiet edit.

# VERIFY RAG-002

Verifier session, 2026-09-26 (19:21–19:50 UTC+7), Windows 11, `.venv` Python 3.13. Reviewed branch `rag-002` at
`d9a59df` (PR #13 into `dev`, merge base `dfcfbd4` = `origin/dev`). Commits: `4ed1eda` (chore), `e12eba8`, `d8b8fec`,
`999da92`, `d9a59df`.

**Quota rule: zero Gemini requests were spent.** The Chroma store and the embedding cache were read only. The dev
top-1 scores were re-derived through a `CachingEmbedder` whose inner embedder raises on any cache miss. `.env` was not
opened. No eval question text was printed or written anywhere.

## Verdict: ACCEPT WITH FIXES

1 FAIL (F1: code index expressions such as `args[0]` are parsed as citation markers). 0 UNVERIFIED except the live
LLM request count, which can only be traced to the validation file. Everything else passes and was re-run by the verifier.

## Checks (owner's list 1–10, then 99-VERIFY A–G)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Baseline | PASS | A scratch worktree of `origin/dev` `dfcfbd4` gave `313 passed, 1 deselected in 10.19s`. `rag-002` `d9a59df` gave `369 passed, 1 deselected in 8.75s`. The difference is +56, which matches the report. The report's 313, which it said was not re-run, is now measured. |
| 2a | `passage_hash` | PASS | `passage.py:7-19`: SHA-256 of `embed_text` with its leading `heading path + "\n\n"` line removed. `render_passage` (`prompt_builder.py:40`) and `build_citation` (`citations.py:70`) use the same `passage_body`, so the hash covers exactly the text the LLM sees. An independent recompute (own strip + own SHA-256 over every chunk read from Chroma, 733 + 859) gave 0 mismatches with `passage_body`/`passage_hash`. `content_hash` is unchanged: no file under `infrastructure/chunking/` is in the diff, and `chunk_builder.py:86` still hashes `display_text`. |
| 2b | Tie-break, `duplicate_chunk_ids` | PASS | `retrieve.py:31` sorts by `(-score, chunk_id)` and ignores store order. The kept hit gets `duplicate_chunk_ids=tuple(replaced[key])` (`:43`). Tests: `test_equal_scores_break_ties_by_chunk_id_and_are_stable` (3 insertion orders), `test_duplicates_across_documents_collapse_to_one_slot_with_duplicate_ids`. |
| 2c | Arm A 13 / 26, Arm B 0 | PASS | Recomputed from the Chroma collections. `kb_header-1600…`: 733 chunks, **13 groups / 26 extra copies**; by `content_hash` 2; by identical `embed_text` 24 (this is the RAG-001b "24"). `kb_fixed-1600…`: 859 chunks, **0 / 0**. The group list equals the validation file (12/13 ×2, 13-internal, 17 ×8, 23 ×2). |
| 2d | Eval cases touching groups | PASS | Read-only overlap of every `expected-spans-v1.json` span with every group member (source + char overlap): exactly Q-EVAL-003 S1 (expected #13 `13:header-1600:0002`, alternate #12 `12:header-1600:0002`) and Q-EVAL-004 S1 (same pair); kept on a tie = `12:header-1600:0002`. This matches the report's table row for row. No doc 17/23/13-internal group is touched. |
| 3a | Threshold 0.686 | PASS | From the validation file (lines 37–42), Arm A answerable top-1 = 0.7360, 0.7943, 0.7737, 0.7548 → min 0.7360 − 0.05 = **0.6860**. **Re-derived offline**: all 12 (arm, case) top-1 scores reproduced to 4 decimals from the cached query vectors + Chroma, 0 cache misses. `config.py` default = 0.686. At 0.686 the gate refuses Q-DEV-005/006 on both arms and no answerable case. |
| 3b | Gate before LLM, boundary | PASS | `answer_question.py:89-95`: the gate returns before `build`/`generate`. `test_gate_fires_below_threshold_and_llm_is_not_called` asserts `llm.requests == []`. Boundary: `test_gate_does_not_fire_at_or_above_threshold` uses a top score exactly equal to the threshold (0.5) → the LLM is called. Spec `retrieval-spec.md:34` says "top-1 score < threshold" (strict), so equality passes. There is no explicit sentence for the equality case (see note N3). |
| 4a | Invalid JSON → `GenerationError` + raw text | PASS | `parse_answer_json` (`:35-55`); 5 parametrized cases all assert `caught.value.raw_text == raw`. It is never turned into "insufficient". |
| 4b | Markers outside 1..k removed + recorded; union | **FAIL (F1)** | Real markers work: `[7]` with k=5 is removed and recorded, and the union order is markers first, then `cited_passages` (`test_citations_follow_answer_order_then_cited_passages`). **But** `_MARKER = r"\[(\d+)\]"` (`citations.py:13`) also matches code. Verifier probe: `resolve_citations("Use \`args[0]\` and \`values[7]\` like this [1].\n\`\`\`csharp\nvar x = items[2];\n\`\`\`", [1], k=5)` gives answer `"Use \`args\` and \`values\` like this [1]. … items[2] …"`, citations `[1, 2]`, dropped `(0, 7)`. So the code shown to the user is silently changed (prompt rule 4 says code stays exact), a citation to passage 2 is invented, and `dropped_markers`, the hallucination signal that evaluation will measure, counts C# indexers. |
| 4c | D2: citations on insufficient = related-only | PASS | `:103-112`: when `insufficient`, `answer` = the localized message, `missing_information` is kept, and the citations come only from `cited_passages`/markers. `AnswerResult` has no `related_only` field; the report (GUI mismatch 1) derives it from `insufficient`. Test: `test_llm_insufficient_keeps_missing_information_and_related_citations`. |
| 5 | Prompt, messages, model names | PASS | `PromptBuilder.from_dir(prompts_dir, version)` reads `config/prompts/<version>.md`; the version comes from `ANSWER_PROMPT_VERSION` (default `answer_v1`). Grep for template sentences in `src/`, `scripts/`: 0. Messages are loaded from `config/messages.json` (`load_messages`). A grep in `src/` finds the message strings only in `presentation/.../fake_ask_question.py`, a GUI-001-pre file not in this diff (N2). Model names outside `config.py`: only in tests that assert the config value. No `-latest` alias. |
| 6 | Layering | PASS | `grep -E "^\s*(import\|from)\s+(google\|chromadb\|PySide6)" core/ application/` → 0 lines. `tests/unit/test_project_structure.py`: 7 passed. `core/models` imports `LLMResponse` from `core/interfaces/llm` (core → core, no cycle). |
| 7 | Eval firewall | PASS | Verifier script (eval question texts held in memory, never printed): **0 of 36 question texts** in `validation/`, `data/logs/`, `scripts/`, `tests/`, and 0 in the lines this PR adds. **Eval IDs: 0** in `validation/generation/` and `data/logs/`. Hits elsewhere are all in files from earlier tasks that RAG-002 did not touch: `validation/ingestion/blueprint-coverage-arm-a.md` (BP-EVAL IDs), `scripts/evaluation/*` (file name) and `tests/unit/test_eval_dataset.py`, `test_evaluation_blueprints.py`, `test_eval_expected_spans.py`, `test_eval_retrieval_metrics.py`. All 5 ID hits among the added lines are in the execution report's owner-requested table/section. `eval-v1.jsonl` `3436870e…` and `dev-v1.jsonl` `37d349e5…` are unchanged since `eval-freeze-v1`. `expected-spans-v1.json` differs from the tag because of EVAL-003b-pre, and not in this PR (`git diff origin/dev HEAD` empty). |
| 8 | Mutations (2 of 4, scratch worktree) | PASS | M1 dedup key → `hit.chunk.content_hash`: `test_link_only_difference_is_a_duplicate_although_content_hash_differs` FAILED (1 failed, 152 passed). M3 gate `<` → `<=`: `test_gate_does_not_fire_at_or_above_threshold` FAILED (1 failed, 152 passed). The worktree was removed afterwards. |
| 9 | Secrets (`AIza` + 35) | PASS | The full `git diff origin/dev...HEAD` (160 k chars): 0. `validation/` (12 files), `data/logs/`: 0. One hit in the tree, `tests/.../__pycache__/test_gemini_embedder…pyc`, is the synthetic `"AIza" + "x" * 35` from a pre-existing redaction test (`test_gemini_embedder.py:215`), not a key. |
| 10 | HIGH risk: `Citation`, `RetrievedChunk` | PASS (additive; new required fields) | Diff `core/models/__init__.py`: nothing removed or renamed. `RetrievedChunk` gains `duplicate_chunk_ids=()` at the end (defaulted). `Citation` gains **required** `chunk_id`, `marker`, `source_url`, placed before the defaulted `location_type`. That would break positional 5-argument callers, but none exist. Call sites: `RetrievedChunk(` in `chroma_store.py:146` (keywords), `retrieve.py:43`, `tests/fakes.py:177` and tests (3 positional, still valid). Core `Citation(`: only `citations.py:66` (keywords). `fake_ask_question.py:29` builds the GUI's `contracts.Citation`, not the core one. Suite green on both sides (check 1). |
| A | Task-prompt "Do" / acceptance | PASS except §3.4 markers (F1) | §1 contracts match the prompt, plus the reported deviations 1–4. §3.1 `detect_language`: 12 cases + NFD, VI without diacritics → "en" documented. §3.2–3.6 present. §3.7 all 7 test bullets map to tests (report table checked against the test names). §3.8 validation file exists, dev only. Acceptance: offline pytest green; no TBD for threshold/prompt/citation in the three specs (`grep -i "TBD\|DECISION REQUIRED"` → 0); prompt file referenced by version; eval IDs in `validation/generation` + logs = 0. |
| B | Tests quality | PASS, with one gap | The tests assert behaviour, not mocks: exact answer text after removal, citation fields, `llm.requests == []`, `raw_text`. The gap is F1: no test puts code containing `[n]` in an answer. |
| C | Claims vs reality | PASS | Traced: 313/369/+56 (re-run); 13/26 and 2/24 (recomputed); the 12 top-1 scores (recomputed); 0.686; the eval-overlap table; 6 embed requests (cache: exactly 6 `query` rows created `2026-09-26T12:05`, plus 1 older probe row at 02:19). The 2 LLM requests and their token counts trace only to the validation file (lines 139–197); no server-side record exists (UNVERIFIED by construction; consistent). |
| D | Project rules | PASS | Checks 5, 6, 7, 9. Corpus/data: `git diff --stat origin/dev...HEAD -- corpus data` is empty. |
| E | Scope | PASS | The deviations are all disclosed with owner decisions (`passage_hash`, `duplicate_chunk_ids`, `AnswerResult.duplicates_dropped`, `RetrievalResult`). The G3 box was correctly left unticked. The chore commit `4ed1eda` (GitNexus counts) was separate and disclosed. |
| F | Quality spot-read | FAIL (F1) | `dedupe_by_passage`, `AnswerQuestion.ask`, `resolve_citations`, `GeminiLLM.generate` were read line by line. Swallowed exceptions: none; the adapter raises `GenerationError` on MAX_TOKENS/SAFETY/empty. The ranks are 1..k after dedup. `retrieved[0]` is safe because an empty store raises `RetrievalError` first. The defect is F1. |
| G | Explain-it-back | PASS | All 5 bullets are correct. One precision: "Markers outside 1..k are removed and counted as a hallucination signal" is currently also true for code indexers (F1). |

## Findings

**F1 (FAIL, medium): citation-marker regex matches code.** `citations.py:13-14` (`_MARKER`, `_MARKER_WITH_SPACE`)
matches every `[digits]`, including indexers in inline code and fenced code blocks. Effects:
- the user-visible code is altered (`args[0]` → `args`);
- citations are invented (`items[2]` → citation 2);
- `dropped_markers` and `count_uncited_sentences` are skewed.

The corpus is mostly C#/.NET, so answers with indexers are likely. The task prompt said "extract `[n]`" without
addressing code; this is a spec gap, fixed below.

Non-blocking notes:
- **N1:** doc 15 passage bodies still contain `[](data:image/svg+xml, …)` links: 8 chunks in Arm A, 6 in Arm B. Arm A also has
  `23:header-1600:0085`, a link whose text has nested parentheses. They come from the chunker's link regex (INGEST, pre-existing), not RAG-002. Dedup is
  unaffected. They cost prompt tokens when doc 15 is retrieved. For a later ingestion task, not this fix.
- **N2:** `presentation/desktop/viewmodels/fake_ask_question.py` (GUI-001-pre) inlines the two insufficient messages.
  GUI-001 wiring should read `config/messages.json` through the real use case.
- **N3:** gate equality (score == threshold → LLM is called) follows from the strict `<` in `retrieval-spec.md:34` and
  the test name. One explicit sentence in the spec would remove any doubt.
- **N4:** the `@pytest.mark.gemini` live test for the LLM was not added (disclosed; the prompt allowed a script).

## Held until re-verify (owner instructions, conditional on ACCEPT)
These are **not** applied yet:
- tick M2 in `master-plan.md`;
- ledger row 08 (RAG-003): "smoke must exercise the LLM insufficient path once: Q-DEV-005 with gate disabled (1 LLM request)";
- ledger row 09a: "runner records top-1 and gate decision per case; report answerable cases refused by the gate".

## Fix prompt (run in a new session on branch `rag-002`)

```
RAG-002 fix after 99-VERIFY (docs/reviews/code/RAG-002-verify.md, F1). Zero Gemini requests. Never open .env.
Read CLAUDE.md, citation-spec.md, and src/knowledge_assistant/application/citation/citations.py first.
Run gitnexus impact on extract_markers, remove_markers, count_uncited_sentences, resolve_citations before editing.

1. citations.py: citation markers are only recognised OUTSIDE code. Ignore any [n] inside inline backtick
   spans (`...`) and inside fenced code blocks (``` or ~~~ fences) in extract_markers, remove_markers and
   count_uncited_sentences (a sentence whose only "[n]" is inside code counts as uncited).
   Code text must come back byte-identical.
   Owner decision (ask, do not assume): should a [n] directly preceded by a word character outside code
   (e.g. prose "args[0]") also be ignored? Record the answer in citation-spec.md.
2. Tests (tests/unit/application/test_citations.py), each must fail on the current code:
   - the verifier's probe: resolve_citations("Use `args[0]` and `values[7]` like this [1].\n```csharp\nvar x = items[2];\n```", [1], k=5)
     -> answer unchanged, citations [1] only, dropped ().
   - regression: "A [2][3]. B. [1]" still yields markers [2, 3, 1]; "[7]" in prose with k=5 is still dropped and removed.
   - an AnswerQuestion-level test where the LLM answer contains a fenced code block with an indexer.
3. citation-spec.md: one sentence stating markers inside code are not markers.
   retrieval-spec.md: one sentence stating score == threshold is not gated (N3).
4. Mutation: make the code-skipping a no-op -> the new tests fail; restore.
5. Offline suite: report the exact count (expected 369 + new tests). gitnexus_detect_changes before commit.
   Update the execution report (addendum section) and AI_WORKLOG (fix entry). Commit "RAG-002: fix F1 ...", push. Stop.
Re-verify step (verifier session, after the fix): confirm F1 with the probe, then apply the held items:
tick M2 in master-plan; ledger row 08 += "smoke must exercise the LLM insufficient path once: Q-DEV-005 with gate
disabled (1 LLM request)"; ledger row 09a += "runner records top-1 and gate decision per case; report answerable
cases refused by the gate"; row 07 -> verified.
```

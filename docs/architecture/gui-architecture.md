# Gui architecture

PySide6 desktop under presentation/desktop (app, windows, views, viewmodels, widgets, dialogs, resources). Must not parse, access ChromaDB, call Gemini, retrieve or evaluate; calls application use cases. Only an app.py scaffold exists (PySide6 imported lazily).

## Wiring the real use case (GUI-001)

- `viewmodels/core_ask_question.py` is the ONE adapter: `to_gui_result` (core `AnswerResult` -> `contracts.AnswerResult`) and `CoreAskQuestion` (the `AskQuestionPort`; one `AnswerQuestion` per arm, built on first use; errors -> `AskQuestionError(kind)`: `LLMError.kind` 1:1, `RetrievalError`/`VectorStoreError` -> `no_index`, anything else -> `other`). It imports core only.
- `wiring.py` is the ONLY presentation module that imports `composition` and `infrastructure` (the GUI process is one more entry point, like `scripts/ask.py`). It builds one `GeminiLLM` shared by both arms (shared throttles), forces `ALLOW_FALLBACK=true`, and gives the retriever a per-call embedder (the embedding cache is a SQLite connection usable only on its creating thread, while the pool runs each question on any worker). `tests/unit/test_project_structure.py` pins "only `wiring.py`".
- `app.py` calls `build_real_port()` (default) or `FakeAskQuestion` (`--fake`); the fake reads its refusal text from `config/messages.json`.

## Notebook layout (GUI-002)

- `windows/main_window.py` is three panes in a splitter: the source list, the conversation (a `QTextBrowser` thread with the composer pinned under it), and the source viewer, shown only while a citation is open. Its look follows the Knowledge Assistant design system; `theme.py` holds the same tokens (light and dark, picked from the system colour scheme) and writes the Qt stylesheet.
- `AskViewModel` owns everything the window shows: the conversation as a list of `Turn`s, retry (the question moves to the end and is asked again with its original arm), recall of the last question, the viewer (`open_citation`, `step_citation`, `close_viewer`, "n of m"), per-source hit counts of the newest cited answer, and the answer split into text and citation-marker segments. The first version's single-answer properties (`state`, `result`, `selected`, `status_line`, ...) describe the newest turn.
- The port contract is unchanged (`ask(question, arm)`). Source titles reach the view-model as a constructor argument: `wiring.load_source_titles()` reads them from the corpus manifest (`CORPUS_MANIFEST`), the fake passes `FAKE_SOURCES`. A test pins that the manifest titles equal the `document_name`s in the chunk files.
- The thread is HTML with `cite:`, `copy:` and `retry:` anchors (`setOpenLinks(False)`); hovering a citation shows its excerpt as a tool-tip, clicking opens the viewer. The arm choice moved to the Settings menu.
- Not built yet (need application-layer work): limiting the search to chosen sources (retrieval has no source filter), suggested questions, a conversation kept between sessions, and showing the whole section around a cited passage (the GUI only receives the excerpt).

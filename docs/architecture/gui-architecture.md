# Gui architecture

PySide6 desktop under presentation/desktop (app, windows, views, viewmodels, widgets, dialogs, resources). Must not parse, access ChromaDB, call Gemini, retrieve or evaluate; calls application use cases. Only an app.py scaffold exists (PySide6 imported lazily).

## Wiring the real use case (GUI-001)

- `viewmodels/core_ask_question.py` is the ONE adapter: `to_gui_result` (core `AnswerResult` -> `contracts.AnswerResult`) and `CoreAskQuestion` (the `AskQuestionPort`; one `AnswerQuestion` per arm, built on first use; errors -> `AskQuestionError(kind)`: `LLMError.kind` 1:1, `RetrievalError`/`VectorStoreError` -> `no_index`, anything else -> `other`). It imports core only.
- `wiring.py` is the ONLY presentation module that imports `composition` and `infrastructure` (the GUI process is one more entry point, like `scripts/ask.py`). It builds one `GeminiLLM` shared by both arms (shared throttles), forces `ALLOW_FALLBACK=true`, and gives the retriever a per-call embedder (the embedding cache is a SQLite connection usable only on its creating thread, while the pool runs each question on any worker). `tests/unit/test_project_structure.py` pins "only `wiring.py`".
- `app.py` calls `build_real_port()` (default) or `FakeAskQuestion` (`--fake`); the fake reads its refusal text from `config/messages.json`.

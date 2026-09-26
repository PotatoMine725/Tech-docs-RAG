# Tech stack

- PRIMARY LANGUAGE: Python
- DESKTOP UI: PySide6
- VECTOR DATABASE: ChromaDB
- LLM PROVIDER: Google Gemini API (official `google-genai` SDK); answer model + judge `gemini-3.5-flash-lite`, fallback `gemini-3.5-flash` (ADR-0004; names in config only)
- LLM AUTHENTICATION: `GEMINI_API_KEY` environment variable (never committed; `.env` git-ignored; `.env.example` placeholders only)
- TESTING: pytest (Gemini-dependent tests use the `gemini` marker and are deselected by default)
- SOURCE FORMAT: current corpus = Markdown; architecture = format-independent
- STRUCTURED DATA: JSON / JSONL
- OPTIONAL FUTURE STORAGE: SQLite only if a concrete requirement appears (first one: the embedding cache, ADR-0005 D18)
- DOCUMENT CONVERSION: Microsoft MarkItDown `markitdown[pdf,docx]>=0.1.8,<0.2` (ADR-0002; added in INGEST-003; only `infrastructure/parsing/markitdown_parser.py`). Its `magika` dependency needs `onnxruntime`, which `chromadb` already requires (no new runtime; imported lazily).
- CHUNKING: header-aware baseline; fixed-size as experiment comparison (ADR-0002); parameters in ADR-0003
- EMBEDDING: abstracted behind `core.interfaces.embedding`; `gemini-embedding-001` (ADR-0004); MUST be multilingual (EN + VI queries over an English corpus, ADR-0003 D9)
- LLM: Gemini API through an abstraction/interface (`core.interfaces.llm`)
- RERANKING: optional / experiment / bonus
- PACKAGING: PyInstaller later if required
- Extra dependency: `python-dotenv` (already used by existing scripts/utilities/smoke_test.py)

## Not part of the default stack
C#, .NET, Java, Node.js, React, Angular, Vue, Flutter, Electron, ASP.NET Core as an app framework (it appears only as corpus subject matter), SQLite (until required), ML/ONNX/local models (until required), reranking (until an experiment).

## Configuration notes
- `CHROMA_PATH` env var; default `data/chroma/` (OD-7, ADR-0005 D16; was `D:\ChromaDB`).
- Generated vector data is git-ignored and not committed; it is rebuilt by script from the chunk files and the embedding cache (ADR-0005 D16).
- Embedding settings (model, dimension 768, limits, batch size) live in `config.py`, env-overridable (ADR-0005).
- SQLite (stdlib `sqlite3`) is used for one concrete need: the embedding cache `data/cache/embeddings.sqlite` (atomic per-batch writes, resume across quota days; ADR-0005 D18).

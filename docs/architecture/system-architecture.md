# System architecture

Layers: presentation -> application -> core <- infrastructure.
- core: domain models, interfaces, exceptions; no PySide6, ChromaDB, Gemini or format-specific dependency.
- application: use cases (ingestion, retrieval, generation, citation, evaluation); depends on core interfaces only.
- infrastructure: parsers, chunkers, embeddings, ChromaDB, Gemini, persistence; implements core interfaces.
- presentation: PySide6 desktop GUI; no business logic.
Enforced by tests/unit/test_project_structure.py (core/application import checks).

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "knowledge_assistant"
EXCLUDED_IDS = {"14", "19", "24", "27"}
FORBIDDEN_CORE = ("PySide6", "chromadb", "google", "markitdown", "httpx")  # httpx: RAG-003, raw HTTP errors stay in infrastructure
FORBIDDEN_APP = FORBIDDEN_CORE


def _imports(layer: str) -> set[str]:
    found = set()
    for py in (PKG / layer).rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
    return found


def test_package_imports():
    import knowledge_assistant  # noqa: F401
    from knowledge_assistant.core import models  # noqa: F401
    from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM  # noqa: F401


def test_core_has_no_technology_dependencies():
    assert not _imports("core") & set(FORBIDDEN_CORE)


def test_application_has_no_technology_or_presentation_dependencies():
    assert not _imports("application") & set(FORBIDDEN_APP)
    assert "presentation" not in _imports("application")


def test_presentation_does_not_import_provider_libraries():
    """RAG-003: google.genai / httpx exceptions are wrapped in infrastructure, so the GUI never needs (or sees) them."""
    assert not _imports("presentation") & {"google", "httpx", "chromadb", "markitdown"}


def test_core_and_application_do_not_import_outer_layers():
    for layer in ("core", "application"):
        for py in (PKG / layer).rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            assert "knowledge_assistant.infrastructure" not in text, py
            assert "knowledge_assistant.presentation" not in text, py


def test_markitdown_is_imported_only_by_its_adapter():
    """ADR-0002: MarkItDown lives in one infrastructure/parsing module."""
    importers = set()
    for py in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            if any(name.split(".")[0] == "markitdown" for name in names):
                importers.add(py.relative_to(PKG).as_posix())
    assert importers == {"infrastructure/parsing/markitdown_parser.py"}


def test_excluded_corpus_ids_are_exactly_14_19_24_27():
    excluded = {p.name.split("-")[0] for p in (ROOT / "corpus" / "excluded").glob("*.md")}
    assert excluded == EXCLUDED_IDS


def test_excluded_ids_absent_from_sources():
    sources = {p.name.split("-")[0] for p in (ROOT / "corpus" / "sources").glob("*.md")}
    assert not sources & EXCLUDED_IDS

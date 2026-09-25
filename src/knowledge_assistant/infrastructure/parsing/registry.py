"""Maps document formats (file extensions) to parser adapters."""
from knowledge_assistant.core.exceptions import ParserNotFoundError
from knowledge_assistant.core.interfaces.parser import DocumentParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {}

    def register(self, extension: str, parser: DocumentParser) -> None:
        self._parsers[extension.lower()] = parser

    def get(self, extension: str) -> DocumentParser:
        try:
            return self._parsers[extension.lower()]
        except KeyError:
            raise ParserNotFoundError(extension) from None


def default_registry() -> ParserRegistry:
    """Markdown is read directly; PDF, HTML, DOCX and txt go through one shared MarkItDown adapter (ADR-0002)."""
    from knowledge_assistant.infrastructure.parsing.markdown_parser import MarkdownParser
    from knowledge_assistant.infrastructure.parsing.markitdown_parser import MARKITDOWN_EXTENSIONS, MarkItDownParser

    registry = ParserRegistry()
    for extension in (".md", ".markdown"):
        registry.register(extension, MarkdownParser())
    converter = MarkItDownParser()
    for extension in MARKITDOWN_EXTENSIONS:
        registry.register(extension, converter)
    return registry

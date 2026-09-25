"""Maps document formats to parser adapters (skeleton)."""
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
    """Parsers for the formats the pipeline reads today (Markdown; MarkItDown formats come with INGEST-003)."""
    from knowledge_assistant.infrastructure.parsing.markdown_parser import MarkdownParser

    registry = ParserRegistry()
    for extension in (".md", ".markdown"):
        registry.register(extension, MarkdownParser())
    return registry

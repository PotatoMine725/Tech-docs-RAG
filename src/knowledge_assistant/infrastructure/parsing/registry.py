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

from typing import Protocol

from knowledge_assistant.core.models import Document, ParsedDocument


class DocumentParser(Protocol):
    def parse(self, document: Document) -> ParsedDocument: ...

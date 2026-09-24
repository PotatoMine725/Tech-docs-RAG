from typing import Protocol

from knowledge_assistant.core.models import ParsedDocument


class DocumentParser(Protocol):
    def parse(self, path: str) -> ParsedDocument: ...

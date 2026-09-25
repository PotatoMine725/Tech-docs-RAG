from typing import Protocol

from knowledge_assistant.core.models import DocumentChunk, ParsedDocument


class Chunker(Protocol):
    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]: ...

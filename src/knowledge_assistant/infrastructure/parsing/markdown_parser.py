"""Markdown parser adapter: reads the file as-is (line endings untouched; the normalizer handles them)."""
from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import Document, ParsedDocument


class MarkdownParser:
    def parse(self, document: Document) -> ParsedDocument:
        try:
            with open(document.path, encoding="utf-8", newline="") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            raise DocumentParseError(f"cannot read #{document.source_id} ({document.path}): {error}") from error
        return ParsedDocument(document=document, text=text, document_name=document.name, source_url=document.source_url)

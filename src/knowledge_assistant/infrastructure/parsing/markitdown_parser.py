"""MarkItDown adapter (ADR-0002): converts PDF, HTML, DOCX and plain-text files to Markdown.

The only module that imports `markitdown` (guarded by `tests/unit/test_project_structure.py`). The import and
the converters are created on the first `parse`, so building the default registry stays cheap for the Markdown
corpus. Each extension is sent to its own MarkItDown converter: the `MarkItDown` front end guesses the format from
the content and returned damaged or mismatched files (a zip renamed `.docx`, a header-only `.pdf`) as plain text.
The result is a raw `ParsedDocument` (`normalized=False`): the ADR-0003 D1 normalizer is specific to the
web-exported corpus pages and is not applied. Line endings are unified and the H1-H3 sections are computed the
same way as for normalized text, so both chunkers can take the document as-is.
"""
from pathlib import Path

from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans

# extension -> name of the converter class in `markitdown.converters`
_CONVERTERS = {
    ".pdf": "PdfConverter",
    ".html": "HtmlConverter",
    ".htm": "HtmlConverter",
    ".docx": "DocxConverter",
    ".txt": "PlainTextConverter",
}
MARKITDOWN_EXTENSIONS = tuple(_CONVERTERS)


class MarkItDownParser:
    def __init__(self) -> None:
        self._converters: dict[str, object] = {}

    def parse(self, document: Document) -> ParsedDocument:
        path = Path(document.path)
        extension = path.suffix.lower()
        where = f"#{document.source_id} ({document.path})"
        if extension not in _CONVERTERS:
            raise DocumentParseError(f"cannot convert {where}: no MarkItDown converter for {extension!r}")
        if not path.is_file():
            raise DocumentParseError(f"cannot convert {where}: {'not a file' if path.exists() else 'file not found'}")
        try:
            from markitdown import StreamInfo

            with path.open("rb") as stream:
                info = StreamInfo(extension=extension, local_path=str(path), filename=path.name)
                result = self._converter(extension).convert(stream, info)
        except Exception as error:  # converters raise format-specific errors; one clear error for callers
            raise DocumentParseError(f"cannot convert {where}: {error}") from error
        text = result.markdown.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        if not text.strip():  # e.g. a scanned PDF: an empty document must not vanish silently from the index
            raise DocumentParseError(f"cannot convert {where}: no text extracted")
        text += "\n"
        return ParsedDocument(
            document=document,
            text=text,
            document_name=" ".join((result.title or "").split()) or document.name,
            source_url=document.source_url,
            sections=section_spans(text),
        )

    def _converter(self, extension: str):
        name = _CONVERTERS[extension]
        if name not in self._converters:
            from markitdown import converters

            self._converters[name] = getattr(converters, name)()
        return self._converters[name]

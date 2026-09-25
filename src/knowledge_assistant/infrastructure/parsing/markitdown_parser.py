"""MarkItDown adapter (ADR-0002): converts PDF, HTML, DOCX and plain-text files to Markdown.

The only module that imports `markitdown` (guarded by `tests/unit/test_project_structure.py`). The import and
the converter are created on the first `parse`, so building the default registry stays cheap for the Markdown
corpus. The result is a raw `ParsedDocument` (`normalized=False`): the ADR-0003 D1 normalizer is specific to the
web-exported corpus pages and is not applied. Line endings are unified and the H1-H3 sections are computed the
same way as for normalized text, so both chunkers can take the document as-is.
"""
import zipfile
from pathlib import Path

from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans

MARKITDOWN_EXTENSIONS = (".pdf", ".html", ".htm", ".docx", ".txt")
# MarkItDown picks its converter from the content, so a damaged .docx silently comes back as plain text.
# Binary formats are therefore checked against their file signature first.
def _starts_like_pdf(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


_SIGNATURES = {".pdf": _starts_like_pdf, ".docx": zipfile.is_zipfile}


class MarkItDownParser:
    def __init__(self) -> None:
        self._converter = None

    def parse(self, document: Document) -> ParsedDocument:
        path = Path(document.path)
        check = _SIGNATURES.get(path.suffix.lower())
        try:
            if check is not None and not check(path):
                raise ValueError(f"content is not a valid {path.suffix.lower()} file")
            result = self._markitdown().convert_local(document.path)
        except Exception as error:  # MarkItDown raises format-specific errors; one clear error for callers
            raise DocumentParseError(f"cannot convert #{document.source_id} ({document.path}): {error}") from error
        text = result.text_content.replace("\r\n", "\n").replace("\r", "\n")
        text = text.strip("\n") + "\n" if text.strip() else ""
        return ParsedDocument(
            document=document,
            text=text,
            document_name=(result.title or "").strip() or document.name,
            source_url=document.source_url,
            sections=section_spans(text),
        )

    def _markitdown(self):
        if self._converter is None:
            from markitdown import MarkItDown

            self._converter = MarkItDown(enable_plugins=False)
        return self._converter

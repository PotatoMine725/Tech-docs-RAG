"""INGEST-003: MarkItDown adapter. Fixtures are built in the test (no binary files in the repo)."""
import io
import os
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import Document
from knowledge_assistant.infrastructure.chunking.factory import load_arm
from knowledge_assistant.infrastructure.parsing.markdown_parser import MarkdownParser
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans
from knowledge_assistant.infrastructure.parsing.markitdown_parser import MARKITDOWN_EXTENSIONS, MarkItDownParser
from knowledge_assistant.infrastructure.parsing.registry import default_registry

ROOT = Path(__file__).resolve().parents[3]
CHUNKING_CONFIG = ROOT / "config" / "chunking.json"

SECTIONS = (("Heading1", "Retry policy"), (None, "Use exponential backoff."), ("Heading2", "Limits"), (None, "At most five attempts."))
EXPECTED_MARKDOWN = "# Retry policy\n\nUse exponential backoff.\n\n## Limits\n\nAt most five attempts.\n"
HTML = (
    "<html><head><title>Retry guide</title></head><body><h1>Retry policy</h1><p>Use exponential backoff.</p>"
    "<h2>Limits</h2><p>At most five attempts.</p></body></html>"
)


def _pdf(lines: list[str]) -> bytes:
    """One-page PDF with Helvetica text lines and a correct xref table."""
    content = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def _docx(paragraphs) -> bytes:
    """Minimal WordprocessingML package: paragraphs with optional Heading1/Heading2 styles."""
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(
        "<w:p>"
        + (f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else "")
        + f"<w:r><w:t>{text}</w:t></w:r></w:p>"
        for style, text in paragraphs
    )
    styles = "".join(
        f'<w:style w:type="paragraph" w:styleId="Heading{n}"><w:name w:val="heading {n}"/></w:style>' for n in (1, 2)
    )
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    main = "application/vnd.openxmlformats-officedocument.wordprocessingml"
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/word/document.xml" ContentType="{main}.document.main+xml"/>'
            f'<Override PartName="/word/styles.xml" ContentType="{main}.styles+xml"/></Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="word/document.xml"/></Relationships>'
        ),
        "word/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/styles" Target="styles.xml"/></Relationships>'
        ),
        "word/document.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>',
        "word/styles.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{w}">{styles}</w:styles>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for name, data in files.items():
            package.writestr(name, data)
    return buffer.getvalue()


def _parse(tmp_path: Path, name: str, data: bytes | str, source_id: str = "90"):
    path = tmp_path / name
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    parser = default_registry().get(path.suffix)
    return parser.parse(Document(source_id, path.stem, str(path)))


def test_registry_sends_every_markitdown_format_to_one_adapter():
    registry = default_registry()
    parsers = {registry.get(extension.upper()) for extension in MARKITDOWN_EXTENSIONS}
    assert len(parsers) == 1 and isinstance(parsers.pop(), MarkItDownParser)
    assert isinstance(registry.get(".md"), MarkdownParser)


def test_html_becomes_markdown_with_headings_sections_and_title(tmp_path):
    parsed = _parse(tmp_path, "guide.html", HTML)
    assert parsed.text == EXPECTED_MARKDOWN
    assert parsed.document_name == "Retry guide"  # the HTML <title>
    assert [s.heading_path for s in parsed.sections] == [("Retry policy",), ("Retry policy", "Limits")]
    assert parsed.sections == section_spans(parsed.text)
    assert parsed.normalized is False  # the corpus-specific D1 normalizer is not applied


def test_docx_heading_styles_become_markdown_headings(tmp_path):
    parsed = _parse(tmp_path, "guide.docx", _docx(SECTIONS))
    assert parsed.text == EXPECTED_MARKDOWN
    assert parsed.document_name == "guide"  # no title in the file -> the Document name
    assert [s.heading_path for s in parsed.sections] == [("Retry policy",), ("Retry policy", "Limits")]


def test_pdf_text_is_extracted_without_headings(tmp_path):
    parsed = _parse(tmp_path, "notes.pdf", _pdf(["Retry policy overview", "Use exponential backoff."]))
    assert "Retry policy overview" in parsed.text and "Use exponential backoff." in parsed.text
    assert parsed.sections == ()  # plain PDF text has no Markdown headings


def test_txt_keeps_text(tmp_path):
    parsed = _parse(tmp_path, "notes.txt", "Line one.\n\nLine two.\n")
    assert parsed.text == "Line one.\n\nLine two.\n"
    assert parsed.source_id == "90"


def test_adapter_unifies_line_endings_and_drops_a_bom_from_the_converter_output(tmp_path, monkeypatch):
    """MarkItDown's own converters already emit LF and drop a BOM, so the adapter's own handling is tested with a stub."""

    class Stub:
        def convert(self, stream, info):
            return type("Result", (), {"markdown": "\ufeffa\r\nb\rc", "title": None})()

    parser = MarkItDownParser()
    monkeypatch.setattr(parser, "_converter", lambda extension: Stub())
    path = tmp_path / "notes.txt"
    path.write_text("ignored", encoding="utf-8")
    assert parser.parse(Document("90", "notes", str(path))).text == "a\nb\nc\n"


def test_utf8_bom_does_not_hide_the_first_heading(tmp_path):
    parsed = _parse(tmp_path, "notes.txt", "\ufeff# Title\n\nBody\n")
    assert [s.heading_path for s in parsed.sections] == [("Title",)]


def test_title_whitespace_is_collapsed(tmp_path):
    parsed = _parse(tmp_path, "guide.html", HTML.replace("<title>Retry guide</title>", "<title>  Retry\n guide </title>"))
    assert parsed.document_name == "Retry guide"


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for name, data in files.items():
            package.writestr(name, data)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "name, data",
    [
        ("broken.docx", b"not a zip file"),
        ("readme.docx", _zip({"readme.txt": "a zip, but not a Word document"})),
        ("broken.pdf", b"not a real document"),
        ("header-only.pdf", b"%PDF-1.4\n"),
    ],
)
def test_damaged_or_mismatched_file_raises_instead_of_being_read_as_text(tmp_path, name, data):
    """MarkItDown's front end would return these as plain text; the adapter must fail loudly."""
    with pytest.raises(DocumentParseError, match="#91"):
        _parse(tmp_path, name, data, source_id="91")


@pytest.mark.parametrize(
    "name, data",
    [("empty.txt", b""), ("empty.html", b"<html><body></body></html>"), ("scan.pdf", _pdf([])), ("empty.docx", _docx([]))],
)
def test_document_without_text_raises_instead_of_vanishing(tmp_path, name, data):
    with pytest.raises(DocumentParseError, match="#92.*no text extracted"):
        _parse(tmp_path, name, data, source_id="92")


def test_missing_file_and_directory_get_their_own_message(tmp_path):
    parser = MarkItDownParser()
    with pytest.raises(DocumentParseError, match="#93.*file not found"):
        parser.parse(Document("93", "missing", str(tmp_path / "missing.docx")))
    (tmp_path / "folder.pdf").mkdir()
    with pytest.raises(DocumentParseError, match="#93.*not a file"):
        parser.parse(Document("93", "folder", str(tmp_path / "folder.pdf")))


@pytest.mark.parametrize("arm", ["A", "B"])
def test_converted_formats_chunk_like_the_same_markdown(tmp_path, arm):
    """Format independence: HTML and DOCX give the same chunks as the equivalent Markdown file."""
    chunker = load_arm(CHUNKING_CONFIG, arm)
    markdown = MarkdownParser().parse(_write(tmp_path, "guide.md", EXPECTED_MARKDOWN))
    markdown = replace(markdown, sections=section_spans(markdown.text))
    expected = [(c.heading_path, c.display_text, c.location_type) for c in chunker.chunk(markdown)]
    assert expected and expected[0][0] == ("Retry policy",)
    for name, data in (("guide.html", HTML), ("guide.docx", _docx(SECTIONS))):
        parsed = _parse(tmp_path, name, data)
        chunks = chunker.chunk(parsed)
        assert [(c.heading_path, c.display_text, c.location_type) for c in chunks] == expected, name
        assert all(parsed.text[c.char_start : c.char_end] == c.display_text for c in chunks)


def test_markitdown_is_imported_lazily():
    """Building the registry (as the Markdown-only corpus scripts do) must not import MarkItDown."""
    code = (
        "import sys; from knowledge_assistant.infrastructure.parsing.registry import default_registry; "
        "default_registry(); print('markitdown' in sys.modules)"
    )
    # This checkout's src first: an editable install may point at another checkout (INGEST-003 verify, B1).
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=ROOT, env=env)
    assert result.stdout.strip() == "False"


def _write(tmp_path: Path, name: str, text: str) -> Document:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return Document("90", path.stem, str(path))

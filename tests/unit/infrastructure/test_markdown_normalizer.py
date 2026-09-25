"""INGEST-001: Markdown parser + ADR-0003 D1 normalizer (offline)."""
from pathlib import Path

import pytest

from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import MarkdownNormalizer, content_sha256
from knowledge_assistant.infrastructure.parsing.markdown_parser import MarkdownParser
from knowledge_assistant.infrastructure.parsing.registry import default_registry

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "corpus" / "sources"

PAGE = """# Some page - C# | Microsoft Learn

Source: https://learn.microsoft.com/en-us/some/page

---

---

Note

Access to this page requires authorization. You can try [signing in](#) or changing directories.

Access to this page requires authorization. You can try changing directories.

# Some page

By [Jane Doe](https://example.com), and [John Roe](https://example.org)

Note

This isn't the latest version of this article. For the current release, see the [.NET 10 version of this article](?view=aspnetcore-10.0).

Warning

This version of ASP.NET Core is no longer supported. For more information, see the [policy](https://dotnet.microsoft.com).

Intro text.



Note

A real note that stays.

## Section

```text
By [Kept](https://example.com) inside code
- Last updated on
```

---

## Additional resources

---

- Last updated on
  2026-09-22
"""


def _normalize(text: str, source_id: str = "99") -> ParsedDocument:
    return MarkdownNormalizer().normalize(ParsedDocument(Document(source_id, "name"), text))


def test_crlf_is_converted_first_and_gives_the_same_result_as_lf():
    lf = _normalize(PAGE)
    crlf = _normalize(PAGE.replace("\n", "\r\n"))
    assert "\r" not in crlf.text
    assert crlf.text == lf.text
    assert crlf.sections == lf.sections
    assert content_sha256(crlf.text) == content_sha256(lf.text)


def test_wrapper_moves_to_metadata_and_is_removed_from_the_text():
    doc = _normalize(PAGE)
    assert doc.text.startswith("# Some page\n\nIntro text.\n")
    assert doc.wrapper_title == "Some page - C# | Microsoft Learn"
    assert doc.source_url == "https://learn.microsoft.com/en-us/some/page"
    assert doc.document_name == "Some page"
    assert "Source:" not in doc.text and "Microsoft Learn" not in doc.text
    assert doc.normalized


def test_boilerplate_lines_and_their_labels_are_removed():
    text = _normalize(PAGE).text
    for gone in ("requires authorization", "isn't the latest version", "no longer supported", "By [Jane Doe]",
                 "Warning", "2026-09-22"):
        assert gone not in text, gone
    assert "\n- Last updated on" not in text.split("```")[-1]
    assert text.endswith("## Additional resources\n")  # the footer rule before "Last updated" goes too
    assert "Note\n\nA real note that stays." in text
    assert text.count("\nNote\n") == 1


def test_code_fences_are_left_untouched():
    text = _normalize(PAGE).text
    assert "```text\nBy [Kept](https://example.com) inside code\n- Last updated on\n```" in text


def test_blank_line_runs_collapse_to_one():
    assert "\n\n\n" not in _normalize(PAGE).text


def test_yaml_front_matter_of_29_is_removed():
    source = next(SOURCES.glob("29-*.md"))
    doc = MarkdownNormalizer().normalize(MarkdownParser().parse(Document("29", "asp0033", str(source))))
    assert doc.text.startswith("# ASP0033: `[ValidatableType]` is applied to an inaccessible type\n")
    for key in ("title:", "author:", "monikerRange:", "ms.date:", "uid:"):
        assert key not in doc.text, key
    assert doc.source_url == "https://github.com/dotnet/AspNetCore.Docs/blob/main/aspnetcore/diagnostics/asp0033.md"


def test_unknown_preamble_line_raises_instead_of_being_dropped():
    page = PAGE.replace("Source: https://learn.microsoft.com/en-us/some/page", "Source: x\n\nSome real content")
    with pytest.raises(DocumentParseError, match="unexpected preamble line"):
        _normalize(page)


def test_missing_page_h1_raises():
    with pytest.raises(DocumentParseError):
        _normalize("# Only a wrapper\n\nSource: x\n\ntext\n")


def test_version_variants_are_kept_and_numbered():
    page = PAGE.replace("## Section", "## Section\n\nv1\n\n## Section")
    doc = _normalize(page)
    repeated = [s for s in doc.sections if s.heading_path == ("Some page", "Section")]
    assert [(s.variant, s.variant_count) for s in repeated] == [(1, 2), (2, 2)]
    for span in doc.sections:
        assert doc.text[span.char_start : span.char_end].startswith("#" * span.level + " ")


def test_parser_keeps_raw_line_endings_and_the_registry_selects_it(tmp_path):
    path = tmp_path / "doc.md"
    path.write_bytes(b"# a\r\n")
    parser = default_registry().get(".MD")
    assert isinstance(parser, MarkdownParser)
    assert parser.parse(Document("01", "a", str(path))).text == "# a\r\n"


def test_parser_raises_a_clear_error_for_unreadable_files(tmp_path):
    with pytest.raises(DocumentParseError, match="#07"):
        MarkdownParser().parse(Document("07", "missing", str(tmp_path / "missing.md")))

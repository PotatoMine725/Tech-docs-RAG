"""NFC at ingestion (owner decision 2026-11-25, ADR-0008). Synthetic text only."""
import unicodedata

from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans
from knowledge_assistant.infrastructure.parsing.nfc_normalizer import NfcNormalizer

COMPOSED = "# Hoàn cảnh quốc tế\n\nViêm gan B mạn tính.\n\n## Điều trị\n\nThuốc kháng virus.\n"


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(Document("C2-99", "t", "x.md"), text, sections=section_spans(text))


def test_decomposed_text_is_composed_and_sections_recomputed():
    decomposed = _doc(unicodedata.normalize("NFD", COMPOSED))
    assert len(decomposed.text) > len(COMPOSED)
    result = NfcNormalizer().normalize(decomposed)
    assert result.text == COMPOSED
    assert result.sections == section_spans(COMPOSED)
    second = result.sections[1]
    assert result.text[second.char_start:].startswith("## Điều trị")


def test_text_already_in_nfc_comes_back_as_the_same_object():
    document = _doc(COMPOSED)
    assert NfcNormalizer().normalize(document) is document


def test_inner_normalizer_runs_first():
    class Upper:
        def normalize(self, document):
            return ParsedDocument(document.document, unicodedata.normalize("NFD", document.text.upper()))

    result = NfcNormalizer(Upper()).normalize(_doc(COMPOSED))
    assert result.text == COMPOSED.upper()

"""Unicode NFC at ingestion (owner decision 2026-11-25, ADR-0008).

Some corpus-2 documents are stored decomposed (NFD: C2-07, C2-08, C2-25) while questions are typed composed (NFC),
so keyword search and quote matching missed. `NfcNormalizer` runs after any other normalizer and composes the text;
the section spans are recomputed on the composed text because composing shortens it. Text already in NFC (all of
corpus 1) comes back unchanged, the same object.
"""
import unicodedata
from dataclasses import replace

from knowledge_assistant.core.interfaces.normalizer import DocumentNormalizer
from knowledge_assistant.core.models import ParsedDocument
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans


def to_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


class NfcNormalizer:
    """`inner` (e.g. the corpus-1 MarkdownNormalizer) runs first; None = the parser output as it is (corpus 2)."""

    def __init__(self, inner: DocumentNormalizer | None = None) -> None:
        self._inner = inner

    def normalize(self, document: ParsedDocument) -> ParsedDocument:
        if self._inner is not None:
            document = self._inner.normalize(document)
        if unicodedata.is_normalized("NFC", document.text):
            return document
        text = to_nfc(document.text)
        return replace(document, text=text, sections=section_spans(text))

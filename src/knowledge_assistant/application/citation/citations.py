"""Citation markers and citation building (RAG-002, citation-spec.md). Pure functions.

Passages are numbered 1..k in rank order in the prompt; the answer cites them with markers like [2] or [2][3].
"""
import re

from knowledge_assistant.application.common.passage import passage_body
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, Citation, RetrievedChunk

EXCERPT_CHARS = 300
MIN_WORDS_FOR_FACT = 5  # shorter sentences are not counted by `count_uncited_sentences`

_MARKER = re.compile(r"\[(\d+)\]")
_MARKER_WITH_SPACE = re.compile(r"[ \t]*\[(\d+)\]")
# A sentence ends at . ! or ? (plus any markers right after it) before whitespace or the end, or at a line break.
_SENTENCE_END = re.compile(r"[.!?]+(?:[ \t]*\[\d+\])*(?=\s|$)|\n+")
_WORD = re.compile(r"\w+")


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    """The first `limit` characters, cut back to the last word boundary. A verbatim prefix of the text (no ellipsis
    added), so it can be found in the chunk."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if not text[limit].isspace():
        space = max(cut.rfind(" "), cut.rfind("\n"))
        if space > 0:
            cut = cut[:space]
    return cut.rstrip()


def extract_markers(answer: str) -> list[int]:
    """Marker numbers in order of first appearance, without repeats."""
    return list(dict.fromkeys(int(match) for match in _MARKER.findall(answer)))


def remove_markers(answer: str, markers: set[int]) -> str:
    """The answer without the given markers (and the spaces before them)."""
    return _MARKER_WITH_SPACE.sub(lambda m: "" if int(m.group(1)) in markers else m.group(0), answer)


def split_sentences(text: str) -> list[str]:
    sentences, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        sentences.append(text[start : match.end()])
        start = match.end()
    sentences.append(text[start:])
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def count_uncited_sentences(answer: str) -> int:
    """Diagnostic: sentences of at least MIN_WORDS_FOR_FACT words (markers not counted) without any marker."""
    count = 0
    for sentence in split_sentences(answer):
        if _MARKER.search(sentence):
            continue
        if len(_WORD.findall(_MARKER.sub("", sentence))) >= MIN_WORDS_FOR_FACT:
            count += 1
    return count


def build_citation(hit: RetrievedChunk, marker: int) -> Citation:
    chunk = hit.chunk
    return Citation(
        source_id=chunk.source_id,
        document_name=chunk.document_name,
        location=HEADING_PATH_SEPARATOR.join(chunk.heading_path),
        excerpt=excerpt(passage_body(chunk)),
        chunk_id=chunk.chunk_id,
        marker=marker,
        source_url=chunk.source_url or "",
        location_type=chunk.location_type,
    )


def resolve_citations(
    answer: str, cited_passages: list[int], retrieved: tuple[RetrievedChunk, ...]
) -> tuple[str, tuple[Citation, ...], tuple[int, ...]]:
    """(answer without out-of-range markers, citations, dropped marker numbers).

    Citations follow the first marker in the answer, then any `cited_passages` not marked in the text. A number
    outside 1..k (k = len(retrieved)) is dropped from the text and recorded, whether it came from a marker or from
    `cited_passages`.
    """
    k = len(retrieved)
    order = list(dict.fromkeys(extract_markers(answer) + list(cited_passages)))
    dropped = tuple(n for n in order if not 1 <= n <= k)
    kept = [n for n in order if 1 <= n <= k]
    cleaned = remove_markers(answer, set(dropped)) if dropped else answer
    return cleaned, tuple(build_citation(retrieved[n - 1], n) for n in kept), dropped

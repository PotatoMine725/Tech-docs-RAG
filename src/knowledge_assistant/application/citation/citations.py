"""Citation markers and citation building (RAG-002, citation-spec.md). Pure functions.

Passages are numbered 1..k in rank order in the prompt; the answer cites them with markers like [2] or [2][3].
A `[n]` is a marker only outside code (inline backtick spans and fenced ``` / ~~~ blocks) and only for n >= 1;
anything else (e.g. `args[0]`, a C# indexer in a code block, prose "[0]") is plain text: left byte-identical and
never recorded (RAG-002 fix F1, owner decision).
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
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
_NOT_A_MARKER = "\x00"  # replaces the "[" of a non-marker `[n]`, inside `count_uncited_sentences` only


def _code_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) offsets of fenced code blocks (fence lines included; an unclosed fence runs to the end) and of
    inline backtick spans outside them (a backtick run closed by a run of the same length)."""
    spans: list[tuple[int, int]] = []
    prose: list[tuple[int, int]] = []  # regions outside fences, searched for inline code
    offset, prose_start, fence = 0, 0, None  # fence = (char, length, start offset) while inside a block
    for line in text.splitlines(keepends=True):
        if fence is None:
            opening = _FENCE_OPEN.match(line)
            if opening:
                prose.append((prose_start, offset))
                fence = (opening.group(1)[0], len(opening.group(1)), offset)
        else:
            char, length, start = fence
            if re.fullmatch(" {0,3}" + re.escape(char) + "{%d,}[ \t]*\r?\n?" % length, line):
                spans.append((start, offset + len(line)))
                fence, prose_start = None, offset + len(line)
        offset += len(line)
    if fence is not None:
        spans.append((fence[2], len(text)))
    else:
        prose.append((prose_start, len(text)))
    for start, end in prose:
        spans.extend((start + m.start(), start + m.end()) for m in _INLINE_CODE.finditer(text[start:end]))
    return spans


def _is_marker(bracket: int, number: str, code: list[tuple[int, int]]) -> bool:
    """True if the `[number]` whose "[" is at offset `bracket` is a citation marker: n >= 1 and outside code."""
    return int(number) >= 1 and not any(start <= bracket < end for start, end in code)


def _marker_matches(text: str, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    """Matches of `pattern` (group 1 = the number) that are citation markers."""
    code = _code_spans(text)
    return [m for m in pattern.finditer(text) if _is_marker(m.start(1) - 1, m.group(1), code)]


def _mask_non_markers(text: str) -> str:
    """The text with the "[" of every non-marker `[n]` replaced, so `_MARKER` finds only real markers. Same length."""
    code = _code_spans(text)
    chars = list(text)
    for m in _MARKER.finditer(text):
        if not _is_marker(m.start(), m.group(1), code):
            chars[m.start()] = _NOT_A_MARKER
    return "".join(chars)


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
    """Marker numbers (outside code, n >= 1) in order of first appearance, without repeats."""
    return list(dict.fromkeys(int(m.group(1)) for m in _marker_matches(answer, _MARKER)))


def remove_markers(answer: str, markers: set[int]) -> str:
    """The answer without the given markers (and the spaces before them). A `[n]` inside code and `[0]` are not
    markers and stay byte-identical."""
    for m in reversed([m for m in _marker_matches(answer, _MARKER_WITH_SPACE) if int(m.group(1)) in markers]):
        answer = answer[: m.start()] + answer[m.end() :]
    return answer


def split_sentences(text: str) -> list[str]:
    sentences, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        sentences.append(text[start : match.end()])
        start = match.end()
    sentences.append(text[start:])
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def count_uncited_sentences(answer: str) -> int:
    """Diagnostic: sentences of at least MIN_WORDS_FOR_FACT words (markers not counted) without any marker. A `[n]`
    inside code or `[0]` is not a marker, so a sentence whose only `[n]` is in code counts as uncited."""
    count = 0
    for sentence in split_sentences(_mask_non_markers(answer)):
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

from knowledge_assistant.application.citation.citations import (
    count_uncited_sentences,
    excerpt,
    extract_markers,
    resolve_citations,
    split_sentences,
)
from knowledge_assistant.application.common.passage import passage_body, passage_hash
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import make_chunk


def _retrieved(k=5):
    return tuple(
        RetrievedChunk(make_chunk(f"{i:02d}", i, f"Body of passage {i}.", ("Doc", f"Part {i}")), i, 1 - i / 10)
        for i in range(1, k + 1)
    )


def test_markers_in_first_appearance_order():
    assert extract_markers("A [2]. B [3][2]. C [10].") == [2, 3, 10]


def test_out_of_range_marker_is_dropped_from_text_and_recorded():
    answer, citations, dropped = resolve_citations("Fact one [2]. Fact two [7].", [], _retrieved(5))
    assert answer == "Fact one [2]. Fact two."
    assert dropped == (7,)
    assert [c.marker for c in citations] == [2]


def test_marker_two_cites_rank_two_with_heading_path_and_excerpt():
    retrieved = _retrieved(5)
    _, citations, _ = resolve_citations("Fact [2].", [], retrieved)
    [citation] = citations
    assert citation.chunk_id == retrieved[1].chunk.chunk_id
    assert citation.source_id == "02"
    assert citation.location == "Doc > Part 2"
    assert citation.location_type == "heading"
    assert citation.excerpt == "Body of passage 2."
    assert citation.source_url == "https://example.invalid/02"


def test_citations_follow_answer_order_then_cited_passages():
    _, citations, dropped = resolve_citations("X [3]. Y [1].", [1, 4, 0, 3], _retrieved(5))
    assert [c.marker for c in citations] == [3, 1, 4]
    assert dropped == (0,)


def test_passage_body_strips_the_contextual_heading_line():
    chunk = make_chunk(text="Body [link text] here.", heading_path=("Doc", "Sec"))
    assert chunk.embed_text.startswith("Doc > Sec\n\n")
    assert passage_body(chunk) == "Body [link text] here."


def test_excerpt_cuts_at_a_word_boundary_and_stays_a_prefix():
    text = "word " * 100
    cut = excerpt(text, 23)
    assert cut == "word word word word"
    assert text.startswith(cut)
    assert excerpt("short text", 300) == "short text"
    assert excerpt("abcdefghij klm", 12) == "abcdefghij"


def test_sentence_split_keeps_trailing_markers_with_their_sentence():
    assert split_sentences("One fact here. [1] Two facts here [2]. Three") == [
        "One fact here. [1]", "Two facts here [2].", "Three"]
    assert split_sentences("Uses System.Text.Json today [1].") == ["Uses System.Text.Json today [1]."]


def test_uncited_sentences_counts_long_sentences_without_markers():
    answer = "This long sentence has no marker at all. This one is cited properly here [1]. Too short.\n- a list item"
    assert count_uncited_sentences(answer) == 1


def test_passage_hash_ignores_the_heading_line_but_not_the_body():
    assert passage_hash(make_chunk("01", 0, "Same body.", ("A",))) == passage_hash(make_chunk("02", 0, "Same body.", ("B",)))
    assert passage_hash(make_chunk("01", 0, "Body one.")) != passage_hash(make_chunk("01", 0, "Body two."))

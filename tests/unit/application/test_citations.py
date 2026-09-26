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


# RAG-002 fix F1: `[n]` inside code and `[0]` are not markers (citation-spec.md, owner decision 2026-09-26).
PROBE = "Use `args[0]` and `values[7]` like this [1].\n```csharp\nvar x = items[2];\n```"


def test_verifier_probe_code_indexers_are_not_markers():
    answer, citations, dropped = resolve_citations(PROBE, [1], _retrieved(5))
    assert answer == PROBE
    assert [c.marker for c in citations] == [1]
    assert dropped == ()


def test_inline_code_zero_index_is_left_alone():
    text = "Read `args[0]` first [1]."
    assert extract_markers(text) == [1]
    assert resolve_citations(text, [], _retrieved(5))[0] == text


def test_inline_code_out_of_range_index_is_not_dropped():
    text = "Then `values[7]` holds it [2]."
    answer, citations, dropped = resolve_citations(text, [], _retrieved(5))
    assert (answer, [c.marker for c in citations], dropped) == (text, [2], ())


def test_fenced_code_index_does_not_invent_a_citation():
    for fence in ("```", "~~~"):
        text = f"Example [1].\n{fence}csharp\nvar x = items[2];\nvar y = items[9];\n{fence}\nDone [3]."
        answer, citations, dropped = resolve_citations(text, [], _retrieved(5))
        assert (answer, [c.marker for c in citations], dropped) == (text, [1, 3], ())


def test_unclosed_fence_runs_to_the_end():
    text = "Example [1].\n```\nvar x = items[2];"
    assert extract_markers(text) == [1]


def test_zero_in_plain_text_is_not_a_marker_and_not_dropped():
    text = "Index [0] is the first slot [1]."
    answer, citations, dropped = resolve_citations(text, [], _retrieved(5))
    assert (answer, [c.marker for c in citations], dropped) == (text, [1], ())
    assert extract_markers(text) == [1]


def test_zero_in_cited_passages_is_dropped_but_prose_zero_stays():
    text = "Index [0] is the first slot [1]."
    answer, _, dropped = resolve_citations(text, [0], _retrieved(5))
    assert answer == text and dropped == (0,)


def test_marker_directly_after_a_word_is_still_a_marker():
    assert extract_markers("The class is sealed[2].") == [2]
    assert resolve_citations("The class is sealed[7].", [], _retrieved(5))[0] == "The class is sealed."


def test_marker_right_after_a_closing_backtick_is_a_marker():
    assert extract_markers("Call `x`[1].") == [1]
    assert extract_markers("Call ``a ` b``[2] and `y[3]`.") == [2]


def test_regression_marker_order_and_prose_out_of_range_drop():
    assert extract_markers("A [2][3]. B. [1]") == [2, 3, 1]
    answer, _, dropped = resolve_citations("Fact [7] here.", [], _retrieved(5))
    assert answer == "Fact here." and dropped == (7,)


def test_sentence_whose_only_bracket_is_in_code_counts_as_uncited():
    assert count_uncited_sentences("Always read the value through `args[1]` safely.") == 1
    assert count_uncited_sentences("Always read the value through args safely [1].") == 0
    assert count_uncited_sentences("The first slot is at index [0] in C#.") == 1

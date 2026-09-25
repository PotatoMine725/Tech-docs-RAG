"""INGEST-002: both chunkers on small hand-made Markdown (ADR-0003 D2-D6)."""
import re
from pathlib import Path

import pytest

from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.chunking.chunk_builder import build_chunks, Span
from knowledge_assistant.infrastructure.chunking.factory import load_arm
from knowledge_assistant.infrastructure.chunking.fixed_size import FixedSizeChunker, FixedSizeConfig
from knowledge_assistant.infrastructure.chunking.header_aware import HeaderAwareChunker, HeaderAwareConfig
from knowledge_assistant.infrastructure.chunking.markdown_structure import fenced_ranges
from knowledge_assistant.infrastructure.chunking.stats import chunk_stats, cuts_code_fence
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans

ROOT = Path(__file__).resolve().parents[3]
ARM_A = HeaderAwareConfig("header-1600", max_chars=1600, min_chars=400, overlap_chars=200, drop_heading_only=True)
ARM_A_KEEP_HEADINGS = HeaderAwareConfig("header-1600", max_chars=1600, min_chars=400, overlap_chars=200)
ARM_B = FixedSizeConfig("fixed-1600", size_chars=1600, overlap_chars=200)


def _doc(text: str, source_id: str = "01") -> ParsedDocument:
    return ParsedDocument(
        document=Document(source_id, "Page"),
        text=text,
        document_name="Page",
        source_url="https://example.test/page",
        sections=section_spans(text),
        normalized=True,
    )


def _para(words: int, seed: str = "word") -> str:
    return " ".join(f"{seed}{i}." if i % 12 == 11 else f"{seed}{i}" for i in range(words))


def _chunks_a(text: str, path: tuple[str, ...] | None = None):
    chunks = HeaderAwareChunker(ARM_A).chunk(_doc(text))
    return [c for c in chunks if path is None or c.heading_path == path]


# --- Arm A: sections, merging, heading paths --------------------------------------------------------------------


def test_small_section_merges_with_next_sibling_and_keeps_first_heading_path():
    text = f"# Page\n\n{_para(80)}\n\n## Small\n\nshort text\n\n## Next\n\n{_para(40)}\n"
    chunks = _chunks_a(text)
    merged = [c for c in chunks if "## Small" in c.display_text]
    assert len(merged) == 1 and "## Next" in merged[0].display_text
    assert merged[0].heading_path == ("Page", "Small")


def test_small_section_does_not_merge_into_its_child_or_a_different_parent():
    text = f"# Page\n\n{_para(80)}\n\n## Parent\n\nintro\n\n### Child\n\n{_para(80)}\n\n## Other\n\n{_para(80)}\n"
    paths = [c.heading_path for c in _chunks_a(text)]
    assert paths == [("Page",), ("Page", "Parent"), ("Page", "Parent", "Child"), ("Page", "Other")]


def test_small_sections_do_not_merge_beyond_max():
    text = f"# Page\n\n{_para(80)}\n\n## Small\n\nshort\n\n## Big\n\n{_para(260)}\n"
    assert any(c.display_text == "## Small\n\nshort" for c in _chunks_a(text))


def test_h4_stays_inside_its_h3_section():
    text = f"# Page\n\n{_para(80)}\n\n## A\n\n### B\n\n{_para(40)}\n\n#### Deep\n\n{_para(40)}\n"
    deep = [c for c in _chunks_a(text) if "#### Deep" in c.display_text]
    assert [c.heading_path for c in deep] == [("Page", "A", "B")]


# --- Arm A: heading-only chunks (ADR-0003 D3a) ---------------------------------------------------------------------


def test_heading_only_chunk_of_an_h2_followed_by_its_h3_is_dropped():
    text = f"# Page\n\n{_para(80)}\n\n## Parent\n\n### Child\n\n{_para(80)}\n"
    kept = HeaderAwareChunker(ARM_A_KEEP_HEADINGS).chunk(_doc(text))
    assert [c.display_text for c in kept if c.heading_path == ("Page", "Parent")] == ["## Parent"]
    dropped = HeaderAwareChunker(ARM_A).chunk(_doc(text))
    assert [c.heading_path for c in dropped] == [("Page",), ("Page", "Parent", "Child")]


def test_sibling_headings_without_body_are_dropped_together():
    text = f"# Page\n\n{_para(80)}\n\n## A\n\n## B\n\n### B1\n\n{_para(80)}\n"
    assert [c.display_text for c in _chunks_a(text, ("Page", "A"))] == []
    assert [c.display_text for c in HeaderAwareChunker(ARM_A_KEEP_HEADINGS).chunk(_doc(text))][1] == "## A\n\n## B"


def test_heading_with_body_is_kept():
    text = f"# Page\n\n{_para(80)}\n\n## Parent\n\nOne short line of body.\n\n### Child\n\n{_para(80)}\n"
    kept = [c.display_text for c in _chunks_a(text, ("Page", "Parent"))]
    assert kept == ["## Parent\n\nOne short line of body."]


def test_hash_lines_inside_a_code_fence_are_body_not_headings():
    text = f"# Page\n\n{_para(80)}\n\n## Script\n\n```bash\n# install\n# run\n```\n\n### Next\n\n{_para(80)}\n"
    kept = [c.display_text for c in _chunks_a(text, ("Page", "Script"))]
    assert kept == ["## Script\n\n```bash\n# install\n# run\n```"]


def test_a_split_code_piece_of_only_hash_comment_lines_is_kept():
    body = "\n".join(
        [f"echo step {i:03d}" for i in range(100)] + [f"# note {i:03d}" for i in range(400)] + ["echo done"]
    )
    text = f"# Page\n\n{_para(80)}\n\n## Script\n\n```bash\n{body}\n```\n"
    chunks = _chunks_a(text, ("Page", "Script"))
    assert any(all(line.startswith("# note") for line in c.display_text.split("\n")) for c in chunks)
    assert {f"# note {i:03d}" for i in range(400)} <= {line for c in chunks for line in c.display_text.split("\n")}


def test_ids_stay_deterministic_and_contiguous_after_heading_only_drops():
    text = f"# Page\n\n{_para(80)}\n\n## A\n\n### A1\n\n{_para(80)}\n\n## B\n\n### B1\n\n{_para(80)}\n"
    runs = [HeaderAwareChunker(ARM_A).chunk(_doc(text, "07")) for _ in range(2)]
    ids = [c.chunk_id for c in runs[0]]
    assert ids == [c.chunk_id for c in runs[1]] == [f"07:header-1600:{i:04d}" for i in range(len(ids))]
    assert len(ids) == len(HeaderAwareChunker(ARM_A_KEEP_HEADINGS).chunk(_doc(text, "07"))) - 2


def test_every_heading_path_is_a_section_of_the_document():
    text = f"# Page\n\n{_para(300)}\n\n## A\n\n{_para(300)}\n\n### B\n\n{_para(50)}\n"
    document = _doc(text)
    known = {section.heading_path for section in document.sections}
    assert {c.heading_path for c in HeaderAwareChunker(ARM_A).chunk(document)} <= known


# --- Arm A: size limits, atomic blocks, overlap --------------------------------------------------------------------


def test_oversized_section_splits_within_max_at_paragraph_or_sentence_boundaries():
    paragraphs = "\n\n".join(_para(60, f"p{n}w") for n in range(8))
    chunks = _chunks_a(f"# Page\n\n## Long\n\n{paragraphs}\n")
    long_pieces = [c for c in chunks if c.heading_path == ("Page", "Long")]
    assert len(long_pieces) > 1 and len(chunks) == len(long_pieces)  # the bodiless "# Page" section is dropped (D3a)
    assert all(len(c.display_text) <= 1600 for c in chunks)
    assert all(c.display_text.endswith(".") for c in long_pieces)  # paragraph ends


def test_a_single_long_paragraph_is_split_at_sentence_ends():
    chunks = _chunks_a(f"# Page\n\n## Long\n\n{_para(700)}\n", ("Page", "Long"))
    assert len(chunks) > 1 and all(len(c.display_text) <= 1600 for c in chunks)
    assert all(c.display_text.rstrip().endswith(".") for c in chunks[:-1])


def test_code_block_up_to_max_is_never_cut():
    code = "```csharp\n" + "\n".join(f"var value{i} = Compute({i});" for i in range(56)) + "\n```"
    assert 1400 < len(code) <= 1600  # longer than max - overlap: only atomicity keeps it whole
    text = f"# Page\n\n## Code\n\n{_para(150)}\n\n{code}\n\n{_para(150)}\n"
    document = _doc(text)
    fences = fenced_ranges(text)
    chunks = HeaderAwareChunker(ARM_A).chunk(document)
    assert not any(cuts_code_fence(c, fences) for c in chunks)
    assert any(code in c.display_text for c in chunks)


def test_code_block_over_max_is_split_by_whole_lines():
    lines = [f"Console.WriteLine({i});" for i in range(120)]
    text = "# Page\n\n## Code\n\n```csharp\n" + "\n".join(lines) + "\n```\n"
    chunks = _chunks_a(text, ("Page", "Code"))
    assert len(chunks) > 1 and all(len(c.display_text) <= 1600 for c in chunks)
    for chunk in chunks:
        body = [line for line in chunk.display_text.split("\n") if line.startswith("Console")]
        assert all(line in lines for line in body)  # never a partial line


def test_table_over_max_is_split_by_rows_with_header_repeated_in_embed_text_only():
    header = "| Name | Value |\n|---|---|"
    rows = [f"| row{i} | {'v' * 40} |" for i in range(60)]
    text = f"# Page\n\n## Table\n\n{header}\n" + "\n".join(rows) + "\n"
    chunks = _chunks_a(text, ("Page", "Table"))
    assert len(chunks) > 1 and all(len(c.display_text) <= 1600 for c in chunks)
    assert chunks[0].display_text.startswith(f"## Table\n\n{header}")
    assert chunks[1].display_text.startswith("| row")  # overlap starts at a row, not inside one
    assert chunks[1].embed_text.count("| Name | Value |") == 1
    assert "| Name | Value |" not in chunks[1].display_text
    for chunk in chunks:
        assert all(line in rows or line in header.split("\n") for line in chunk.display_text.split("\n")[2:])


def test_table_up_to_max_stays_whole():
    table = "| A | B |\n|---|---|\n" + "\n".join(f"| a{i} | b{i} |" for i in range(40))
    text = f"# Page\n\n## T\n\n{_para(200)}\n\n{table}\n\n{_para(200)}\n"
    assert any(table in c.display_text for c in _chunks_a(text))


def test_overlap_only_between_pieces_of_one_split_section():
    text = f"# Page\n\n{_para(80)}\n\n## Long\n\n{_para(700)}\n\n## After\n\n{_para(100)}\n"
    chunks = _chunks_a(text)
    long_pieces = [c for c in chunks if c.heading_path == ("Page", "Long")]
    assert len(long_pieces) > 1
    for first, second in zip(long_pieces, long_pieces[1:]):
        assert 0 < first.char_end - second.char_start <= 200
    others = [c for c in chunks if c.heading_path != ("Page", "Long")]
    ordered = sorted(others + [long_pieces[0], long_pieces[-1]], key=lambda c: c.char_start)
    for first, second in zip(ordered, ordered[1:]):
        if first.heading_path != second.heading_path:
            assert first.char_end <= second.char_start


def test_overlap_never_starts_inside_a_code_fence():
    code = "```text\n" + "\n".join(f"line {i} of the listing" for i in range(55)) + "\n```"
    text = f"# Page\n\n## S\n\n{_para(200)}\n\n{code}\n\n{_para(200)}\n"
    document = _doc(text)
    fences = fenced_ranges(text)
    for chunk in HeaderAwareChunker(ARM_A).chunk(document):
        assert not any(start < chunk.char_start < end for start, end in fences)


# --- Arm B ---------------------------------------------------------------------------------------------------------


def test_fixed_size_windows_have_the_configured_size_and_overlap():
    text = "# Page\n\n" + _para(900) + "\n"
    chunks = FixedSizeChunker(ARM_B).chunk(_doc(text))
    assert len(chunks) > 2
    assert all(len(c.display_text) <= 1600 for c in chunks)
    assert all(len(c.display_text) >= 1590 for c in chunks[:-1])  # only whitespace is trimmed
    for first, second in zip(chunks, chunks[1:]):
        assert 190 <= first.char_end - second.char_start <= 200


def test_fixed_size_heading_path_is_the_nearest_heading_before_the_chunk_start():
    text = f"# Page\n\n{_para(200)}\n\n## Second\n\n{_para(400)}\n"
    document = _doc(text)
    second_start = text.index("## Second")
    for chunk in FixedSizeChunker(ARM_B).chunk(document):
        expected = ("Page", "Second") if chunk.char_start >= second_start else ("Page",)
        assert chunk.heading_path == expected


# --- both arms: D5/D6, duplicates, IDs -----------------------------------------------------------------------------


@pytest.mark.parametrize("chunker", [HeaderAwareChunker(ARM_A), FixedSizeChunker(ARM_B)])
def test_display_text_is_the_exact_slice_and_embed_text_has_heading_line_and_plain_links(chunker):
    text = f"# Page\n\n{_para(80)}\n\n## Links\n\nSee [the docs](https://x.test/a_(b)) and ![img](i.png).\n\n```md\n[keep](in-code)\n```\n\n{_para(80)}\n"
    document = _doc(text)
    for chunk in chunker.chunk(document):
        assert text[chunk.char_start : chunk.char_end] == chunk.display_text
        assert chunk.embed_text.split("\n")[0] == " > ".join(chunk.heading_path)
        assert chunk.location_type == "heading"
        assert chunk.content_hash == __import__("hashlib").sha256(chunk.display_text.encode()).hexdigest()
    joined = "\n".join(c.embed_text for c in chunker.chunk(document))
    assert "See the docs and img." in joined and "](https://" not in joined
    assert "[keep](in-code)" in joined  # links inside code fences are code, not links
    assert any("[the docs](https://x.test/a_(b))" in c.display_text for c in chunker.chunk(document))


@pytest.mark.parametrize("chunker", [HeaderAwareChunker(ARM_A), FixedSizeChunker(ARM_B)])
def test_ids_are_deterministic_and_follow_the_d6_pattern(chunker):
    text = f"# Page\n\n{_para(300)}\n\n## A\n\n{_para(500)}\n"
    first = [(c.chunk_id, c.content_hash) for c in chunker.chunk(_doc(text, "07"))]
    second = [(c.chunk_id, c.content_hash) for c in chunker.chunk(_doc(text, "07"))]
    assert first == second
    name = chunker.config.chunker_config
    assert [cid for cid, _ in first] == [f"07:{name}:{i:04d}" for i in range(len(first))]


def test_exact_duplicate_sections_are_dropped_per_document_and_counted():
    variant = f"## Setup\n\n{_para(90)}\n\n"
    text = f"# Page\n\n{_para(80)}\n\n{variant}{variant}## Other\n\n{_para(90)}\n"
    result = HeaderAwareChunker(ARM_A).chunk_with_report(_doc(text))
    assert result.duplicates_dropped == 1
    assert sum("## Setup" in c.display_text for c in result.chunks) == 1
    assert [c.chunk_id[-4:] for c in result.chunks] == [f"{i:04d}" for i in range(len(result.chunks))]


def test_chunker_config_with_a_colon_is_rejected():
    with pytest.raises(ValueError):
        build_chunks(_doc("# Page\n\ntext\n"), [Span(0, 6, ("Page",))], "bad:name")


def test_both_arms_emit_identical_field_sets():
    from dataclasses import fields

    text = f"# Page\n\n{_para(300)}\n"
    a = HeaderAwareChunker(ARM_A).chunk(_doc(text))[0]
    b = FixedSizeChunker(ARM_B).chunk(_doc(text))[0]
    assert type(a) is type(b)
    assert [f.name for f in fields(a)] == [f.name for f in fields(b)]


# --- stats and configuration ---------------------------------------------------------------------------------------


def test_code_fence_cut_detection():
    text = "# Page\n\nintro\n\n```\ncode\nmore\n```\n\nafter\n"
    document = _doc(text)
    fences = fenced_ranges(text)
    start, end = fences[0]
    whole = build_chunks(document, [Span(0, end, ("Page",))], "t").chunks[0]
    cut = build_chunks(document, [Span(0, start + 6, ("Page",))], "t").chunks[0]
    outside = build_chunks(document, [Span(0, start - 2, ("Page",))], "t").chunks[0]
    assert (cuts_code_fence(whole, fences), cuts_code_fence(cut, fences), cuts_code_fence(outside, fences)) == (
        False,
        True,
        False,
    )


def test_stats_report_counts_sizes_and_duplicates():
    documents = [_doc(f"# Page\n\n{_para(600)}\n", "01"), _doc("# Tiny\n\nsmall\n", "02")]
    chunker = FixedSizeChunker(ARM_B)
    stats = chunk_stats(documents, [chunker.chunk_with_report(d) for d in documents], "fixed-1600", 400)
    assert stats["documents"] == 2 and stats["documents_with_one_chunk"] == ["02"]
    assert stats["chunks_total"] == sum(stats["chunks_per_document"].values())
    assert stats["size_chars"]["min"] <= stats["size_chars"]["p50"] <= stats["size_chars"]["p90"] <= stats["size_chars"]["max"]
    assert stats["chunks_under_small_chunk_chars"] == 1


def test_arms_come_from_the_configuration_file():
    a, b = load_arm(ROOT / "config" / "chunking.json", "A"), load_arm(ROOT / "config" / "chunking.json", "B")
    assert (a.config.max_chars, a.config.min_chars, a.config.overlap_chars) == (1600, 400, 200)
    assert a.config.drop_heading_only is True  # ADR-0003 D3a, Arm A only
    assert (b.config.size_chars, b.config.overlap_chars) == (1600, 200)
    assert re.fullmatch(r"[^:]+", a.config.chunker_config) and a.config.chunker_config != b.config.chunker_config

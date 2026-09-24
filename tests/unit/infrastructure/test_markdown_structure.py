import pytest

from knowledge_assistant.infrastructure.chunking.markdown_structure import (
    find_headings,
    read_page_frame,
    split_sections,
)


def _lines(text: str) -> list[str]:
    return text.split("\n")


# --- find_headings -------------------------------------------------------


def test_heading_ending_in_csharp_keeps_the_hash():
    headings = find_headings(_lines("## What's new in C#"))
    assert [(h.level, h.text) for h in headings] == [(2, "What's new in C#")]


def test_closing_hash_sequence_after_a_space_is_removed():
    assert find_headings(_lines("## Title ##"))[0].text == "Title"


def test_hash_without_a_space_is_not_a_heading():
    assert find_headings(_lines("#hashtag")) == []


def test_four_space_indent_is_not_a_heading():
    assert find_headings(_lines("    ## indented code")) == []


def test_up_to_three_spaces_of_indent_is_a_heading():
    assert find_headings(_lines("   ### Indented"))[0].level == 3


def test_comment_lines_inside_a_code_fence_are_not_headings():
    text = "```bash\n# install the tool\n```\n## Real heading"
    headings = find_headings(_lines(text))
    assert [(h.text, h.line) for h in headings] == [("Real heading", 3)]


def test_fence_closes_only_with_the_same_character_and_enough_length():
    text = "````md\n```\n# still inside\n````\n~~~\n```\n# inside tilde\n~~~\n## After"
    assert [h.text for h in find_headings(_lines(text))] == ["After"]


def test_deep_heading_levels_are_reported():
    assert find_headings(_lines("#### Deep"))[0].level == 4


# --- split_sections ------------------------------------------------------


DOC = _lines(
    "# Page\n"  # 0
    "intro\n"  # 1
    "## Alpha\n"  # 2
    "a\n"  # 3
    "### Detail\n"  # 4
    "#### Deeper\n"  # 5
    "d\n"  # 6
    "## Beta\n"  # 7
    "### Only child\n"  # 8
    "b"  # 9
)


def test_sections_follow_h1_h2_h3_paths_and_h4_stays_inside_its_parent():
    sections = split_sections(DOC)
    assert [(s.heading_path, s.start_line, s.end_line) for s in sections] == [
        (("Page",), 0, 2),
        (("Page", "Alpha"), 2, 4),
        (("Page", "Alpha", "Detail"), 4, 7),
        (("Page", "Beta"), 7, 8),
        (("Page", "Beta", "Only child"), 8, 10),
    ]


def test_h3_without_an_h2_parent_hangs_off_the_h1():
    sections = split_sections(_lines("# Page\n### Orphan\nx"))
    assert sections[-1].heading_path == ("Page", "Orphan")


def test_headings_before_start_line_are_ignored():
    lines = _lines("# Wrapper\nSource: x\n# Page\n## Alpha")
    assert [s.heading_path for s in split_sections(lines, start_line=2)] == [
        ("Page",),
        ("Page", "Alpha"),
    ]


# --- read_page_frame -----------------------------------------------------


EXPORT = _lines(
    "# Routing in ASP.NET Core | Microsoft Learn\n"
    "\n"
    "Source: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/routing\n"
    "\n"
    "---\n"
    "\n"
    "# Routing in ASP.NET Core\n"
    "text"
)


def test_page_frame_reads_wrapper_title_source_url_and_page_h1():
    frame = read_page_frame(EXPORT)
    assert frame.wrapper_title == "Routing in ASP.NET Core | Microsoft Learn"
    assert frame.source_url == "https://learn.microsoft.com/en-us/aspnet/core/fundamentals/routing"
    assert frame.page_title == "Routing in ASP.NET Core"
    assert frame.page_title_line == 6


def test_page_frame_without_a_second_h1_is_an_error():
    with pytest.raises(ValueError):
        read_page_frame(_lines("# Only wrapper\nSource: x\n## Section"))

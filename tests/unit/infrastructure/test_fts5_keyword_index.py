"""FTS5 keyword index (ADR-0007): upsert/replace, delete by source, BM25 search, query building, settings check."""
import sqlite3

import pytest

from knowledge_assistant.core.exceptions import KeywordIndexError, VectorStoreError
from knowledge_assistant.infrastructure.keyword_index.fts5_index import (
    TOKENIZER,
    Fts5KeywordIndex,
    index_file_name,
    match_expression,
)
from tests.fakes import make_chunk


def _index(tmp_path, chunks=(), **kwargs):
    index = Fts5KeywordIndex(tmp_path, "header-1600", **kwargs)
    index.upsert(list(chunks))
    return index


def test_one_file_per_chunker_config(tmp_path):
    index = _index(tmp_path)
    assert index.path == tmp_path / "kw_header-1600.sqlite"
    assert index_file_name("fixed/1600 x") == "kw_fixed-1600-x.sqlite"


def test_search_ranks_by_bm25_and_returns_whole_chunks(tmp_path):
    chunks = [
        make_chunk("01", 0, "Dependency injection registers IHostedService with AddHostedService."),
        make_chunk("02", 0, "Kestrel is the web server."),
        make_chunk("03", 0, "IHostedService IHostedService runs background work."),
    ]
    index = _index(tmp_path, chunks)
    hits = index.search("How do I register an IHostedService?", 5)
    assert [hit.chunk.chunk_id for hit in hits][:2] == ["03:header-1600:0000", "01:header-1600:0000"]
    assert [hit.rank for hit in hits] == list(range(1, len(hits) + 1))
    assert hits[0].score > hits[1].score  # -bm25: higher = better
    assert hits[0].chunk == chunks[2]  # every field round-trips, heading_path as a tuple
    assert "02:header-1600:0000" not in [hit.chunk.chunk_id for hit in hits]


def test_question_words_are_ored_not_anded(tmp_path):
    index = _index(tmp_path, [make_chunk("01", 0, "Kestrel configuration")])
    assert [hit.chunk.source_id for hit in index.search("kestrel zzzunknownword", 5)] == ["01"]


@pytest.mark.parametrize("question", [
    'What is "Kestrel"?', "kestrel AND OR NOT", "kestrel: (x) * - ^ {y}", "NEAR(kestrel)", "kestrel's c# .net",
])
def test_fts5_syntax_in_the_question_never_raises(tmp_path, question):
    index = _index(tmp_path, [make_chunk("01", 0, "Kestrel configuration")])
    assert [hit.chunk.source_id for hit in index.search(question, 5)] == ["01"]


def test_no_word_token_gives_no_hits(tmp_path):
    index = _index(tmp_path, [make_chunk("01", 0, "Kestrel")])
    assert match_expression("?? -- _ !!") is None
    assert index.search("?? -- _ !!", 5) == []
    assert index.search("kestrel", 0) == []


def test_match_expression_quotes_distinct_casefolded_tokens():
    assert match_expression("Kestrel kestrel max_tokens?") == '"kestrel" OR "max_tokens"'


def test_snake_case_identifier_matches_as_a_phrase(tmp_path):
    index = _index(tmp_path, [make_chunk("01", 0, "Set max_tokens to 10."), make_chunk("02", 0, "tokens max")])
    assert [hit.chunk.source_id for hit in index.search("max_tokens", 5)] == ["01"]


def test_diacritics_are_kept_provisionally(tmp_path):
    """ADR-0007 D3 (PROVISIONAL): 'thể' matches 'thể' only, not 'the' or 'thế'; case is folded."""
    assert TOKENIZER == "unicode61 remove_diacritics 0"
    index = _index(tmp_path, [make_chunk("01", 0, "the model"), make_chunk("02", 0, "có thể"),
                              make_chunk("03", 0, "thế giới")])
    assert [hit.chunk.source_id for hit in index.search("Thể", 5)] == ["02"]
    assert [hit.chunk.source_id for hit in index.search("THE", 5)] == ["01"]


def test_upsert_replaces_by_chunk_id(tmp_path):
    index = _index(tmp_path, [make_chunk("01", 0, "old words")])
    index.upsert([make_chunk("01", 0, "new words")])
    assert index.count() == 1
    assert index.search("old", 5) == []
    assert [hit.chunk.embed_text for hit in index.search("new", 5)] == [make_chunk("01", 0, "new words").embed_text]


def test_delete_source_removes_only_that_document(tmp_path):
    index = _index(tmp_path, [make_chunk("01", 0, "a"), make_chunk("01", 1, "b"), make_chunk("02", 0, "c")])
    assert index.delete_source("01") == 2
    assert index.get_ids() == {"02:header-1600:0000"}
    assert index.delete_source("99") == 0


def test_chunk_of_another_config_is_refused(tmp_path):
    index = _index(tmp_path)
    with pytest.raises(KeywordIndexError):
        index.upsert([make_chunk("01", 0, "x", config="fixed-1600")])


def test_index_built_with_other_settings_is_refused_on_open(tmp_path):
    _index(tmp_path, [make_chunk("01", 0, "x")]).close()
    with pytest.raises(KeywordIndexError, match="tokenizer"):
        Fts5KeywordIndex(tmp_path, "header-1600", tokenizer="unicode61 remove_diacritics 2")
    connection = sqlite3.connect(tmp_path / "kw_header-1600.sqlite")
    with connection:
        connection.execute("UPDATE meta SET value = 'other' WHERE key = 'normalizer'")
    connection.close()
    with pytest.raises(VectorStoreError, match="normalizer"):  # a KeywordIndexError is a VectorStoreError
        Fts5KeywordIndex(tmp_path, "header-1600")


def test_read_only_open_of_a_missing_index_is_empty_and_creates_nothing(tmp_path):
    index = Fts5KeywordIndex(tmp_path / "none", "header-1600", create=False)
    assert not index.exists
    assert index.count() == 0 and index.get_ids() == set() and index.search("x", 5) == []
    assert not (tmp_path / "none").exists()
    with pytest.raises(KeywordIndexError):
        index.upsert([make_chunk()])


def test_reopened_index_keeps_its_rows(tmp_path):
    _index(tmp_path, [make_chunk("01", 0, "kestrel")]).close()
    reopened = Fts5KeywordIndex(tmp_path, "header-1600", create=False)
    assert reopened.exists and reopened.count() == 1

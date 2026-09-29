"""IndexCorpus with FakeEmbedder and a real Chroma store in tmp_path (offline)."""
import json

import pytest

from knowledge_assistant.application.ingestion.build_chunks import chunk_to_record, load_chunks
from knowledge_assistant.application.ingestion.index_corpus import IndexCorpus, chunker_config_of
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore
from tests.fakes import FakeEmbedder
from tests.unit.infrastructure.test_chroma_store import CONFIG, MODEL, five_chunks, make_chunk


def write_chunks(path, chunks):
    path.write_text("".join(json.dumps(chunk_to_record(c), ensure_ascii=False) + "\n" for c in chunks), encoding="utf-8")
    return path


def test_chunk_file_round_trip_keeps_every_field(tmp_path):
    chunks = five_chunks()  # includes a None source_url and an empty heading path
    assert load_chunks(write_chunks(tmp_path / "arm-a.jsonl", chunks)) == chunks


def test_index_then_search_finds_each_chunk(tmp_path):
    embedder = FakeEmbedder()
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    chunks = five_chunks()
    report = IndexCorpus(embedder, store).run(write_chunks(tmp_path / "arm-a.jsonl", chunks))
    assert (report.chunks_total, report.already_present, report.newly_embedded, report.store_count) == (5, 0, 5, 5)
    assert report.chunker_config == CONFIG and report.embedding_model_id == MODEL
    assert all(call[1] is EmbeddingTask.DOCUMENT for call in embedder.calls)
    assert store.search(embedder.vector(chunks[3].embed_text), 1)[0].chunk == chunks[3]


def test_resume_embeds_only_chunks_missing_from_the_store(tmp_path):
    """A bare FakeEmbedder (no cache), so only the store's get_ids can explain the skip."""
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    first = five_chunks()
    IndexCorpus(FakeEmbedder(), store).run(write_chunks(tmp_path / "arm-a.jsonl", first))

    embedder = FakeEmbedder()
    more = first + [make_chunk(i) for i in (5, 6, 7)]
    report = IndexCorpus(embedder, store).run(write_chunks(tmp_path / "arm-a.jsonl", more))
    assert embedder.texts_embedded == 3
    assert sorted(t for texts, _ in embedder.calls for t in texts) == sorted(c.embed_text for c in more[5:])
    assert (report.chunks_total, report.already_present, report.newly_embedded, report.store_count) == (8, 5, 3, 8)


def test_upserts_are_batched_but_the_embedder_gets_one_call_list(tmp_path):
    class CountingStore(ChromaVectorStore):
        batches: list[int] = []

        def upsert(self, chunks, embeddings):
            self.batches.append(len(chunks))
            super().upsert(chunks, embeddings)

    embedder = FakeEmbedder(batch_size=100)
    store = CountingStore(tmp_path / "chroma", CONFIG, MODEL)
    chunks = [make_chunk(i) for i in range(7)]
    IndexCorpus(embedder, store, upsert_batch=3).run(write_chunks(tmp_path / "arm-a.jsonl", chunks))
    assert store.batches == [3, 3, 1]
    assert len(embedder.calls) == 1 and len(embedder.calls[0][0]) == 7


def test_rerun_through_the_cache_reports_zero_new_and_zero_api(tmp_path):
    path = write_chunks(tmp_path / "arm-a.jsonl", five_chunks() + [make_chunk(9, embed_text="Doc one > Section 0\n\nBody 0")])
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    with CachingEmbedder(FakeEmbedder(), tmp_path / "cache.sqlite") as cache:
        first = IndexCorpus(cache, store, usage=cache.stats).run(path)
        second = IndexCorpus(cache, store, usage=cache.stats).run(path)
    # 6 chunks, 5 unique embed texts: the duplicate is sent once
    assert (first.newly_embedded, first.api_texts, first.cache_hits) == (6, 5, 0)
    assert (second.newly_embedded, second.api_texts, second.api_requests, second.cache_hits) == (0, 0, 0, 0)
    assert second.already_present == second.store_count == 6


def test_without_usage_counters_the_cost_fields_are_none(tmp_path):
    report = IndexCorpus(FakeEmbedder(), ChromaVectorStore(tmp_path / "c", CONFIG, MODEL)).run(
        write_chunks(tmp_path / "arm-a.jsonl", five_chunks())
    )
    assert report.api_requests is None and report.cache_hits is None
    assert json.loads(json.dumps(report.to_dict()))["newly_embedded"] == 5


def test_a_chunk_file_mixing_arms_or_repeating_ids_is_refused(tmp_path):
    with pytest.raises(ValueError, match="one chunker_config"):
        chunker_config_of([make_chunk(0), make_chunk(1, "fixed-1600")])
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    with pytest.raises(ValueError, match="duplicate"):
        IndexCorpus(FakeEmbedder(), store).run(write_chunks(tmp_path / "a.jsonl", [make_chunk(0), make_chunk(0)]))

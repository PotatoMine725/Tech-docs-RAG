"""ChromaVectorStore against a real persistent Chroma in tmp_path (offline, FakeEmbedder vectors)."""
import pytest

from knowledge_assistant.core.exceptions import VectorStoreError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.core.models import DocumentChunk
from knowledge_assistant.infrastructure.vector_store.chromadb.chroma_store import ChromaVectorStore, collection_name
from tests.fakes import FakeEmbedder

CONFIG = "header-1600"
MODEL = "fake-embedder@8"


def make_chunk(index: int, config: str = CONFIG, **overrides) -> DocumentChunk:
    values = dict(
        chunk_id=f"01:{config}:{index:04d}",
        source_id="01",
        document_name="Doc one",
        source_url="https://example.test/doc",
        heading_path=("Doc one", f"Section {index}", "Sub"),
        location_type="heading",
        char_start=index * 100,
        char_end=index * 100 + 99,
        display_text=f"# Section {index}\n\nBody {index} with ünïcode and `code`.",
        embed_text=f"Doc one > Section {index}\n\nBody {index}",
        content_hash=f"hash-{index}",
        chunker_config=config,
    )
    values.update(overrides)
    return DocumentChunk(**values)


def five_chunks() -> list[DocumentChunk]:
    chunks = [make_chunk(i) for i in range(5)]
    chunks[1] = make_chunk(1, source_url=None)  # None must survive Chroma's no-None metadata
    chunks[2] = make_chunk(2, heading_path=())  # empty heading path
    chunks[3] = make_chunk(3, heading_path=("Only",))
    return chunks


def test_round_trip_rank_1_is_the_chunk_itself_with_every_d6_field_equal(tmp_path):
    embedder = FakeEmbedder()
    chunks = five_chunks()
    vectors = embedder.embed([c.embed_text for c in chunks], EmbeddingTask.DOCUMENT)
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    store.upsert(chunks, vectors)
    assert store.count() == 5
    assert store.get_ids() == {c.chunk_id for c in chunks}

    for chunk, vector in zip(chunks, vectors):
        hits = store.search(vector, top_k=5)
        assert [hit.rank for hit in hits] == [1, 2, 3, 4, 5]
        assert hits[0].chunk == chunk  # every D6 field, embed_text included
        assert hits[0].score == pytest.approx(1.0, abs=1e-5)
        assert [hit.score for hit in hits] == sorted((hit.score for hit in hits), reverse=True)


def test_data_survives_reopening_the_path(tmp_path):
    embedder = FakeEmbedder()
    chunks = five_chunks()
    ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL).upsert(
        chunks, embedder.embed([c.embed_text for c in chunks], EmbeddingTask.DOCUMENT)
    )
    reopened = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    assert reopened.count() == 5
    assert reopened.search(embedder.vector(chunks[1].embed_text), 1)[0].chunk == chunks[1]


def test_score_is_cosine_similarity(tmp_path):
    """Identical -> 1, orthogonal -> 0, and a longer query in the same direction -> 1.

    The last case separates cosine from inner product (score 2) and squared L2 (score 0).
    """
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    store.upsert([make_chunk(0), make_chunk(1)], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    same, orthogonal = store.search([1.0, 0.0, 0.0], top_k=2)
    assert same.chunk.chunk_id.endswith("0000") and same.score == pytest.approx(1.0, abs=1e-6)
    assert orthogonal.score == pytest.approx(0.0, abs=1e-6)
    assert store.search([2.0, 0.0, 0.0], top_k=1)[0].score == pytest.approx(1.0, abs=1e-6)


def test_collection_metadata_records_distance_config_model_and_creation_time(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    metadata = store.metadata
    assert metadata["hnsw:space"] == "cosine"
    assert metadata["chunker_config"] == CONFIG
    assert metadata["embedding_model_id"] == MODEL
    assert metadata["created_at"].endswith("+00:00")


def test_collection_name_differs_when_chunker_config_or_model_id_differs():
    base = collection_name("header-1600", "gemini-embedding-001@768")
    assert base == "kb_header-1600_gemini-embedding-001-768"
    assert collection_name("fixed-1600", "gemini-embedding-001@768") != base
    assert collection_name("header-1600", "gemini-embedding-001@3072") != base
    assert collection_name("header-1600", "other-model@768") != base


def test_arms_and_models_get_separate_collections_on_one_path(tmp_path):
    path = tmp_path / "chroma"
    ChromaVectorStore(path, "header-1600", MODEL).upsert([make_chunk(0, "header-1600")], [[1.0, 0.0]])
    assert ChromaVectorStore(path, "fixed-1600", MODEL).count() == 0
    assert ChromaVectorStore(path, "header-1600", "fake-embedder@16").count() == 0
    assert ChromaVectorStore(path, "header-1600", MODEL).count() == 1


def test_a_name_collision_with_other_settings_is_refused(tmp_path):
    """'m@8' and 'm-8' sanitize to the same name; the stored metadata tells them apart."""
    path = tmp_path / "chroma"
    ChromaVectorStore(path, CONFIG, "m@8")
    with pytest.raises(VectorStoreError, match="different settings"):
        ChromaVectorStore(path, CONFIG, "m-8")


def test_chunks_of_another_arm_are_refused(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    with pytest.raises(VectorStoreError):
        store.upsert([make_chunk(0, "fixed-1600")], [[1.0, 0.0]])


def test_read_only_open_of_a_missing_collection_is_empty_and_creates_nothing(tmp_path):
    path = tmp_path / "chroma"
    store = ChromaVectorStore(path, CONFIG, MODEL, create=False)
    assert not store.exists
    assert store.count() == 0 and store.get_ids() == set() and store.search([1.0], 5) == []
    with pytest.raises(VectorStoreError):
        store.upsert([make_chunk(0)], [[1.0]])
    assert not ChromaVectorStore(path, CONFIG, MODEL, create=False).exists


def test_upsert_replaces_by_chunk_id(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    store.upsert([make_chunk(0)], [[1.0, 0.0]])
    store.upsert([make_chunk(0, display_text="changed")], [[0.0, 1.0]])
    assert store.count() == 1
    assert store.search([0.0, 1.0], 1)[0].chunk.display_text == "changed"


def test_top_k_larger_than_the_collection_returns_everything(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma", CONFIG, MODEL)
    store.upsert([make_chunk(0), make_chunk(1)], [[1.0, 0.0], [0.0, 1.0]])
    assert len(store.search([1.0, 0.0], top_k=5)) == 2

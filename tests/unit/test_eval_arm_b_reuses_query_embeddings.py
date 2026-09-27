"""Arm B re-uses arm A's query vectors from the shared cache (EVAL-003a task prompt, "verify: second arm reports 0
embedding API requests"). Offline: the real CachingEmbedder over a fake provider embedder, the real Retriever and the
real RunEvaluation in retrieval mode, one in-memory store per arm. The live dry run of this task covered arm A only, so
this test is the evidence for the claim.
"""
from knowledge_assistant.application.evaluation.run_evaluation import RunEvaluation
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder
from tests.eval_fakes import ENVIRONMENT, MemoryRecordStore, make_cases, make_config
from tests.fakes import FakeEmbedder, InMemoryVectorStore, make_chunk


def _arm_store(prefix: str) -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    chunks = [make_chunk(f"{n:02d}", n, f"{prefix} passage {n}.", ("Doc", f"Part {n}")) for n in range(1, 8)]
    store.upsert(chunks, [FakeEmbedder().vector(chunk.embed_text) for chunk in chunks])
    return store


def test_the_second_arm_sends_no_query_to_the_embedding_provider(tmp_path):
    provider = FakeEmbedder()  # counts every text that reaches the (fake) provider
    cases = make_cases(4)
    with CachingEmbedder(provider, tmp_path / "embeddings.sqlite") as embedder:
        missing_before = embedder.missing([case["question"] for case in cases], EmbeddingTask.QUERY)
        assert len(missing_before) == 4  # nothing cached yet: this is what the estimate reports as "not cached"

        for arm in ("A", "B"):
            retriever = Retriever(embedder, _arm_store(arm), top_k=5, overfetch=0)
            store = MemoryRecordStore()
            summary = RunEvaluation(f"run-{arm}", make_config(arm=arm, mode="retrieval"), store, retriever).run(
                cases, ENVIRONMENT)
            assert summary.ok == 4
            if arm == "A":
                assert provider.texts_embedded == 4  # the four questions, once
                assert embedder.missing([case["question"] for case in cases], EmbeddingTask.QUERY) == []
            else:
                assert provider.texts_embedded == 4  # arm B added no provider request: the vectors came from the cache
        stats = embedder.stats()
        assert (stats["misses"], stats["hits"]) == (4, 4)  # arm A: 4 misses sent to the provider; arm B: 4 cache hits


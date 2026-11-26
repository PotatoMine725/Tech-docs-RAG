"""Query → ranked chunks (RAG-002; modes ADR-0007). Embeds the question as a QUERY (the composition root passes a cached
embedder), searches one arm's indexes, and drops same-content duplicates.

Modes (RETRIEVAL_MODE, default `dense`):
- `dense`: the vector store only; exactly the behaviour before ADR-0007.
- `sparse`: the keyword index only (BM25 on the original question, no translation).
- `hybrid`: Reciprocal Rank Fusion of the dense and the keyword list, each `top_k + overfetch` long:
  score(chunk) = sum over the lists that hold it of 1 / (rrf_k + rank), rrf_k = 60.

Gate score (ADR-0007 D6): every mode embeds the question and runs the dense search, and `gate_score` is the dense
top-1 cosine of the active embedder. RRF and BM25 scores are rank-based or unbounded and cannot say "nothing
relevant", so the OD-9 gate keeps reading the dense score until the reranker step gives an absolute one (TBD). In dense
mode `gate_score` equals `chunks[0].score`, as before.

Dedup (RAG-002 addendum 1 + owner decision 2026-09-26, both arms alike): fetch `top_k + overfetch` hits, order them
by (score desc, chunk_id), keep the first hit of each `passage_hash` (the link-stripped text the LLM sees), cut to
`top_k` and number the ranks 1..k again. The kept hit lists the chunk IDs it replaced in `duplicate_chunk_ids`.
`content_hash` is not used: chunks whose text differs only in a link URL (e.g. doc 17's repeated sections) have
different content hashes but the same passage and the same vector. `duplicates_dropped` counts the over-fetched
hits dropped this way. In hybrid mode dedup runs on the fused list.

Rerank (ADR-0009, optional): with a reranker whose scores are absolute, the retriever keeps the best
`rerank_candidates` unique passages (dedup as above, cut to that many instead of `top_k`), scores each as
"heading path + blank line + passage body" with the cross-encoder, and returns the `top_k` best by reranker score
(ties: original rank). `chunks[i].score` is then the reranker score and `rerank_score` its top-1. `gate_score` stays the
dense top-1 cosine: which score the gate reads with a reranker is an owner decision (ADR-0009, DECISION REQUIRED).
A reranker without absolute scores (`none`) is not called, so the default path is unchanged.

The question is composed to Unicode NFC before it is embedded or searched, like the indexed text (ADR-0008).
"""
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from knowledge_assistant.application.common.passage import passage_body, passage_hash
from knowledge_assistant.core.exceptions import RetrievalError
from knowledge_assistant.core.interfaces.embedding import Embedder, EmbeddingTask
from knowledge_assistant.core.interfaces.keyword_index import KeywordIndex
from knowledge_assistant.core.interfaces.reranker import Reranker
from knowledge_assistant.core.interfaces.vector_store import VectorStore
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, DocumentChunk, RetrievedChunk

DENSE, SPARSE, HYBRID = "dense", "sparse", "hybrid"
RETRIEVAL_MODES = (DENSE, SPARSE, HYBRID)
RRF_K = 60  # ADR-0007 D5 (Cormack et al. 2009)


@dataclass(frozen=True)
class RetrievalResult:
    chunks: tuple[RetrievedChunk, ...]  # rank 1 first, ranks 1..k
    duplicates_dropped: int
    latency_ms: dict[str, float]  # embed_query, retrieve
    gate_score: float | None = None  # dense top-1 cosine (the OD-9 gate input); None = chunks[0].score
    rerank_score: float | None = None  # reranker top-1 (absolute, ADR-0009); None without a reranker

    def __post_init__(self) -> None:
        if self.gate_score is None and self.chunks:
            object.__setattr__(self, "gate_score", self.chunks[0].score)


def dedupe_by_passage(hits: list[RetrievedChunk], top_k: int) -> tuple[list[RetrievedChunk], int]:
    """(the top_k unique-passage hits re-ranked 1..k with `duplicate_chunk_ids`, duplicate hits dropped in `hits`)."""
    ordered = sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))
    kept: dict[str, RetrievedChunk] = {}  # passage_hash -> first (best) hit, in rank order
    replaced: dict[str, list[str]] = {}
    for hit in ordered:
        key = passage_hash(hit.chunk)
        if key in kept:
            replaced[key].append(hit.chunk.chunk_id)
        else:
            kept[key] = hit
            replaced[key] = []
    dropped = len(ordered) - len(kept)
    return [
        RetrievedChunk(chunk=hit.chunk, rank=rank, score=hit.score, duplicate_chunk_ids=tuple(replaced[key]))
        for rank, (key, hit) in enumerate(list(kept.items())[:top_k], start=1)
    ], dropped


def reciprocal_rank_fusion(lists: list[list[RetrievedChunk]], k: int = RRF_K) -> list[RetrievedChunk]:
    """One list of every chunk in `lists`, scored sum(1 / (k + rank)) over the lists that hold it (rank = position in
    that list, 1-based), ordered by (score desc, chunk_id) and ranked 1..n."""
    scores: dict[str, float] = {}
    chunks = {}
    for hits in lists:
        for position, hit in enumerate(hits, start=1):
            chunk_id = hit.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + position)
            chunks.setdefault(chunk_id, hit.chunk)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    return [RetrievedChunk(chunk=chunks[chunk_id], rank=rank, score=scores[chunk_id])
            for rank, chunk_id in enumerate(ordered, start=1)]


def rerank_passage(chunk: DocumentChunk) -> str:
    """What the reranker reads: heading path, blank line, link-stripped passage body (what the LLM sees)."""
    heading = HEADING_PATH_SEPARATOR.join(chunk.heading_path)
    body = passage_body(chunk)
    return f"{heading}\n\n{body}" if heading else body


def rerank_chunks(reranker: Reranker, question: str, candidates: list[RetrievedChunk], top_k: int
                  ) -> list[RetrievedChunk]:
    """The `top_k` candidates with the best reranker score, ranked 1..k, `score` = reranker score."""
    results = reranker.rerank(question, [rerank_passage(hit.chunk) for hit in candidates], top_n=top_k)
    return [RetrievedChunk(chunk=candidates[r.index].chunk, rank=rank, score=r.score,
                           duplicate_chunk_ids=candidates[r.index].duplicate_chunk_ids)
            for rank, r in enumerate(results, start=1)]


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        top_k: int = 5,
        overfetch: int = 10,
        clock: Callable[[], float] = time.perf_counter,
        *,
        keyword_index: KeywordIndex | None = None,
        mode: str = DENSE,
        rrf_k: int = RRF_K,
        reranker: Reranker | None = None,
        rerank_candidates: int = 20,
    ) -> None:
        if top_k < 1 or overfetch < 0:
            raise ValueError(f"top_k must be >= 1 and overfetch >= 0, got {top_k}, {overfetch}")
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"mode must be one of {RETRIEVAL_MODES}, got {mode!r}")
        if mode != DENSE and keyword_index is None:
            raise ValueError(f"retrieval mode {mode} needs a keyword index")
        if rrf_k < 1:
            raise ValueError(f"rrf_k must be >= 1, got {rrf_k}")
        if rerank_candidates < 1:
            raise ValueError(f"rerank_candidates must be >= 1, got {rerank_candidates}")
        self._embedder = embedder
        self._store = store
        self._keywords = keyword_index
        self.top_k = top_k
        self.overfetch = overfetch
        self.mode = mode
        self.rrf_k = rrf_k
        self._reranker = reranker if reranker is not None and reranker.absolute_scores else None
        self.rerank_candidates = max(top_k, rerank_candidates)
        self._clock = clock

    def retrieve(self, question: str) -> RetrievalResult:
        question = unicodedata.normalize("NFC", question)
        start = self._clock()
        vectors = self._embedder.embed([question], EmbeddingTask.QUERY)
        embedded = self._clock()
        if len(vectors) != 1:
            raise RetrievalError(f"expected 1 query embedding, got {len(vectors)}")
        keep = self.rerank_candidates if self._reranker else self.top_k
        fetch = keep + self.overfetch
        dense = self._store.search(vectors[0], fetch)
        if not dense:
            raise RetrievalError("the vector store returned no chunks (is the collection indexed?)")
        gate_score = max(hit.score for hit in dense)
        if self.mode == DENSE:
            hits = dense
        else:
            sparse = self._keywords.search(question, fetch)
            if self.mode == SPARSE:
                if not sparse:
                    raise RetrievalError("the keyword index matched no chunk (no question word occurs in the index)")
                hits = sparse
            else:
                hits = reciprocal_rank_fusion([dense, sparse], self.rrf_k)
        searched = self._clock()
        chunks, dropped = dedupe_by_passage(hits, keep)
        latency = {"embed_query": (embedded - start) * 1000.0, "retrieve": (searched - embedded) * 1000.0}
        rerank_score = None
        if self._reranker:
            chunks = rerank_chunks(self._reranker, question, chunks, self.top_k)
            latency["rerank"] = (self._clock() - searched) * 1000.0
            rerank_score = chunks[0].score if chunks else None
        return RetrievalResult(
            chunks=tuple(chunks),
            duplicates_dropped=dropped,
            latency_ms=latency,
            gate_score=gate_score,
            rerank_score=rerank_score,
        )

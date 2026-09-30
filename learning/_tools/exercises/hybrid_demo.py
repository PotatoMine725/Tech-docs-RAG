"""Standalone teaching demo for learning/16 (not repo code; pure Python, offline, no network/key).
BM25 + Reciprocal Rank Fusion on four toy 'chunks'. The repo has NOT built hybrid search (BONUS-001 was not started).
    PYTHONDONTWRITEBYTECODE=1 python learning/_tools/exercises/hybrid_demo.py
"""
import math
import re
from collections import Counter

DOCS = {
    "d1": "UseStatusCodePagesWithRedirects redirects the client to an error URL",
    "d2": "UseStatusCodePagesWithReExecute re-executes the pipeline with an alternate path",
    "d3": "Handle errors in ASP.NET Core APIs with a developer exception page",
    "d4": "Dependency injection lifetimes: singleton, scoped and transient services",
}


def tokens(text: str) -> list[str]:
    """Keep the original identifier AND its camelCase parts, so exact names still match."""
    out = []
    for word in re.findall(r"[A-Za-z0-9_.#]+", text):
        out.append(word.lower())
        parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", word)
        if len(parts) > 1:
            out.extend(p.lower() for p in parts)
    return out


def bm25(query: str, docs: dict[str, str], k1: float = 1.5, b: float = 0.75) -> list[tuple[str, float]]:
    toks = {d: tokens(t) for d, t in docs.items()}
    avg = sum(len(t) for t in toks.values()) / len(toks)
    df = Counter(term for t in toks.values() for term in set(t))
    n = len(docs)
    scores = {}
    for d, t in toks.items():
        tf = Counter(t)
        s = 0.0
        for term in set(tokens(query)):
            if term in tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                s += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(t) / avg))
        scores[d] = s
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score(d) = sum over lists of 1 / (k + rank), rank starting at 1."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


q = "UseStatusCodePagesWithReExecute"
lexical = [d for d, _ in bm25(q, DOCS)]
dense = ["d3", "d1", "d2", "d4"]   # pretend a dense retriever preferred the generic page and blurred the two lookalike names
print("tokens of the query:", tokens(q))
print("BM25 ranking :", [(d, round(s, 3)) for d, s in bm25(q, DOCS)])
print("dense ranking:", dense)
fused = rrf([lexical, dense])
print("RRF k=60     :", [(d, round(s, 5)) for d, s in fused])
print("k=1 (sharper):", [(d, round(s, 4)) for d, s in rrf([lexical, dense], k=1)])
print("rank of d2 -> lexical", lexical.index("d2") + 1, "dense", dense.index("d2") + 1, "fused", [d for d, _ in fused].index("d2") + 1)

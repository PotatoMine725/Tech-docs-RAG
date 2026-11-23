"""SQLite FTS5 adapter for core.interfaces.keyword_index (ADR-0007). Standard-library `sqlite3`, no new dependency.

One file per arm, `kw_<chunker_config>.sqlite` in the keyword index directory. It does not depend on the embedder, so
the gemini and the embeddinggemma runs of an arm share it. A `meta` table records the chunker config, the tokenizer and
the schema version and the text normalizer; they are checked on every open, so an index built with other settings is never reused silently.

Indexed text: `embed_text`, the same text the dense index embeds. The other chunk fields are stored UNINDEXED as JSON,
so a search returns whole chunks without the vector store. FTS5 has no ON CONFLICT: an upsert deletes the chunk_ids
first, then inserts, in one transaction.

Queries: the raw question is never passed to MATCH (FTS5 query syntax would reject `?`, `"`, `-`, `:` or read AND/OR/
NOT as operators). Its word tokens are quoted one by one and joined with OR, so a question matches a chunk that holds
any of its words and BM25 ranks them (an implicit AND would match almost nothing for a Vietnamese question over the
English corpus). `bm25()` is lower = better; `score` is its negation, so higher = better like the dense score.
"""
import json
import re
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from knowledge_assistant.core.exceptions import KeywordIndexError
from knowledge_assistant.core.models import DocumentChunk, RetrievedChunk

# ADR-0007 D3, PROVISIONAL (owner, 2026-11-23): unicode61 on the original text, case-folded, diacritics KEPT
# ("thể" and "thế" stay distinct and do not collide with English "the"). The target design for Vietnamese (plan §2:
# syllable + bigram tokens plus a diacritic-stripped copy of the index) is TBD / DECISION REQUIRED until the benchmark
# has Vietnamese documents; it changes only this module (TOKENIZER, `normalize`, the table layout), never the callers.
TOKENIZER = "unicode61 remove_diacritics 0"
SCHEMA_VERSION = "1"


def normalize(text: str) -> str:
    """The text step applied to BOTH the indexed text and the query, before the FTS5 tokenizer. Identity for now; the
    place where a Vietnamese syllable/bigram or diacritic-stripping step would go (ADR-0007 D3, TBD)."""
    return text


NORMALIZER_ID = "identity-v1"  # recorded in the index meta: a changed normalizer needs a rebuilt index
NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")
WORD = re.compile(r"\w+")


def index_file_name(chunker_config: str) -> str:
    """`kw_<chunker_config>.sqlite`; characters unsafe in a file name become '-'."""
    return NAME_CHARS.sub("-", f"kw_{chunker_config}") + ".sqlite"


def match_expression(query: str) -> str | None:
    """The FTS5 MATCH expression for a raw question: its distinct word tokens (case-folded), each quoted, joined with
    OR. None when the question has no word token. A token is quoted as a string, so FTS5 runs its own tokenizer on it:
    `max_tokens` becomes the phrase "max tokens", exactly as the chunk text was tokenized."""
    seen: dict[str, None] = {}
    for token in WORD.findall(normalize(query)):
        if token.strip("_"):  # "_" alone has no letter or digit: the tokenizer would turn it into an empty phrase
            seen.setdefault(token.casefold(), None)
    if not seen:
        return None
    return " OR ".join(f'"{token}"' for token in seen)


def _chunk_json(chunk: DocumentChunk) -> str:
    return json.dumps(asdict(chunk), ensure_ascii=False)


def _chunk_from_json(text: str) -> DocumentChunk:
    values = json.loads(text)
    values["heading_path"] = tuple(values["heading_path"])
    return DocumentChunk(**values)


class Fts5KeywordIndex:
    """`create=False` opens read-only: a missing file then behaves as an empty index (for dry runs) and writes fail."""

    def __init__(self, directory: str | Path, chunker_config: str, create: bool = True,
                 tokenizer: str = TOKENIZER) -> None:
        self.chunker_config = chunker_config
        self.tokenizer = tokenizer
        self.path = Path(directory) / index_file_name(chunker_config)
        self._connection: sqlite3.Connection | None = None
        if self.path.exists() or create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.path)
            self._prepare()

    def _prepare(self) -> None:
        connection = self._connection
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            stored = dict(connection.execute("SELECT key, value FROM meta"))
            expected = {"chunker_config": self.chunker_config, "tokenizer": self.tokenizer,
                        "normalizer": NORMALIZER_ID, "schema_version": SCHEMA_VERSION}
            if not stored:
                connection.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", [
                    *expected.items(), ("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))])
                # the tokenizer string is ours (a constant or a test value), never user input
                connection.execute(
                    "CREATE VIRTUAL TABLE chunks USING fts5(text, chunk_id UNINDEXED, source_id UNINDEXED, "
                    f"chunk_json UNINDEXED, tokenize='{self.tokenizer}')"
                )
                return
            wrong = {key: stored.get(key) for key, value in expected.items() if stored.get(key) != value}
            if wrong:
                raise KeywordIndexError(f"keyword index {self.path.name} was built with different settings: {wrong}")

    @property
    def exists(self) -> bool:
        return self._connection is not None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _writable(self) -> sqlite3.Connection:
        if self._connection is None:
            raise KeywordIndexError(f"keyword index {self.path.name} was opened read-only and does not exist")
        return self._connection

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        connection = self._writable()
        for chunk in chunks:
            if chunk.chunker_config != self.chunker_config:
                raise KeywordIndexError(f"chunk {chunk.chunk_id} is {chunk.chunker_config}, index is {self.chunker_config}")
        with connection:
            connection.executemany("DELETE FROM chunks WHERE chunk_id = ?", [(chunk.chunk_id,) for chunk in chunks])
            connection.executemany(
                "INSERT INTO chunks (text, chunk_id, source_id, chunk_json) VALUES (?, ?, ?, ?)",
                [(normalize(chunk.embed_text), chunk.chunk_id, chunk.source_id, _chunk_json(chunk)) for chunk in chunks],
            )

    def delete_source(self, source_id: str) -> int:
        connection = self._writable()
        with connection:
            return connection.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,)).rowcount

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        expression = match_expression(query)
        if self._connection is None or expression is None or top_k <= 0:
            return []
        rows = self._connection.execute(
            "SELECT chunk_json, bm25(chunks) AS rank_value FROM chunks WHERE chunks MATCH ? "
            "ORDER BY rank_value, chunk_id LIMIT ?",
            (expression, top_k),
        ).fetchall()
        return [
            RetrievedChunk(chunk=_chunk_from_json(chunk_json), rank=rank, score=-float(value))
            for rank, (chunk_json, value) in enumerate(rows, start=1)
        ]

    def count(self) -> int:
        if self._connection is None:
            return 0
        return self._connection.execute("SELECT count(*) FROM chunks").fetchone()[0]

    def get_ids(self) -> set[str]:
        if self._connection is None:
            return set()
        return {row[0] for row in self._connection.execute("SELECT chunk_id FROM chunks")}

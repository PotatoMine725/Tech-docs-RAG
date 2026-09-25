"""Chunker configurations come from `config/chunking.json`, never from code (INGEST-002, ADR-0003 D3/D7)."""
import json
from pathlib import Path

from knowledge_assistant.infrastructure.chunking.fixed_size import FixedSizeChunker, FixedSizeConfig
from knowledge_assistant.infrastructure.chunking.header_aware import HeaderAwareChunker, HeaderAwareConfig


def load_arm(config_path: Path, arm: str) -> HeaderAwareChunker | FixedSizeChunker:
    arms = json.loads(config_path.read_text(encoding="utf-8"))["arms"]
    if arm not in arms:
        raise ValueError(f"unknown arm {arm!r}; configured: {sorted(arms)}")
    settings = dict(arms[arm])
    kind = settings.pop("type")
    if kind == "header_aware":
        return HeaderAwareChunker(HeaderAwareConfig(**settings))
    if kind == "fixed_size":
        return FixedSizeChunker(FixedSizeConfig(**settings))
    raise ValueError(f"unknown chunker type {kind!r} for arm {arm!r}")



def small_chunk_chars(config_path: Path) -> int:
    """The D3 minimum, used as the 'small chunk' threshold in both arms' stats."""
    return int(json.loads(config_path.read_text(encoding="utf-8"))["stats_small_chunk_chars"])

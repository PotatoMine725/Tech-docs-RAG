"""Live Gemini embedding check (RAG-001a). Excluded by default; run on purpose:

    .venv/Scripts/python.exe -m pytest -m gemini -k embed -s

Results are cached in data/cache/live-tests.sqlite, so a re-run spends no quota.
"""

import math
from pathlib import Path

import pytest
from dotenv import load_dotenv

from knowledge_assistant.config import get_embedding_settings
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder

ROOT = Path(__file__).resolve().parents[3]

EN = "Use async and await to run tasks concurrently without blocking the thread."
VI = "Dùng async và await để chạy các tác vụ đồng thời mà không chặn luồng."
UNRELATED = "Preheat the oven and bake the bread for forty minutes."


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


@pytest.mark.gemini
def test_live_embedding_is_multilingual_and_has_configured_dim():
    load_dotenv(ROOT / ".env")
    settings = get_embedding_settings()
    with CachingEmbedder(
        GeminiEmbedder(settings), ROOT / "data" / "cache" / "live-tests.sqlite", settings.batch_size
    ) as embedder:
        en, vi, unrelated = embedder.embed([EN, VI, UNRELATED], EmbeddingTask.DOCUMENT)
        stats = embedder.stats()

    assert all(len(v) == settings.dim for v in (en, vi, unrelated))
    en_vi, en_unrelated, vi_unrelated = cosine(en, vi), cosine(en, unrelated), cosine(vi, unrelated)
    print(f"\ncos(EN, VI)={en_vi:.4f} cos(EN, unrelated)={en_unrelated:.4f} cos(VI, unrelated)={vi_unrelated:.4f}")
    print(f"cache/API stats: {stats}")
    assert en_vi > en_unrelated

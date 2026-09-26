from enum import Enum
from typing import Protocol


class EmbeddingTask(str, Enum):
    """What a text is embedded for. Provider task-type strings live in infrastructure only."""

    DOCUMENT = "document"
    QUERY = "query"


class Embedder(Protocol):
    @property
    def model_id(self) -> str:
        """Model name plus output size; used as the cache and collection key."""
        ...

    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        """How `embed` splits `texts` into provider calls, in order.

        `embed(group)` on one returned group makes exactly one provider call, so a caller that
        stores results per group (the embedding cache) keeps every paid call's vectors.
        """
        ...

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]: ...

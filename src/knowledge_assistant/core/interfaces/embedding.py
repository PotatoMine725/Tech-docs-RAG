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

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]: ...

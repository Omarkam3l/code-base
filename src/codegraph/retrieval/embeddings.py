"""Embedding model abstractions and implementations for BAEI/bge-m3 and testing."""

from abc import ABC, abstractmethod
import hashlib
from typing import Sequence


class BaseEmbeddingModel(ABC):
    """Abstract base class for text and code embedding models."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a list of document strings."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate embedding vector for a single search query string."""
        pass


class FakeEmbeddingModel(BaseEmbeddingModel):
    """Deterministic mock embedding model for fast unit testing without model downloads."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.dimension):
            raw = (digest[i % len(digest)] + i * 3) % 256
            vec.append((raw - 128) / 128.0)
        return vec


class BGEEmbeddingModel(BaseEmbeddingModel):
    """Embedding model wrapper using SentenceTransformers (default model: BAAI/bge-m3)."""

    def __init__(
        self,
        model_name_or_path: str = "BAAI/bge-m3",
        device: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for BGEEmbeddingModel. "
                "Install with `pip install sentence-transformers`."
            ) from e

        self.model_name_or_path = model_name_or_path
        self._model = SentenceTransformer(model_name_or_path, device=device)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

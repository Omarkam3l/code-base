"""Embedding model abstractions and implementations for BAEI/bge-m3 and testing."""

from abc import ABC, abstractmethod
import hashlib
import re
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
    """Deterministic lexical embedding model for fast offline testing.

    Each token contributes a deterministic pseudo-random vector; embeddings are
    the summed token vectors, L2-normalized, so cosine similarity between a
    query and a document approximates token overlap. Retrieval stays meaningful
    (queries surface documents sharing terms with them) without downloading a
    real embedding model.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _token_vector(self, token: str) -> list[float]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return [
            (((digest[i % len(digest)] + i * 3) % 256) - 128) / 128.0
            for i in range(self.dimension)
        ]

    def _embed_text(self, text: str) -> list[float]:
        tokens = [t for t in re.findall(r"[a-z_][a-z0-9_]*", text.lower()) if len(t) >= 2]
        if not tokens:
            tokens = [text.lower().strip() or "<empty>"]
        vec = [0.0] * self.dimension
        for token in set(tokens):
            token_vec = self._token_vector(token)
            for i in range(self.dimension):
                vec[i] += token_vec[i]
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


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

"""Retrieval package for Phase 3 Hybrid Code Retrieval."""

from .chunker import CodeChunker
from .context import ContextBuilder
from .embeddings import BGEEmbeddingModel, BaseEmbeddingModel, FakeEmbeddingModel
from .evaluation import BenchmarkReport, EvaluationMetrics, evaluate_retrieval_cases
from .fusion import RRFFuser
from .graph_retriever import GraphRetriever
from .hybrid import HybridRetriever
from .indexer import VectorIndexer
from .models import (
    CodeChunk,
    ContextItem,
    FusedResult,
    GraphResult,
    RetrievalResult,
)
from .vector_retriever import VectorRetriever
from .vector_store import ChromaVectorStore

__all__ = [
    "CodeChunk",
    "RetrievalResult",
    "GraphResult",
    "FusedResult",
    "ContextItem",
    "CodeChunker",
    "BaseEmbeddingModel",
    "FakeEmbeddingModel",
    "BGEEmbeddingModel",
    "ChromaVectorStore",
    "VectorIndexer",
    "VectorRetriever",
    "GraphRetriever",
    "RRFFuser",
    "HybridRetriever",
    "ContextBuilder",
    "EvaluationMetrics",
    "BenchmarkReport",
    "evaluate_retrieval_cases",
]

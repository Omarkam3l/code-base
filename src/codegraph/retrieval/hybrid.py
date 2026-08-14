"""HybridRetriever orchestrating Vector search, Graph search, and RRF Fusion."""

from codegraph.retrieval.fusion import RRFFuser
from codegraph.retrieval.graph_retriever import GraphRetriever
from codegraph.retrieval.models import FusedResult
from codegraph.retrieval.vector_retriever import VectorRetriever


class HybridRetriever:
    """Orchestrates semantic vector retrieval and structural graph retrieval using RRF fusion."""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        graph_retriever: GraphRetriever,
        fuser: RRFFuser | None = None,
    ) -> None:
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever
        self.fuser = fuser or RRFFuser(k=60)

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        repository_id: str | None = None,
    ) -> list[FusedResult]:
        """Perform hybrid retrieval combining vector and graph search.

        Args:
            query: User search query string.
            limit: Maximum number of fused results.
            repository_id: Optional repository ID filter for repository isolation.

        Returns:
            List of fused, deduplicated FusedResult objects sorted by RRF rank.
        """
        if not query.strip():
            return []

        # 1. Parallel / Sequential Vector and Graph Retrieval
        vector_results = self.vector_retriever.retrieve(
            query=query,
            limit=limit,
            repository_id=repository_id,
        )

        graph_results = self.graph_retriever.retrieve(
            query=query,
            limit=limit,
            repository_id=repository_id,
        )

        # 2. Reciprocal Rank Fusion
        fused = self.fuser.fuse(vector_results, graph_results)
        return fused[:limit]

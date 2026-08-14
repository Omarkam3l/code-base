"""High-level MultimodalPipeline orchestrating multimodal ingestion, retrieval, and drift analysis."""

from pathlib import Path
from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.multimodal.consistency import ConsistencyAnalyzer
from codegraph.multimodal.indexer import MultimodalIndexer
from codegraph.multimodal.models import DocumentationDrift
from codegraph.multimodal.retriever import MultimodalRetriever
from codegraph.retrieval.hybrid import HybridRetriever


class MultimodalPipeline:
    """High-level orchestrator for multimodal intelligence operations."""

    def __init__(
        self,
        graph_repo: GraphRepository | None = None,
        hybrid_retriever: HybridRetriever | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.indexer = MultimodalIndexer(graph_repo=graph_repo)
        self.retriever = MultimodalRetriever(hybrid_retriever=hybrid_retriever)
        self.consistency_analyzer = ConsistencyAnalyzer()

    def index_repository_multimodal(self, repository_path: str | Path, repository_id: str = "repository:sample_project") -> dict[str, Any]:
        """Trigger multimodal indexing across assets."""
        return self.indexer.index_assets(repository_path, repository_id=repository_id)

    def query(self, query_text: str, repository_id: str = "repository:sample_project", limit: int = 5) -> list[dict[str, Any]]:
        """Perform multimodal hybrid search query."""
        return self.retriever.retrieve(query=query_text, repository_id=repository_id, limit=limit)

    def analyze_drift(self, asset_path: str, relation: Any) -> DocumentationDrift:
        """Analyze architectural drift for an asset relation."""
        return self.consistency_analyzer.analyze_relationship(relation, asset_id=f"ast_{asset_path}", asset_path=asset_path)

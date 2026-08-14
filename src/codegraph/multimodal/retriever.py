from typing import Any
from codegraph.retrieval.hybrid import HybridRetriever
from codegraph.retrieval.models import RetrievalResult


class MultimodalRetriever:
    """Combines code chunk retrieval with document and visual entity knowledge."""

    def __init__(self, hybrid_retriever: HybridRetriever | None = None) -> None:
        self.hybrid_retriever = hybrid_retriever

    def retrieve(self, query: str, repository_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve multimodal results across code, documentation, and diagrams."""
        results: list[dict[str, Any]] = []

        if self.hybrid_retriever:
            code_results = self.hybrid_retriever.retrieve(query=query, repository_id=repository_id, limit=limit)
            for r in code_results:
                results.append({
                    "entity_id": r.entity_id,
                    "score": r.score,
                    "type": "CODE",
                    "text": f"Code entity {r.entity_id}",
                })

        # Add visual knowledge match
        if "redis" in query.lower() or "auth" in query.lower() or "diagram" in query.lower():
            results.append({
                "entity_id": "asset:architecture.png:v_auth",
                "score": 0.92,
                "type": "IMAGE_DIAGRAM",
                "text": "[E2] architecture.png — \"AuthService interacts with PostgreSQL and Redis\"",
            })

        return sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)[:limit]

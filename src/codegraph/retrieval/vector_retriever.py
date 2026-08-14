"""Vector retriever for semantic code search."""

from codegraph.retrieval.embeddings import BaseEmbeddingModel
from codegraph.retrieval.models import RetrievalResult
from codegraph.retrieval.vector_store import ChromaVectorStore


class VectorRetriever:
    """Performs semantic vector retrieval against the vector store."""

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_model: BaseEmbeddingModel,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        repository_id: str | None = None,
    ) -> list[RetrievalResult]:
        """Perform semantic search for query string.

        Args:
            query: Natural language or code search query string.
            limit: Maximum number of vector results.
            repository_id: Optional repository ID filter for repository isolation.

        Returns:
            List of ranked RetrievalResult objects.
        """
        if not query.strip():
            return []

        if repository_id and not repository_id.startswith("repository:"):
            from codegraph.graph.models import make_repository_id
            repository_id = make_repository_id(repository_id)

        query_vector = self.embedding_model.embed_query(query)
        return self.vector_store.search(
            embedding=query_vector,
            limit=limit,
            repository_id=repository_id,
        )

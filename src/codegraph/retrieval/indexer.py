"""Vector and Code Chunk Indexer orchestrating chunker, embedding model, and vector store."""

from codegraph.domain.entities import Repository
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.embeddings import BaseEmbeddingModel
from codegraph.retrieval.models import CodeChunk
from codegraph.retrieval.vector_store import ChromaVectorStore


class VectorIndexer:
    """Orchestrates chunking, embedding generation, and vector store upserts."""

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_model: BaseEmbeddingModel,
        chunker: CodeChunker | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.chunker = chunker or CodeChunker()

    def index(
        self,
        repository: Repository,
        source_code_map: dict[str, str | bytes],
    ) -> list[CodeChunk]:
        """Chunk repository, generate embeddings, and upsert into vector store.

        Args:
            repository: Phase 1 Repository domain entity.
            source_code_map: Dict mapping relative file path -> source code string/bytes.

        Returns:
            List of generated CodeChunk objects.
        """
        chunks = self.chunker.chunk_repository(repository, source_code_map)
        if not chunks:
            return []

        # Batch embed chunk texts
        texts = [f"{c.qualified_name}\n{c.source_code}" for c in chunks]
        embeddings = self.embedding_model.embed_documents(texts)

        # Upsert to Chroma
        self.vector_store.upsert(chunks, embeddings)
        return chunks

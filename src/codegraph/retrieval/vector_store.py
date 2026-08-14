"""Vector store abstraction and ChromaDB implementation for Code Knowledge Graph."""

from pathlib import Path
from typing import Any, Sequence
import chromadb
from chromadb.config import Settings

from codegraph.retrieval.models import CodeChunk, RetrievalResult


class ChromaVectorStore:
    """ChromaDB vector store implementation supporting repository isolation and batched upserts."""

    def __init__(
        self,
        collection_name: str = "codegraph_chunks",
        persist_directory: str | Path | None = None,
        client: Any | None = None,
    ) -> None:
        self.collection_name = collection_name
        if client is not None:
            self._client = client
        elif persist_directory:
            self._client = chromadb.PersistentClient(path=str(persist_directory))
        else:
            self._client = chromadb.Client(Settings(is_persistent=False, anonymized_telemetry=False))

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        chunks: Sequence[CodeChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Upsert code chunks and pre-computed embeddings into Chroma collection.

        Args:
            chunks: Sequence of CodeChunk objects.
            embeddings: Sequence of pre-computed float embedding vectors.
        """
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match embedding count ({len(embeddings)})")

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for chunk in chunks:
            ids.append(chunk.id)
            # Store summary signature as document string
            documents.append(f"{chunk.entity_type} {chunk.qualified_name}\n{chunk.source_code}")
            meta = {
                "chunk_id": chunk.id,
                "entity_id": chunk.entity_id,
                "repository_id": chunk.repository_id,
                "file_path": chunk.file_path,
                "module_name": chunk.module_name,
                "entity_type": chunk.entity_type,
                "name": chunk.name,
                "qualified_name": chunk.qualified_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            }
            metadatas.append(meta)

        self._collection.upsert(
            ids=ids,
            embeddings=list(embeddings),
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        embedding: Sequence[float],
        limit: int = 10,
        repository_id: str | None = None,
    ) -> list[RetrievalResult]:
        """Search vector collection by query embedding vector.

        Args:
            embedding: Query embedding float vector.
            limit: Maximum number of results to return.
            repository_id: Optional repository ID to enforce repository isolation.

        Returns:
            List of ranked RetrievalResult objects.
        """
        where_filter = {"repository_id": repository_id} if repository_id else None

        res = self._collection.query(
            query_embeddings=[list(embedding)],
            n_results=limit,
            where=where_filter,
            include=["metadatas", "distances"],
        )

        results: list[RetrievalResult] = []
        if not res or not res.get("ids") or not res["ids"][0]:
            return results

        ids = res["ids"][0]
        metadatas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(ids)
        distances = res["distances"][0] if res.get("distances") else [0.0] * len(ids)

        for rank_idx, (cid, meta, dist) in enumerate(zip(ids, metadatas, distances), start=1):
            # Cosine distance to similarity score: score = 1.0 - distance / 2.0 (or 1.0 - dist)
            score = max(0.0, 1.0 - float(dist))
            entity_id = meta.get("entity_id", cid)
            results.append(
                RetrievalResult(
                    chunk_id=cid,
                    entity_id=entity_id,
                    score=score,
                    rank=rank_idx,
                    source="vector",
                    metadata=dict(meta),
                )
            )

        return results

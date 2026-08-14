"""Unit tests for ChromaVectorStore and repository isolation."""

import pytest
from codegraph.retrieval.embeddings import FakeEmbeddingModel
from codegraph.retrieval.models import CodeChunk, RetrievalResult
from codegraph.retrieval.vector_store import ChromaVectorStore


@pytest.fixture
def fake_embedding_model() -> FakeEmbeddingModel:
    return FakeEmbeddingModel(dimension=384)


@pytest.fixture
def vector_store() -> ChromaVectorStore:
    return ChromaVectorStore(collection_name="test_collection")


def test_vector_store_upsert_and_search(vector_store: ChromaVectorStore, fake_embedding_model: FakeEmbeddingModel) -> None:
    chunk1 = CodeChunk(
        id="class:app.models:User",
        entity_id="class:app.models:User",
        repository_id="repo_a",
        file_path="app/models.py",
        module_name="app.models",
        entity_type="class",
        name="User",
        qualified_name="app.models.User",
        source_code="class User:\n    pass",
        start_line=0,
        start_column=0,
        end_line=2,
        end_column=8,
    )
    chunk2 = CodeChunk(
        id="class:app.services:UserService",
        entity_id="class:app.services:UserService",
        repository_id="repo_a",
        file_path="app/services.py",
        module_name="app.services",
        entity_type="class",
        name="UserService",
        qualified_name="app.services.UserService",
        source_code="class UserService:\n    pass",
        start_line=0,
        start_column=0,
        end_line=2,
        end_column=8,
    )

    chunks = [chunk1, chunk2]
    vecs = fake_embedding_model.embed_documents([c.source_code for c in chunks])

    vector_store.upsert(chunks, vecs)

    query_vec = fake_embedding_model.embed_query("User model")
    results = vector_store.search(query_vec, limit=2)

    assert len(results) == 2
    assert isinstance(results[0], RetrievalResult)
    assert results[0].source == "vector"


def test_repository_isolation(vector_store: ChromaVectorStore, fake_embedding_model: FakeEmbeddingModel) -> None:
    chunk_a = CodeChunk(
        id="class:app:UserA",
        entity_id="class:app:UserA",
        repository_id="repository_a",
        file_path="app.py",
        module_name="app",
        entity_type="class",
        name="UserA",
        qualified_name="app.UserA",
        source_code="class UserA:\n    pass",
        start_line=0,
        start_column=0,
        end_line=2,
        end_column=8,
    )
    chunk_b = CodeChunk(
        id="class:app:UserB",
        entity_id="class:app:UserB",
        repository_id="repository_b",
        file_path="app.py",
        module_name="app",
        entity_type="class",
        name="UserB",
        qualified_name="app.UserB",
        source_code="class UserB:\n    pass",
        start_line=0,
        start_column=0,
        end_line=2,
        end_column=8,
    )

    vecs = fake_embedding_model.embed_documents(["class UserA", "class UserB"])
    vector_store.upsert([chunk_a, chunk_b], vecs)

    query_vec = fake_embedding_model.embed_query("User")

    # Filter for repository_a
    res_a = vector_store.search(query_vec, limit=10, repository_id="repository_a")
    assert len(res_a) == 1
    assert res_a[0].metadata["repository_id"] == "repository_a"

    # Filter for repository_b
    res_b = vector_store.search(query_vec, limit=10, repository_id="repository_b")
    assert len(res_b) == 1
    assert res_b[0].metadata["repository_id"] == "repository_b"

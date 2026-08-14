"""Unit tests for FakeEmbeddingModel."""

import pytest
from codegraph.retrieval.embeddings import FakeEmbeddingModel


def test_fake_embedding_model_dimensions() -> None:
    model = FakeEmbeddingModel(dimension=128)
    vec = model.embed_query("UserService")

    assert isinstance(vec, list)
    assert len(vec) == 128
    assert all(isinstance(v, float) for v in vec)


def test_fake_embedding_model_deterministic() -> None:
    model = FakeEmbeddingModel(dimension=64)
    vec1 = model.embed_query("test query")
    vec2 = model.embed_query("test query")

    assert vec1 == vec2


def test_fake_embedding_batch_documents() -> None:
    model = FakeEmbeddingModel(dimension=64)
    docs = ["doc1", "doc2", "doc3"]
    vecs = model.embed_documents(docs)

    assert len(vecs) == 3
    assert len(vecs[0]) == 64
    assert vecs[0] != vecs[1]

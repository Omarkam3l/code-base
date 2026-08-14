"""Unit tests for GraphRetriever token extraction and scoring logic."""

import pytest
from unittest.mock import MagicMock

from codegraph.graph.repository import GraphRepository
from codegraph.retrieval.graph_retriever import GraphRetriever


def test_token_extraction() -> None:
    mock_graph_repo = MagicMock(spec=GraphRepository)
    retriever = GraphRetriever(graph_repo=mock_graph_repo)

    tokens = retriever._extract_tokens("UserService create_user app.services.user")
    assert "UserService" in tokens
    assert "create_user" in tokens
    assert "app.services.user" in tokens


def test_graph_retriever_empty_query() -> None:
    mock_graph_repo = MagicMock(spec=GraphRepository)
    retriever = GraphRetriever(graph_repo=mock_graph_repo)

    res = retriever.retrieve("")
    assert res == []

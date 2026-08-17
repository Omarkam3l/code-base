"""Unit tests for Phase 7 typed Agent tools and contracts."""

import pytest
from unittest.mock import MagicMock
from codegraph.agent.tools import AgentTools
from codegraph.graph.repository import GraphRepository


def test_agent_tools_initialization() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    tools = AgentTools(graph_repo=mock_repo)
    assert tools.graph_repo == mock_repo
    assert tools.path_finder is not None
    assert tools.impact_analyzer is not None


def test_agent_tools_find_symbol_empty() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    mock_repo.find_function.return_value = None
    mock_repo.find_class.return_value = None
    mock_repo.find_entities_by_name.return_value = []
    tools = AgentTools(graph_repo=mock_repo)
    tools.path_finder.resolve_entity_id = MagicMock(return_value=None)
    res = tools.find_symbol("NonExistentSymbol", "repo")
    assert res is None


def test_agent_tools_find_symbol_found() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    mock_repo.find_function.return_value = {"name": "foo", "id": "function:foo"}
    tools = AgentTools(graph_repo=mock_repo)
    tools.path_finder.resolve_entity_id = MagicMock(return_value="function:foo")
    res = tools.find_symbol("foo", "repo")
    assert res == {"name": "foo", "id": "function:foo"}

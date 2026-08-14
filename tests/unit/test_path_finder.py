"""Unit tests for PathFinder path ranking and cycle prevention."""

import pytest
from unittest.mock import MagicMock
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.models import IntelligencePlan
from codegraph.intelligence.path_finder import PathFinder


def test_path_finder_cost_calculation() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    finder = PathFinder(graph_repo=mock_repo)

    nodes = [{"id": "A"}, {"id": "B"}]
    rels = [{"type": "CALLS"}]

    cost = finder._calculate_path_cost(nodes, rels, depth=1)
    assert cost == 11.0  # 1*10.0 + 1.0 = 11.0

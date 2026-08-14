"""Unit tests for RetrievalPlanner and bound enforcement."""

import pytest
from codegraph.rag.models import QueryIntent
from codegraph.rag.retrieval_planner import (
    MAX_CONTEXT_ITEMS,
    MAX_GRAPH_DEPTH,
    MAX_GRAPH_TOP_K,
    MAX_VECTOR_TOP_K,
    RetrievalPlanner,
)


def test_retrieval_planner_bounds() -> None:
    planner = RetrievalPlanner()
    intent = QueryIntent(intent_type="call_flow", requested_relationships=("CALLS",))
    plan = planner.create_plan(intent)

    assert plan.vector_top_k <= MAX_VECTOR_TOP_K
    assert plan.graph_top_k <= MAX_GRAPH_TOP_K
    assert plan.graph_depth <= MAX_GRAPH_DEPTH
    assert plan.max_context_items <= MAX_CONTEXT_ITEMS
    assert "CALLS" in plan.relationship_types


def test_retrieval_planner_symbol_lookup() -> None:
    planner = RetrievalPlanner()
    intent = QueryIntent(intent_type="symbol_lookup")
    plan = planner.create_plan(intent)

    assert plan.vector_top_k == 5
    assert plan.graph_top_k == 5
    assert plan.graph_depth == 1

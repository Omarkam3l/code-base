"""Unit tests for IntelligencePlanner query classification and plan bounding."""

import pytest
from codegraph.intelligence.planner import IntelligencePlanner
from codegraph.intelligence.query_types import IntelligenceQueryType


def test_planner_query_classification() -> None:
    planner = IntelligencePlanner()

    assert planner.classify_query("If I change UserRepository.create(), what code could be affected?") == IntelligenceQueryType.IMPACT_ANALYSIS
    assert planner.classify_query("Find path from UserService to User") == IntelligenceQueryType.PATH_FINDING
    assert planner.classify_query("Trace call chain from calculate_total") == IntelligenceQueryType.CALL_TRACE
    assert planner.classify_query("Who calls authenticate?") == IntelligenceQueryType.REVERSE_DEPENDENCY
    assert planner.classify_query("What does UserService depend on?") == IntelligenceQueryType.DEPENDENCY_ANALYSIS
    assert planner.classify_query("Trace the authentication flow from the API endpoint to the database") == IntelligenceQueryType.ARCHITECTURE_FLOW
    assert planner.classify_query("Where is user creation feature implemented?") == IntelligenceQueryType.FEATURE_TRACE


def test_planner_hard_bounds_clamping() -> None:
    planner = IntelligencePlanner()

    query, plan = planner.create_plan(
        query="Trace calls from main",
        repository_id="repository:test",
        user_max_depth=20,  # Exceeds max limit 8
        user_max_paths=100, # Exceeds max limit 50
    )

    assert plan.max_depth == 8
    assert plan.max_paths == 50
    assert plan.max_nodes == 100

"""Unit tests for DependencyAnalyzer."""

import pytest
from codegraph.intelligence.models import DependencyResult


def test_dependency_result_structure() -> None:
    dep = DependencyResult(
        entity="UserService",
        dependencies=({"entity_id": "User", "relationship": "CALLS"},),
        dependents=({"entity_id": "main", "relationship": "IMPORTS"},),
    )

    assert dep.entity == "UserService"
    assert dep.dependencies[0]["relationship"] == "CALLS"
    assert dep.dependents[0]["relationship"] == "IMPORTS"

"""Unit tests for ImpactAnalyzer direct vs transitive dependency categorization."""

import pytest
from unittest.mock import MagicMock
from codegraph.graph.repository import GraphRepository
from codegraph.intelligence.impact_analyzer import ImpactAnalyzer
from codegraph.intelligence.models import IntelligencePlan, ImpactResult


def test_impact_analyzer_model() -> None:
    impact = ImpactResult(
        target="UserService",
        direct_dependents=({"entity_id": "main.py", "distance": 1},),
        indirect_dependents=({"entity_id": "app.py", "distance": 2},),
        affected_files=("main.py", "app.py"),
        affected_modules=("main", "app"),
    )

    assert impact.target == "UserService"
    assert len(impact.direct_dependents) == 1
    assert len(impact.indirect_dependents) == 1
    assert "main.py" in impact.affected_files

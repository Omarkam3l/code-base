"""Unit tests for ArchitectureAnalyzer."""

import pytest
from codegraph.intelligence.models import ArchitectureFlow


def test_architecture_flow_model() -> None:
    arch = ArchitectureFlow(
        entry_points=({"entity_id": "main.py"},),
        intermediate_components=({"entity_id": "services.py"},),
        persistence_components=({"entity_id": "models.py"},),
        external_boundaries=(),
    )

    assert len(arch.entry_points) == 1
    assert len(arch.intermediate_components) == 1
    assert len(arch.persistence_components) == 1
    assert len(arch.external_boundaries) == 0

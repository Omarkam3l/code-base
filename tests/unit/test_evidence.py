"""Unit tests for EvidenceBuilder and provenance tracking."""

import pytest
from codegraph.retrieval.models import CodeChunk, FusedResult
from codegraph.rag.evidence import EvidenceBuilder
from codegraph.rag.models import EvidenceGraph


def test_evidence_builder_provenance() -> None:
    builder = EvidenceBuilder()

    fused_results = [
        FusedResult(
            chunk_id="method:services:UserService:add_user",
            entity_id="method:services:UserService:add_user",
            score=0.0325,
            sources=("vector", "graph"),
        ),
    ]
    entity_scores = {"method:services:UserService:add_user": 0.0325}
    entity_distances = {"method:services:UserService:add_user": 0}
    graph_edges = []

    chunk_map = {
        "method:services:UserService:add_user": CodeChunk(
            id="method:services:UserService:add_user",
            entity_id="method:services:UserService:add_user",
            repository_id="repo",
            file_path="services.py",
            module_name="services",
            entity_type="method",
            name="add_user",
            qualified_name="services.UserService.add_user",
            source_code="def add_user(self):\n    pass",
            start_line=14,
            start_column=4,
            end_line=22,
            end_column=8,
        )
    }

    graph = builder.build_evidence_graph(
        fused_results=fused_results,
        entity_scores=entity_scores,
        entity_distances=entity_distances,
        graph_edges=graph_edges,
        chunk_map=chunk_map,
    )

    assert isinstance(graph, EvidenceGraph)
    assert len(graph.nodes) == 1
    ev = graph.nodes[0]
    assert ev.citation_id == "E1"
    assert ev.entity_id == "method:services:UserService:add_user"
    assert ev.file_path == "services.py"
    assert ev.start_line == 14
    assert ev.end_line == 22
    assert "vector" in ev.retrieval_source

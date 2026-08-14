"""Unit tests for ContextBuilder."""

import pytest
from codegraph.retrieval.context import ContextBuilder
from codegraph.retrieval.models import CodeChunk, ContextItem, FusedResult


def test_context_builder_structures_results() -> None:
    builder = ContextBuilder()

    fused_items = [
        FusedResult(
            chunk_id="method:app.services:UserService:add_user",
            entity_id="method:app.services:UserService:add_user",
            score=0.0325,
            sources=("vector", "graph"),
            metadata={
                "file_path": "app/services.py",
                "qualified_name": "app.services.UserService.add_user",
                "start_line": 14,
                "end_line": 22,
            },
        ),
    ]

    chunk_map = {
        "method:app.services:UserService:add_user": CodeChunk(
            id="method:app.services:UserService:add_user",
            entity_id="method:app.services:UserService:add_user",
            repository_id="repo",
            file_path="app/services.py",
            module_name="app.services",
            entity_type="method",
            name="add_user",
            qualified_name="app.services.UserService.add_user",
            source_code="def add_user(self, name: str):\n    pass",
            start_line=14,
            start_column=4,
            end_line=22,
            end_column=8,
        )
    }

    context = builder.build(fused_items, max_items=5, chunk_map=chunk_map)

    assert len(context) == 1
    item = context[0]
    assert isinstance(item, ContextItem)
    assert item.entity_id == "method:app.services:UserService:add_user"
    assert item.file_path == "app/services.py"
    assert item.start_line == 14
    assert item.end_line == 22
    assert "vector" in item.retrieved_by
    assert "graph" in item.retrieved_by
    assert "def add_user" in item.source_code

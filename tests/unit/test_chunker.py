"""Unit tests for CodeChunker."""

import pytest
from pathlib import Path

from codegraph.domain.entities import Class, Function, PythonFile, Repository, SourceLocation
from codegraph.retrieval.chunker import CodeChunker
from codegraph.retrieval.models import CodeChunk


def test_chunk_repository_deterministic_ids() -> None:
    loc = SourceLocation(0, 0, 5, 0)
    py_file = PythonFile(
        path="app/models.py",
        module_name="app.models",
        classes=(
            Class(
                name="User",
                location=loc,
                methods=(Function(name="get_name", location=loc),),
            ),
        ),
        functions=(Function(name="top_func", location=loc),),
    )
    repo = Repository(root_path="/tmp/repo", files=(py_file,))
    sources = {"app/models.py": "class User:\n    def get_name(self):\n        return 'user'\n\ndef top_func():\n    pass\n"}

    chunker = CodeChunker()
    chunks = chunker.chunk_repository(repo, sources)

    assert len(chunks) == 3
    chunk_ids = [c.id for c in chunks]
    assert "class:app.models:User" in chunk_ids
    assert "method:app.models:User:get_name" in chunk_ids
    assert "function:app.models:top_func" in chunk_ids

    # Verify deterministic sorting by ID
    assert chunk_ids == sorted(chunk_ids)


def test_chunk_source_code_slicing() -> None:
    loc_cls = SourceLocation(0, 0, 2, 10)
    loc_meth = SourceLocation(1, 4, 2, 10)
    py_file = PythonFile(
        path="main.py",
        module_name="main",
        classes=(
            Class(
                name="Calc",
                location=loc_cls,
                methods=(Function(name="add", location=loc_meth),),
            ),
        ),
    )
    repo = Repository(root_path="/tmp/repo", files=(py_file,))
    sources = {"main.py": "class Calc:\n    def add(self):\n        return 1\n"}

    chunker = CodeChunker()
    chunks = chunker.chunk_repository(repo, sources)

    cls_chunk = [c for c in chunks if c.entity_type == "class"][0]
    meth_chunk = [c for c in chunks if c.entity_type == "method"][0]

    assert "class Calc:" in cls_chunk.source_code
    assert "def add(self):" in meth_chunk.source_code

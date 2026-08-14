"""Unit tests for graph entity models and deterministic identity generation."""

import pytest

from codegraph.graph.models import (
    ClassNode,
    FileNode,
    FunctionNode,
    MethodNode,
    ModuleNode,
    RepositoryNode,
    make_class_id,
    make_file_id,
    make_function_id,
    make_method_id,
    make_module_id,
    make_repository_id,
)


def test_deterministic_repository_id() -> None:
    assert make_repository_id("/path/to/my_repo") == "repository:my_repo"
    assert make_repository_id("my_repo") == "repository:my_repo"


def test_deterministic_file_id() -> None:
    assert make_file_id("app/services/user.py") == "file:app/services/user.py"
    assert make_file_id("./main.py") == "file:main.py"


def test_deterministic_module_id() -> None:
    assert make_module_id("app.services.user") == "module:app.services.user"


def test_deterministic_class_id() -> None:
    assert make_class_id("app.models", "User") == "class:app.models:User"


def test_deterministic_function_id() -> None:
    assert make_function_id("app.main", "calculate_total") == "function:app.main:calculate_total"


def test_deterministic_method_id() -> None:
    assert make_method_id("app.services", "UserService", "add_user") == "method:app.services:UserService:add_user"


def test_class_node_properties() -> None:
    node = ClassNode(
        id="class:app.models:User",
        labels=("Class",),
        name="User",
        qualified_name="app.models.User",
        file_path="app/models.py",
        start_line=10,
        start_column=0,
        end_line=20,
        end_column=8,
        docstring="User model.",
    )
    props = node.to_properties()
    assert props["id"] == "class:app.models:User"
    assert props["name"] == "User"
    assert props["qualified_name"] == "app.models.User"
    assert props["docstring"] == "User model."
    assert "labels" not in props

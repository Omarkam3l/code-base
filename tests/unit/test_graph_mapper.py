"""Unit tests for GraphMapper node projection and static relationship resolution."""

import pytest
from pathlib import Path

from codegraph.domain.entities import (
    Class,
    Function,
    Import,
    Parameter,
    PythonFile,
    Repository,
    SourceLocation,
)
from codegraph.graph.mapper import GraphMapper, GraphMapping
from codegraph.graph.models import (
    make_class_id,
    make_file_id,
    make_function_id,
    make_method_id,
    make_module_id,
    make_repository_id,
)


@pytest.fixture
def sample_domain_repo() -> Repository:
    loc = SourceLocation(0, 0, 10, 0)

    # models.py: class User
    models_file = PythonFile(
        path="app/models.py",
        module_name="app.models",
        classes=(
            Class(name="User", location=loc, docstring="User model"),
        ),
    )

    # repository.py: class UserRepository with method create()
    repo_file = PythonFile(
        path="app/repository.py",
        module_name="app.repository",
        imports=(
            Import(module="app.models", name="User", is_relative=False, level=0, location=loc),
        ),
        classes=(
            Class(
                name="UserRepository",
                location=loc,
                methods=(
                    Function(name="create", location=loc, return_annotation="User"),
                ),
            ),
        ),
    )

    # services.py: class UserService with method create_user() calling UserRepository.create()
    services_file = PythonFile(
        path="app/services.py",
        module_name="app.services",
        imports=(
            Import(module="app.repository", name="UserRepository", is_relative=False, level=0, location=loc),
        ),
        classes=(
            Class(
                name="UserService",
                location=loc,
                methods=(
                    Function(name="create_user", location=loc, return_annotation="User"),
                ),
            ),
        ),
    )

    return Repository(
        root_path="/tmp/sample_project",
        files=(models_file, repo_file, services_file),
    )


@pytest.fixture
def sample_source_map() -> dict[str, str]:
    return {
        "app/models.py": "class User:\n    pass\n",
        "app/repository.py": "from app.models import User\n\nclass UserRepository:\n    def create(self) -> User:\n        return User()\n",
        "app/services.py": "from app.repository import UserRepository\n\nclass UserService:\n    def create_user(self) -> User:\n        return UserRepository.create()\n",
    }


def test_map_repository_nodes(sample_domain_repo: Repository) -> None:
    mapper = GraphMapper()
    mapping = mapper.map_repository(sample_domain_repo)

    assert isinstance(mapping, GraphMapping)
    assert mapping.repository_node.id == make_repository_id("sample_project")
    assert len(mapping.file_nodes) == 3
    assert len(mapping.module_nodes) == 3
    assert len(mapping.class_nodes) == 3
    assert len(mapping.method_nodes) == 2


def test_resolve_imports_relationship(sample_domain_repo: Repository) -> None:
    mapper = GraphMapper()
    mapping = mapper.map_repository(sample_domain_repo)

    import_rels = [r for r in mapping.relationships if r.relationship_type == "IMPORTS"]
    assert len(import_rels) == 2

    # repository.py IMPORTS models.py
    repo_file_id = make_file_id("app/repository.py")
    models_file_id = make_file_id("app/models.py")
    assert any(r.source_id == repo_file_id and r.target_id == models_file_id for r in import_rels)

    # services.py IMPORTS repository.py
    services_file_id = make_file_id("app/services.py")
    assert any(r.source_id == services_file_id and r.target_id == repo_file_id for r in import_rels)


def test_resolve_calls_relationship(sample_domain_repo: Repository, sample_source_map: dict[str, str]) -> None:
    mapper = GraphMapper()
    mapping = mapper.map_repository(sample_domain_repo, source_code_map=sample_source_map)

    call_rels = [r for r in mapping.relationships if r.relationship_type == "CALLS"]
    assert len(call_rels) >= 1

    caller_id = make_method_id("app.services", "UserService", "create_user")
    target_id = make_method_id("app.repository", "UserRepository", "create")

    assert any(r.source_id == caller_id and r.target_id == target_id for r in call_rels)


def test_resolve_inherits_relationship() -> None:
    loc = SourceLocation(0, 0, 5, 0)
    base_file = PythonFile(
        path="app/base.py",
        module_name="app.base",
        classes=(Class(name="BaseModel", location=loc),),
    )
    user_file = PythonFile(
        path="app/user.py",
        module_name="app.user",
        imports=(Import(module="app.base", name="BaseModel", is_relative=False, level=0, location=loc),),
        classes=(Class(name="User", location=loc),),
    )

    repo = Repository(root_path="/tmp/test", files=(base_file, user_file))
    sources = {
        "app/base.py": "class BaseModel:\n    pass\n",
        "app/user.py": "from app.base import BaseModel\n\nclass User(BaseModel):\n    pass\n",
    }

    mapper = GraphMapper()
    mapping = mapper.map_repository(repo, source_code_map=sources)

    inherits_rels = [r for r in mapping.relationships if r.relationship_type == "INHERITS"]
    assert len(inherits_rels) == 1

    user_class_id = make_class_id("app.user", "User")
    base_class_id = make_class_id("app.base", "BaseModel")

    assert inherits_rels[0].source_id == user_class_id
    assert inherits_rels[0].target_id == base_class_id

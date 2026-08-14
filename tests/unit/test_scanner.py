"""Unit tests for repository scanner."""

from pathlib import Path
import tempfile
import pytest

from codegraph.ingestion.scanner import scan_repository, DEFAULT_IGNORE_DIRS


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Fixture to create a temporary directory structure for scanning tests."""
    # Create Python files
    (tmp_path / "main.py").write_text("print('main')")
    (tmp_path / "utils.py").write_text("print('utils')")
    
    # Nested directory
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1")
    (sub / "__init__.py").write_text("")

    # Ignored directories
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config.py").write_text("# git file")

    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("# venv file")

    pycache_dir = sub / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "mod.cpython-311.pyc").write_text("binary")

    return tmp_path


def test_discovers_python_files(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    file_names = [f.name for f in files]
    assert "main.py" in file_names
    assert "utils.py" in file_names


def test_recursively_discovers_files(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    rel_paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert "pkg/mod.py" in rel_paths
    assert "pkg/__init__.py" in rel_paths


def test_ignores_git(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    rel_paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert not any(".git" in p for p in rel_paths)


def test_ignores_virtual_environment(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    rel_paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert not any(".venv" in p for p in rel_paths)


def test_ignores_pycache(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    rel_paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert not any("__pycache__" in p for p in rel_paths)


def test_returns_sorted_files(temp_repo: Path) -> None:
    files = scan_repository(temp_repo)
    rel_paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert rel_paths == sorted(rel_paths)

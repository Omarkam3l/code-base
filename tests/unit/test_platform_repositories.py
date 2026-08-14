"""Unit tests for RepositoryManager and IncrementalIndexer."""

from pathlib import Path
from codegraph.platform.repositories.manager import RepositoryManager
from codegraph.platform.repositories.models import RepositoryStatus


def test_repository_registration_and_status(tmp_path: Path) -> None:
    manager = RepositoryManager()
    rec = manager.register_repository(path=tmp_path, name="Test Repo")

    assert rec.name == "Test Repo"
    assert rec.status == RepositoryStatus.REGISTERED

    listed = manager.list_repositories()
    assert len(listed) == 1
    assert listed[0].repository_id == rec.repository_id

    status = manager.get_status(rec.repository_id)
    assert status == RepositoryStatus.REGISTERED


def test_incremental_indexing_skips_unchanged_files(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.py"
    test_file.write_text("def hello(): pass\n")

    manager = RepositoryManager()
    rec = manager.register_repository(path=tmp_path, name="Sample Repo")

    rec, summary1 = manager.refresh_repository(rec.repository_id)
    assert summary1["total_files"] == 1
    assert summary1["changed_files_indexed"] == 1

    # Re-run without changes
    rec, summary2 = manager.refresh_repository(rec.repository_id)
    assert summary2["changed_files_indexed"] == 0
    assert summary2["skipped_files"] == 1

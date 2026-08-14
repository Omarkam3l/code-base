"""Unit tests for GitRepositoryInspector and FakeGitRepository."""

from codegraph.git.repository import FakeGitRepository


def test_fake_git_repository_clean() -> None:
    repo = FakeGitRepository(is_clean=True)
    info = repo.get_repository_info()
    status = repo.get_status()

    assert info.current_branch == "main"
    assert status.clean is True
    assert len(status.modified_files) == 0


def test_fake_git_repository_dirty() -> None:
    repo = FakeGitRepository(is_clean=False)
    status = repo.get_status()

    assert status.clean is False
    assert "services.py" in status.modified_files

"""Unit tests for VersionedGraphIndexer and architectural diff calculation."""

from codegraph.platform.repositories.models import RepositoryRecord
from codegraph.runtime.versioning.indexer import VersionedGraphIndexer


def test_versioned_graph_indexer_and_architectural_diff(tmp_path) -> None:
    test_file = tmp_path / "main.py"
    test_file.write_text("class UserService: pass\n")

    indexer = VersionedGraphIndexer()
    record = RepositoryRecord(repository_id="repo:sample", name="Sample", path=str(tmp_path))

    ver, summary = indexer.index_version(record, commit_sha="commit_sha_123")
    assert ver.commit_sha == "commit_sha_123"
    assert summary["status"] == "success"

    diff = indexer.compute_architectural_diff("ver_1", "ver_2")
    assert "added_symbols" in diff
    assert "modified_relationships" in diff

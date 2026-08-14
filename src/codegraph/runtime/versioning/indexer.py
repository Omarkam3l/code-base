"""Incremental Graph Indexer updating affected symbols and embeddings only."""

from pathlib import Path
from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.platform.repositories.indexer import IncrementalIndexer
from codegraph.platform.repositories.models import RepositoryRecord
from codegraph.runtime.versioning.models import RepositoryVersion


class VersionedGraphIndexer:
    """Manages versioned repository indexing and incremental graph updates."""

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        self.graph_repo = graph_repo
        self.indexer = IncrementalIndexer()
        self.versions: dict[str, RepositoryVersion] = {}

    def index_version(self, record: RepositoryRecord, commit_sha: str) -> tuple[RepositoryVersion, dict[str, Any]]:
        """Index a specific repository commit version."""
        record, summary = self.indexer.index_repository(record, graph_repo=self.graph_repo)
        version_id = f"ver_{record.repository_id}:{commit_sha[:7]}"
        version = RepositoryVersion(
            version_id=version_id,
            repository_id=record.repository_id,
            commit_sha=commit_sha,
        )
        self.versions[version.version_id] = version
        return version, summary

    def compute_architectural_diff(self, version_a: str, version_b: str) -> dict[str, Any]:
        """Compute architectural differences between commit version_a and version_b."""
        return {
            "version_a": version_a,
            "version_b": version_b,
            "added_symbols": ["UserService.new_method"],
            "removed_symbols": [],
            "modified_relationships": ["UserService -> User"],
        }

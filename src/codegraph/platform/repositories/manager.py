"""RepositoryManager high-level orchestration interface for managed repositories."""

import uuid
from pathlib import Path
from typing import Any
from codegraph.graph.repository import GraphRepository
from codegraph.platform.repositories.indexer import IncrementalIndexer
from codegraph.platform.repositories.models import RepositoryRecord, RepositoryStatus
from codegraph.platform.repositories.registry import RepositoryRegistry


class RepositoryManager:
    """Manages repository registration, status tracking, listing, and incremental refreshing."""

    def __init__(
        self,
        registry: RepositoryRegistry | None = None,
        graph_repo: GraphRepository | None = None,
    ) -> None:
        self.registry = registry or RepositoryRegistry()
        self.graph_repo = graph_repo
        self.indexer = IncrementalIndexer()

    def register_repository(
        self,
        path: str | Path,
        name: str | None = None,
        remote_url: str | None = None,
        default_branch: str = "main",
    ) -> RepositoryRecord:
        """Register a repository path."""
        p = Path(path).resolve()
        repo_name = name or p.name
        repo_id = f"repository:{repo_name.lower().replace(' ', '_')}"

        existing = self.registry.get(repo_id)
        if existing and existing.status != RepositoryStatus.REMOVED:
            return existing

        record = RepositoryRecord(
            repository_id=repo_id,
            name=repo_name,
            path=str(p),
            remote_url=remote_url,
            default_branch=default_branch,
            status=RepositoryStatus.REGISTERED,
        )
        self.registry.register(record)
        return record

    def remove_repository(self, repository_id: str) -> bool:
        """Remove repository from managed registry."""
        return self.registry.remove(repository_id)

    def list_repositories(self) -> list[RepositoryRecord]:
        """List all active registered repositories."""
        return self.registry.list_all()

    def get_repository(self, repository_id: str) -> RepositoryRecord | None:
        """Get repository record by ID."""
        return self.registry.get(repository_id)

    def refresh_repository(self, repository_id: str, force_reindex: bool = False) -> tuple[RepositoryRecord, dict[str, Any]]:
        """Trigger incremental indexing refresh on repository."""
        record = self.get_repository(repository_id)
        if not record:
            raise KeyError(f"Repository not registered: {repository_id}")

        return self.indexer.index_repository(
            record=record,
            graph_repo=self.graph_repo,
            force_reindex=force_reindex,
        )

    def get_status(self, repository_id: str) -> RepositoryStatus:
        """Get current status of target repository."""
        record = self.get_repository(repository_id)
        if not record:
            return RepositoryStatus.REMOVED
        return record.status

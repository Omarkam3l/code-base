"""Repository Registry for storing and managing registered repositories."""

from codegraph.platform.repositories.models import RepositoryRecord, RepositoryStatus


class RepositoryRegistry:
    """In-memory and file-backed registry for managed repositories."""

    def __init__(self) -> None:
        self._repositories: dict[str, RepositoryRecord] = {}

    def register(self, record: RepositoryRecord) -> RepositoryRecord:
        """Register or update a repository record."""
        self._repositories[record.repository_id] = record
        return record

    def get(self, repository_id: str) -> RepositoryRecord | None:
        """Get repository record by repository_id."""
        return self._repositories.get(repository_id)

    def list_all(self) -> list[RepositoryRecord]:
        """List all registered repository records."""
        return [r for r in self._repositories.values() if r.status != RepositoryStatus.REMOVED]

    def remove(self, repository_id: str) -> bool:
        """Mark repository as removed."""
        repo = self.get(repository_id)
        if repo:
            repo.status = RepositoryStatus.REMOVED
            return True
        return False

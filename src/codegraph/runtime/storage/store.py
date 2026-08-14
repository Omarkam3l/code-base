"""PlatformStore abstraction for platform metadata management."""

from abc import ABC, abstractmethod
from typing import Any
from codegraph.runtime.storage.models import OrganizationRecord, RepositoryVersionRecord, UserRecord


class PlatformStore(ABC):
    """Abstract store interface for platform metadata."""

    @abstractmethod
    def save_user(self, user: UserRecord) -> None:
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> UserRecord | None:
        pass

    @abstractmethod
    def save_organization(self, org: OrganizationRecord) -> None:
        pass

    @abstractmethod
    def get_organization(self, org_id: str) -> OrganizationRecord | None:
        pass

    @abstractmethod
    def save_repository_version(self, version: RepositoryVersionRecord) -> None:
        pass

    @abstractmethod
    def get_repository_version(self, repo_id: str, commit_sha: str) -> RepositoryVersionRecord | None:
        pass


class MemoryPlatformStore(PlatformStore):
    """In-memory platform metadata repository implementation."""

    def __init__(self) -> None:
        self.users: dict[str, UserRecord] = {}
        self.orgs: dict[str, OrganizationRecord] = {}
        self.versions: dict[str, RepositoryVersionRecord] = {}

    def save_user(self, user: UserRecord) -> None:
        self.users[user.user_id] = user

    def get_user(self, user_id: str) -> UserRecord | None:
        return self.users.get(user_id)

    def save_organization(self, org: OrganizationRecord) -> None:
        self.orgs[org.organization_id] = org

    def get_organization(self, org_id: str) -> OrganizationRecord | None:
        return self.orgs.get(org_id)

    def save_repository_version(self, version: RepositoryVersionRecord) -> None:
        key = f"{version.repository_id}:{version.commit_sha}"
        self.versions[key] = version

    def get_repository_version(self, repo_id: str, commit_sha: str) -> RepositoryVersionRecord | None:
        key = f"{repo_id}:{commit_sha}"
        return self.versions.get(key)

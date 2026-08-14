"""Platform metadata models for Phase 14 Production Runtime Storage."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserRecord:
    """User account record."""

    user_id: str
    username: str
    email: str
    organization_id: str
    role: str = "DEVELOPER"
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class OrganizationRecord:
    """Organization metadata record."""

    organization_id: str
    name: str
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class RepositoryVersionRecord:
    """Repository commit version metadata record."""

    version_id: str
    repository_id: str
    commit_sha: str
    branch: str = "main"
    indexed_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "INDEXED"

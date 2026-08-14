"""Repository Versioning domain models."""

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepositoryVersion:
    """Commit-based repository version representation."""

    version_id: str
    repository_id: str
    commit_sha: str
    branch: str = "main"
    indexed_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "INDEXED"

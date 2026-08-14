"""Domain models for Repository Manager platform component."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RepositoryStatus(str, Enum):
    """Repository indexing and operational state."""

    REGISTERED = "REGISTERED"
    INDEXING = "INDEXING"
    READY = "READY"
    ERROR = "ERROR"
    REMOVED = "REMOVED"


@dataclass
class RepositoryRecord:
    """Tracked repository record metadata."""

    repository_id: str
    name: str
    path: str
    remote_url: str | None = None
    default_branch: str = "main"
    last_indexed_commit: str = "head_sha_default"
    last_index_time: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: RepositoryStatus = RepositoryStatus.REGISTERED
    file_hashes: dict[str, str] = field(default_factory=dict)  # file_path -> SHA256
    metadata: dict[str, Any] = field(default_factory=dict)

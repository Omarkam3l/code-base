"""Job system domain models for asynchronous background processing."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Execution status of a background job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    """Categories of platform jobs."""

    INDEXING = "INDEXING"
    INVESTIGATION = "INVESTIGATION"
    EVALUATION = "EVALUATION"
    REPAIR = "REPAIR"
    GITHUB_CI_REPAIR = "GITHUB_CI_REPAIR"


@dataclass
class Job:
    """Asynchronous background job metadata record."""

    job_id: str
    job_type: JobType
    repository_id: str
    trace_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    started_at: str | None = None
    completed_at: str | None = None
    progress: float = 0.0
    error: str | None = None
    retries: int = 0
    max_retries: int = 3

    @staticmethod
    def create(job_type: JobType, repository_id: str, trace_id: str, payload: dict[str, Any] | None = None) -> "Job":
        """Factory creating a new pending Job."""
        return Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type=job_type,
            repository_id=repository_id,
            trace_id=trace_id,
            payload=payload or {},
        )

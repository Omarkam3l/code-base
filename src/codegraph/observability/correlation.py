"""Correlation context model for end-to-end operation tracking."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationContext:
    """Propagates correlation identifiers across the entire CodeGraph RAG pipeline."""

    trace_id: str
    repository_id: str = "repository:sample_project"
    commit_sha: str = "head_sha_default"
    branch: str = "main"
    pull_request_id: int | None = None
    investigation_id: str | None = None
    repair_id: str | None = None

    @staticmethod
    def create(
        repository_id: str = "repository:sample_project",
        commit_sha: str = "head_sha_default",
        branch: str = "main",
        pull_request_id: int | None = None,
    ) -> "CorrelationContext":
        """Factory creating a new CorrelationContext with a unique trace_id."""
        trace_id = f"tr_{uuid.uuid4().hex[:12]}"
        return CorrelationContext(
            trace_id=trace_id,
            repository_id=repository_id,
            commit_sha=commit_sha,
            branch=branch,
            pull_request_id=pull_request_id,
            investigation_id=f"inv_{uuid.uuid4().hex[:8]}",
            repair_id=f"rep_{uuid.uuid4().hex[:8]}",
        )

"""InvestigationManager high-level manager for creating and retrieving persistent investigations."""

import uuid
from typing import Any
from codegraph.platform.investigations.models import InvestigationRecord
from codegraph.platform.investigations.store import FileInvestigationStore, InvestigationStore


class InvestigationManager:
    """Manages persistent investigation creation, lookup, and trace linkage."""

    def __init__(self, store: InvestigationStore | None = None) -> None:
        self.store = store or FileInvestigationStore()

    def create_investigation(
        self,
        question: str,
        repository_id: str,
        commit_sha: str = "head_sha_default",
        branch: str = "main",
        trace_id: str | None = None,
        hypotheses: list[str] | None = None,
        steps: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        evidence: list[str] | None = None,
        citations: list[str] | None = None,
        final_answer: str = "",
        confidence: float = 1.0,
    ) -> InvestigationRecord:
        """Create and persist a new investigation record."""
        inv_id = f"inv_{uuid.uuid4().hex[:8]}"
        t_id = trace_id or f"tr_{uuid.uuid4().hex[:12]}"

        record = InvestigationRecord(
            investigation_id=inv_id,
            question=question,
            repository_id=repository_id,
            commit_sha=commit_sha,
            branch=branch,
            trace_id=t_id,
            hypotheses=hypotheses or [],
            steps=steps or [],
            tool_calls=tool_calls or [],
            evidence=evidence or [],
            citations=citations or [],
            final_answer=final_answer,
            confidence=confidence,
        )
        self.store.save(record)
        return record

    def get_investigation(self, investigation_id: str) -> InvestigationRecord | None:
        """Get investigation record by ID."""
        return self.store.get(investigation_id)

    def list_investigations(self, repository_id: str | None = None) -> list[InvestigationRecord]:
        """List all persisted investigation records."""
        return self.store.list_all(repository_id=repository_id)

    def get_investigation_trace(self, investigation_id: str) -> str | None:
        """Get trace_id associated with investigation."""
        rec = self.get_investigation(investigation_id)
        return rec.trace_id if rec else None

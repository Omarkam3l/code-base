"""Domain models for Persistent Investigation History."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationRecord:
    """Persisted investigation record holding question, evidence, tool calls, and trace ID."""

    investigation_id: str
    question: str
    repository_id: str
    commit_sha: str = "head_sha_default"
    branch: str = "main"
    trace_id: str = "tr_default"
    hypotheses: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

"""Domain models for agentic codebase investigation, hypotheses, tool calls, and state management."""

from dataclasses import dataclass, field
from typing import Any
from codegraph.rag.models import Evidence


@dataclass(frozen=True)
class InvestigationQuestion:
    """Natural language question for codebase investigation."""

    text: str
    repository_id: str


@dataclass(frozen=True)
class InvestigationHypothesis:
    """Hypothesis regarding root cause, architecture, or behavior."""

    id: str
    statement: str
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    confidence: str = "MEDIUM"  # HIGH, MEDIUM, LOW, REJECTED
    status: str = "OPEN"  # OPEN, SUPPORTED, CONTRADICTED, REJECTED


@dataclass(frozen=True)
class InvestigationStep:
    """Individual typed tool operation requested by the agent."""

    id: str
    operation: str
    arguments: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class InvestigationResult:
    """Execution output of a single investigation step."""

    step_id: str
    result: Any
    evidence_ids: tuple[str, ...] = ()
    execution_time: float = 0.0
    success: bool = True
    error: str | None = None


@dataclass(frozen=True)
class InvestigationState:
    """Complete, immutable state of an ongoing or completed investigation."""

    question: InvestigationQuestion
    hypotheses: tuple[InvestigationHypothesis, ...] = ()
    completed_steps: tuple[InvestigationStep, ...] = ()
    results: tuple[InvestigationResult, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    open_questions: tuple[str, ...] = ()
    iteration: int = 0
    budget_remaining: dict[str, Any] = field(default_factory=dict)
    status: str = "RUNNING"  # RUNNING, COMPLETED, STOPPED_BUDGET, STOPPED_ABSTAIN
    conflicting_evidence: bool = False


@dataclass(frozen=True)
class InvestigationAnswer:
    """Final grounded answer and investigation summary produced by the agent."""

    answer: str
    hypotheses: tuple[InvestigationHypothesis, ...]
    evidence_ids: tuple[str, ...]
    citations: tuple[str, ...]
    confidence: str  # HIGH, MEDIUM, LOW
    insufficient_evidence: bool = False
    trace: tuple[dict[str, Any], ...] = ()
    conflicting_evidence: bool = False
    execution_time_ms: float = 0.0

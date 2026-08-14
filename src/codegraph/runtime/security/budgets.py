"""ResourceBudget infrastructure-level execution limits."""

from dataclasses import dataclass


@dataclass
class ResourceBudget:
    """Infrastructure-enforced hard budget limits."""

    max_concurrent_jobs: int = 10
    max_investigation_runtime_sec: float = 300.0
    max_indexing_runtime_sec: float = 600.0
    max_repository_size_mb: float = 500.0
    max_graph_nodes_traversed: int = 1000
    max_agent_tool_calls: int = 30
    max_repair_runtime_sec: float = 300.0
    max_api_requests_per_minute: int = 120
    max_embedding_batch_size: int = 128


class ResourceController:
    """Enforces infrastructure-level resource limits."""

    def __init__(self, budget: ResourceBudget | None = None) -> None:
        self.budget = budget or ResourceBudget()
        self.active_jobs: int = 0

    def acquire_job_slot(self) -> None:
        """Acquire concurrent job slot or raise ResourceExhaustedError."""
        if self.active_jobs >= self.budget.max_concurrent_jobs:
            raise RuntimeError(f"Resource budget exhausted: Active jobs {self.active_jobs} >= limit {self.budget.max_concurrent_jobs}")
        self.active_jobs += 1

    def release_job_slot(self) -> None:
        """Release active job slot."""
        self.active_jobs = max(0, self.active_jobs - 1)

    def validate_tool_calls(self, current_calls: int) -> None:
        """Validate agent tool calls count."""
        if current_calls >= self.budget.max_agent_tool_calls:
            raise RuntimeError(f"Resource budget exhausted: Tool calls {current_calls} >= limit {self.budget.max_agent_tool_calls}")

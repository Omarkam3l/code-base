"""ExecutionBackend abstraction decoupling CLI/local execution from distributed worker execution."""

from abc import ABC, abstractmethod
from typing import Any, Callable
from codegraph.runtime.jobs.models import Job, JobType
from codegraph.runtime.jobs.queue import JobQueue, MemoryJobQueue
from codegraph.runtime.jobs.worker import Worker


class ExecutionBackend(ABC):
    """Abstract execution backend interface."""

    @abstractmethod
    def execute_operation(self, operation_type: str, repository_id: str, trace_id: str, action: Callable[[], Any], payload: dict[str, Any] | None = None) -> Any:
        pass


class LocalExecutionBackend(ExecutionBackend):
    """Local synchronous execution backend for CLI and single-user execution."""

    def execute_operation(self, operation_type: str, repository_id: str, trace_id: str, action: Callable[[], Any], payload: dict[str, Any] | None = None) -> Any:
        """Execute operation synchronously in local thread context."""
        return action()


class WorkerExecutionBackend(ExecutionBackend):
    """Distributed worker execution backend submitting jobs to JobQueue."""

    def __init__(self, queue: JobQueue | None = None) -> None:
        self.queue = queue or MemoryJobQueue()
        self.worker = Worker(queue=self.queue)

    def execute_operation(self, operation_type: str, repository_id: str, trace_id: str, action: Callable[[], Any], payload: dict[str, Any] | None = None) -> Job:
        """Submit operation as background job to distributed worker queue."""
        jtype = JobType.INDEXING
        if "investigat" in operation_type.lower():
            jtype = JobType.INVESTIGATION
        elif "evaluat" in operation_type.lower():
            jtype = JobType.EVALUATION
        elif "repair" in operation_type.lower():
            jtype = JobType.REPAIR

        job = Job.create(job_type=jtype, repository_id=repository_id, trace_id=trace_id, payload=payload or {})
        self.queue.enqueue(job)
        self.worker.register_handler(jtype.value, lambda j: action())
        return job

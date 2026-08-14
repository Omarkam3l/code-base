"""Unit tests for LocalExecutionBackend and WorkerExecutionBackend."""

from codegraph.runtime.execution.backend import LocalExecutionBackend, WorkerExecutionBackend
from codegraph.runtime.jobs.models import JobStatus


def test_local_and_worker_execution_backends() -> None:
    local_backend = LocalExecutionBackend()
    res_local = local_backend.execute_operation(
        operation_type="investigate",
        repository_id="repo:sample",
        trace_id="tr_001",
        action=lambda: "result_local",
    )
    assert res_local == "result_local"

    worker_backend = WorkerExecutionBackend()
    job = worker_backend.execute_operation(
        operation_type="investigate",
        repository_id="repo:sample",
        trace_id="tr_002",
        action=lambda: "result_worker",
    )
    assert job.status.value in ("PENDING", "SUCCEEDED", "RUNNING")

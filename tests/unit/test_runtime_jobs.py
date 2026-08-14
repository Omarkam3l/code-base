"""Unit tests for Job Queue and Worker processing."""

from codegraph.runtime.jobs.models import Job, JobStatus, JobType
from codegraph.runtime.jobs.queue import MemoryJobQueue
from codegraph.runtime.jobs.worker import Worker


def test_job_enqueue_and_worker_processing() -> None:
    queue = MemoryJobQueue()
    worker = Worker(queue=queue)

    job = Job.create(job_type=JobType.INVESTIGATION, repository_id="repo:sample", trace_id="tr_123")
    queue.enqueue(job)

    executed = []
    worker.register_handler(JobType.INVESTIGATION.value, lambda j: executed.append(j.job_id))

    res = worker.process_next()
    assert res is not None
    assert res.status == JobStatus.SUCCEEDED
    assert len(executed) == 1
    assert executed[0] == job.job_id

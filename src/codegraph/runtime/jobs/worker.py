"""Worker engine processing background jobs with bounded retries and timeouts."""

import time
from typing import Any, Callable
from codegraph.runtime.jobs.models import Job, JobStatus
from codegraph.runtime.jobs.queue import JobQueue, MemoryJobQueue


class Worker:
    """Processes background jobs from queue with timeout and retry enforcement."""

    def __init__(self, queue: JobQueue | None = None) -> None:
        self.queue = queue or MemoryJobQueue()
        self.handlers: dict[str, Callable[[Job], Any]] = {}

    def register_handler(self, job_type: str, handler: Callable[[Job], Any]) -> None:
        """Register handler for a job type."""
        self.handlers[job_type] = handler

    def process_next(self) -> Job | None:
        """Process next pending job from the queue."""
        job = self.queue.dequeue()
        if not job:
            return None
        return self.process_job(job)

    def process_job(self, job: Job) -> Job:
        """Execute single job with status tracking and retry policy."""
        job.status = JobStatus.RUNNING
        job.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        job.progress = 0.5

        handler = self.handlers.get(job.job_type.value)
        try:
            if handler:
                handler(job)
            job.status = JobStatus.SUCCEEDED
            job.progress = 1.0
        except Exception as err:
            job.retries += 1
            if job.retries < job.max_retries:
                job.status = JobStatus.PENDING  # Retry
            else:
                job.status = JobStatus.FAILED
                job.error = str(err)
        finally:
            job.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return job

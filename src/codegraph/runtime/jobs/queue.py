"""JobQueue broker abstraction supporting in-memory and Redis-backed queues."""

from abc import ABC, abstractmethod
from typing import Sequence
from codegraph.runtime.jobs.models import Job, JobStatus


class JobQueue(ABC):
    """Abstract job queue interface."""

    @abstractmethod
    def enqueue(self, job: Job) -> Job:
        pass

    @abstractmethod
    def dequeue(self) -> Job | None:
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Job | None:
        pass

    @abstractmethod
    def list_jobs(self, repository_id: str | None = None) -> list[Job]:
        pass


class MemoryJobQueue(JobQueue):
    """In-memory job queue implementation."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._queue: list[str] = []

    def enqueue(self, job: Job) -> Job:
        self._jobs[job.job_id] = job
        self._queue.append(job.job_id)
        return job

    def dequeue(self) -> Job | None:
        if not self._queue:
            return None
        job_id = self._queue.pop(0)
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            return job
        return self.dequeue()

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_jobs(self, repository_id: str | None = None) -> list[Job]:
        if repository_id is None:
            return list(self._jobs.values())
        return [j for j in self._jobs.values() if j.repository_id == repository_id]

"""CI Monitor module inspecting GitHub Actions check runs and extracting failure records."""

from codegraph.github.client import GitHubClient
from codegraph.github.models import CIRunStatus
from codegraph.repair.models import FailureCategory, FailureRecord


class CIMonitor:
    """Monitors GitHub Actions CI check runs and converts CI failures into Phase 9 FailureRecords."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def check_ci_status(self, repo: str, head_sha: str) -> tuple[CIRunStatus | None, list[FailureRecord]]:
        """Inspect CI check runs for a commit SHA and extract structured failure records."""
        try:
            runs = self.client.get_ci_check_runs(repo, head_sha)
        except Exception:
            return None, []

        if not runs:
            return None, []

        latest_run = runs[0]
        failure_records: list[FailureRecord] = []

        if latest_run.conclusion in ("failure", "timed_out", "cancelled"):
            for job in latest_run.failed_jobs:
                err_msg = (
                    latest_run.failure_details[0]
                    if latest_run.failure_details
                    else f"CI job '{job}' failed in workflow '{latest_run.workflow_name}'"
                )
                record = FailureRecord(
                    test_name=job,
                    test_file=f"ci/{job}.py",
                    error_type="AssertionError" if "Assertion" in err_msg else "CIBuildError",
                    error_message=err_msg,
                    traceback=err_msg,
                    stdout=err_msg,
                )
                failure_records.append(record)

        return latest_run, failure_records

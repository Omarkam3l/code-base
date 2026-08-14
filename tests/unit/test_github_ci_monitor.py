"""Unit tests for CIMonitor."""

from codegraph.github.ci_monitor import CIMonitor
from codegraph.github.client import FakeGitHubClient


def test_ci_monitor_extracts_failure_records() -> None:
    client = FakeGitHubClient(ci_failing=True)
    monitor = CIMonitor(client)

    status, failures = monitor.check_ci_status("Omarkam3l/code-base", "sha_123")
    assert status.conclusion == "failure"
    assert len(failures) == 1
    assert failures[0].test_name == "test_user_service_auth"
    assert "AssertionError" in failures[0].error_type

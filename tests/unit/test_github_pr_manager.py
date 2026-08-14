"""Unit tests for PRManager."""

from codegraph.git.models import PullRequestPlan
from codegraph.github.client import FakeGitHubClient
from codegraph.github.pr_manager import PRManager


def test_pr_manager_creates_and_formats_pr() -> None:
    client = FakeGitHubClient()
    manager = PRManager(client)

    plan = PullRequestPlan(
        title="fix(userservice): normalize user identity",
        summary="Automated fix for user identity mismatch",
        problem="Authorization failure",
        root_cause="Identity key mismatch",
        changes=("Modified services.py",),
        tests="Pytest passed 110/110",
        risks="LOW risk",
        evidence=("E1", "E2"),
        branch="codegraph/fix/userservice",
        base_branch="main",
    )

    created, err = manager.create_or_update_pr("Omarkam3l/code-base", plan)
    assert err is None
    assert created.pr_number == 102
    assert "Evidence Provenance" in created.body
    assert "[E1]" in created.body

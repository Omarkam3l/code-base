"""Unit tests for FakeGitHubClient."""

from codegraph.github.client import FakeGitHubClient


def test_fake_github_client_pr_operations() -> None:
    client = FakeGitHubClient()
    pr = client.get_pull_request("Omarkam3l/code-base", 101)

    assert pr.pr_number == 101
    assert "userservice" in pr.title.lower()
    assert pr.head_branch == "codegraph/fix/userservice-auth"

    new_pr = client.create_pull_request(
        repo="Omarkam3l/code-base",
        title="fix(models): update user schema",
        body="Body",
        head_branch="codegraph/fix/user-schema",
    )
    assert new_pr.pr_number == 102
    assert new_pr.title == "fix(models): update user schema"


def test_fake_github_client_ci_and_review() -> None:
    client_fail = FakeGitHubClient(ci_failing=True, has_review=True)
    runs = client_fail.get_ci_check_runs("Omarkam3l/code-base", "sha_123")
    reviews = client_fail.get_review_comments("Omarkam3l/code-base", 101)

    assert len(runs) == 1
    assert runs[0].conclusion == "failure"
    assert len(reviews) == 1
    assert "services.py" in reviews[0].path

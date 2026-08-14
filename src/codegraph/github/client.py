"""Typed GitHub REST API client interface and deterministic mock client."""

from typing import Any
from codegraph.github.models import CIRunStatus, PRMetadata, ReviewComment


class GitHubClient:
    """Safe, typed interface for interacting with GitHub REST API endpoints."""

    def __init__(self, token: str | None = None, api_base_url: str = "https://api.github.com") -> None:
        self.token = token
        self.api_base_url = api_base_url.rstrip("/")

    def get_pull_request(self, repo: str, pr_number: int) -> PRMetadata:
        """Fetch Pull Request metadata."""
        raise NotImplementedError

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> PRMetadata:
        """Create a new Pull Request."""
        raise NotImplementedError

    def update_pull_request(self, repo: str, pr_number: int, title: str | None = None, body: str | None = None) -> PRMetadata:
        """Update existing Pull Request description or title."""
        raise NotImplementedError

    def get_ci_check_runs(self, repo: str, ref_sha: str) -> list[CIRunStatus]:
        """Fetch GitHub Actions CI check runs for a commit SHA."""
        raise NotImplementedError

    def get_review_comments(self, repo: str, pr_number: int) -> list[ReviewComment]:
        """Fetch inline PR review comments."""
        raise NotImplementedError

    def post_review_reply(self, repo: str, pr_number: int, comment_id: str, body: str) -> bool:
        """Post a reply to an inline PR review comment thread."""
        raise NotImplementedError


class FakeGitHubClient(GitHubClient):
    """Deterministic mock GitHub client for unit and benchmark testing."""

    def __init__(self, ci_failing: bool = False, has_review: bool = False) -> None:
        super().__init__(token="mock_token")
        self.ci_failing = ci_failing
        self.has_review = has_review
        self.prs: dict[int, PRMetadata] = {
            101: PRMetadata(
                pr_number=101,
                title="fix(userservice): normalize authenticated user identity",
                body="Root cause: Identity mismatch\n\nEvidence: [E1], [E2]",
                author="codegraph-bot",
                state="open",
                head_sha="a1b2c3d4e5f678901234567890abcdef12345678",
                head_branch="codegraph/fix/userservice-auth",
                base_branch="main",
                html_url="https://github.com/Omarkam3l/code-base/pull/101",
            )
        }

    def get_pull_request(self, repo: str, pr_number: int) -> PRMetadata:
        return self.prs.get(
            pr_number,
            PRMetadata(
                pr_number=pr_number,
                title=f"PR #{pr_number}",
                body="Mock PR Body",
                author="user",
                state="open",
                head_sha="head_sha_123",
                head_branch="feature",
                base_branch="main",
            ),
        )

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> PRMetadata:
        new_pr = PRMetadata(
            pr_number=102,
            title=title,
            body=body,
            author="codegraph-bot",
            state="open",
            head_sha="head_sha_456",
            head_branch=head_branch,
            base_branch=base_branch,
            html_url=f"https://github.com/{repo}/pull/102",
        )
        self.prs[102] = new_pr
        return new_pr

    def update_pull_request(self, repo: str, pr_number: int, title: str | None = None, body: str | None = None) -> PRMetadata:
        pr = self.get_pull_request(repo, pr_number)
        updated = PRMetadata(
            pr_number=pr.pr_number,
            title=title or pr.title,
            body=body or pr.body,
            author=pr.author,
            state=pr.state,
            head_sha=pr.head_sha,
            head_branch=pr.head_branch,
            base_branch=pr.base_branch,
            html_url=pr.html_url,
        )
        self.prs[pr_number] = updated
        return updated

    def get_ci_check_runs(self, repo: str, ref_sha: str) -> list[CIRunStatus]:
        if self.ci_failing:
            return [
                CIRunStatus(
                    run_id="ci_run_999",
                    workflow_name="pytest-ci",
                    status="completed",
                    conclusion="failure",
                    failed_jobs=("test_user_service_auth",),
                    failure_details=("AssertionError: expected 'authenticated' got 'unauthorized'",),
                    head_sha=ref_sha,
                )
            ]
        return [
            CIRunStatus(
                run_id="ci_run_100",
                workflow_name="pytest-ci",
                status="completed",
                conclusion="success",
                head_sha=ref_sha,
            )
        ]

    def get_review_comments(self, repo: str, pr_number: int) -> list[ReviewComment]:
        if self.has_review:
            return [
                ReviewComment(
                    comment_id="comment_777",
                    path="services.py",
                    line=42,
                    author="code-reviewer",
                    body="Please fix the user identity normalization for empty string user_ids.",
                    created_at="2026-08-14T12:00:00Z",
                )
            ]
        return []

    def post_review_reply(self, repo: str, pr_number: int, comment_id: str, body: str) -> bool:
        return True

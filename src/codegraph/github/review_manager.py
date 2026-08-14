"""Review Manager module for fetching, parsing, and replying to PR review comments."""

from codegraph.github.client import GitHubClient
from codegraph.github.models import ReviewComment


class ReviewManager:
    """Manages PR inline review comment ingestion and response posting."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def fetch_review_comments(self, repo: str, pr_number: int) -> list[ReviewComment]:
        """Fetch all inline review comments for a target PR."""
        try:
            return self.client.get_review_comments(repo, pr_number)
        except Exception:
            return []

    def post_reply(self, repo: str, pr_number: int, comment_id: str, reply_text: str) -> bool:
        """Post a reply to an inline PR review comment."""
        try:
            return self.client.post_review_reply(repo, pr_number, comment_id, reply_text)
        except Exception:
            return False

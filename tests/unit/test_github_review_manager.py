"""Unit tests for ReviewManager."""

from codegraph.github.client import FakeGitHubClient
from codegraph.github.review_manager import ReviewManager


def test_review_manager_fetches_and_replies() -> None:
    client = FakeGitHubClient(has_review=True)
    manager = ReviewManager(client)

    comments = manager.fetch_review_comments("Omarkam3l/code-base", 101)
    assert len(comments) == 1
    assert "services.py" in comments[0].path

    replied = manager.post_reply("Omarkam3l/code-base", 101, comments[0].comment_id, "Addressed in fix commit")
    assert replied is True

"""Unit tests for EventNormalizer and GitHubSafetyController."""

from codegraph.github.event_normalizer import EventNormalizer
from codegraph.github.models import GitHubEvent
from codegraph.github.safety import GitHubSafetyController


def test_event_normalizer_pr_opened() -> None:
    event = GitHubEvent(
        event_id="evt_001",
        event_type="pr_opened",
        repository="Omarkam3l/code-base",
        pr_number=101,
        branch="feature/auth",
        sender="user1",
        payload={"pull_request": {"title": "Fix Auth Endpoint", "body": "Normalize user identity"}},
    )

    norm = EventNormalizer.normalize_event(event)
    assert norm.event_id == "evt_001"
    assert "Fix Auth Endpoint" in norm.query_or_instruction


def test_safety_controller_prohibits_auto_merge() -> None:
    controller = GitHubSafetyController()
    valid, err = controller.validate_action("merge_pull_request")
    assert valid is False
    assert "prohibited" in err.lower()

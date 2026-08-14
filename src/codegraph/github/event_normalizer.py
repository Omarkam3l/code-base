"""Event Normalizer module converting raw GitHub webhooks into unified NormalizedEvents."""

from typing import Any
from codegraph.github.models import GitHubEvent, NormalizedEvent


class EventNormalizer:
    """Normalizes heterogeneous GitHub webhook events into unified NormalizedEvent objects."""

    @staticmethod
    def normalize_event(event: GitHubEvent) -> NormalizedEvent:
        """Convert a raw GitHubEvent into a standardized NormalizedEvent."""
        payload = event.payload or {}
        event_type = event.event_type.lower()

        query_or_instruction = ""
        metadata: dict[str, Any] = {
            "repository": event.repository,
            "pr_number": event.pr_number,
            "branch": event.branch,
            "sender": event.sender,
        }

        if event_type in ("pr_opened", "pull_request"):
            title = payload.get("pull_request", {}).get("title", "")
            body = payload.get("pull_request", {}).get("body", "")
            query_or_instruction = f"{title}\n{body}".strip() or f"Investigate PR #{event.pr_number}"

        elif event_type in ("review_comment", "pull_request_review_comment"):
            comment_body = payload.get("comment", {}).get("body", "")
            path = payload.get("comment", {}).get("path", "")
            line = payload.get("comment", {}).get("line", 0)
            query_or_instruction = f"Address review comment on {path}:{line}: {comment_body}"
            metadata["path"] = path
            metadata["line"] = line

        elif event_type in ("ci_completed", "check_run"):
            workflow_name = payload.get("check_run", {}).get("name", "CI Workflow")
            query_or_instruction = f"Repair CI failure in workflow '{workflow_name}' for PR #{event.pr_number}"
            metadata["check_run_id"] = payload.get("check_run", {}).get("id")

        else:
            query_or_instruction = f"Process GitHub event {event_type} for PR #{event.pr_number}"

        return NormalizedEvent(
            event_id=event.event_id,
            event_type=event_type,
            repository=event.repository,
            pr_number=event.pr_number,
            branch=event.branch,
            query_or_instruction=query_or_instruction,
            context_metadata=metadata,
            raw_payload=payload,
        )

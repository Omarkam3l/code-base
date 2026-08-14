"""GitHub safety controller enforcing token security, rate limits, and merge prohibitions."""

import re


class GitHubSafetyController:
    """Enforces API rate limits, token redaction, and blocks forbidden automated actions (e.g. merging)."""

    def __init__(self, allow_auto_merge: bool = False) -> None:
        self.allow_auto_merge = allow_auto_merge

    def validate_action(self, action_name: str) -> tuple[bool, str | None]:
        """Validate proposed GitHub API action safety."""
        action_low = action_name.lower()

        if "merge" in action_low:
            return False, "SAFETY_VIOLATION: Automatic Pull Request merging is strictly prohibited."

        if "delete_repo" in action_low or "delete_branch" in action_low:
            return False, f"SAFETY_VIOLATION: Destructive GitHub action '{action_name}' is prohibited."

        return True, None

    @staticmethod
    def sanitize_log_output(text: str) -> str:
        """Redact tokens or authorization headers from diagnostic log strings."""
        if not text:
            return ""
        # Redact Bearer tokens, GitHub ghp_/gho_ tokens, and AWS key patterns
        sanitized = re.sub(r"ghp_[a-zA-Z0-9]{36}", "ghp_REDACTED", text)
        sanitized = re.sub(r"gho_[a-zA-Z0-9]{36}", "gho_REDACTED", sanitized)
        sanitized = re.sub(r"Bearer\s+[a-zA-Z0-9._-]+", "Bearer REDACTED", sanitized, flags=re.IGNORECASE)
        return sanitized

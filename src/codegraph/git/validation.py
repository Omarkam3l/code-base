"""Secret detection and concurrent change validation for Phase 10."""

import re
from typing import Sequence
from codegraph.git.models import GitDiff, GitRepository, GitStatus


class SecretDetector:
    """Local deterministic pattern scanner detecting secrets, API keys, and credentials in source diffs."""

    SECRET_PATTERNS: tuple[re.Pattern, ...] = (
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub Personal Access Token
        re.compile(r"gho_[a-zA-Z0-9]{36}"),  # GitHub OAuth Token
        re.compile(r"-----BEGIN\s+(?:RSA|OPENSSH|EC|PGP|PRIVATE)\s+KEY"),  # Private Key Header
        re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),  # Slack Token
        re.compile(r"EYJ[0-9A-ZA-Z_-]+\.[0-9A-ZA-Z_-]+\.[0-9A-ZA-Z_-]+", re.IGNORECASE),  # JWT Token
        re.compile(r"(?:api_key|access_token|secret_key|password)\s*[:=]\s*['\"](?![A-Za-z0-9_]*TEST[A-Za-z0-9_]*)[A-Za-z0-9_/-]{16,}['\"]", re.IGNORECASE),
    )

    @staticmethod
    def scan_diff_for_secrets(diff: GitDiff | str) -> tuple[bool, str | None]:
        """Scan diff unified string or GitDiff object for credential leakage.

        Returns (is_clean, failure_reason).
        """
        diff_text = diff.unified_diff if isinstance(diff, GitDiff) else diff

        if not diff_text:
            return True, None

        for line in diff_text.splitlines():
            # Only scan added lines in diffs
            if line.startswith("+") and not line.startswith("+++"):
                added_content = line[1:]
                for pattern in SecretDetector.SECRET_PATTERNS:
                    match = pattern.search(added_content)
                    if match:
                        matched_snippet = match.group(0)[:12] + "..."
                        return False, f"Secret/Credential leakage detected in diff: '{matched_snippet}'"

        return True, None


class ConcurrentChangeDetector:
    """Detects if working tree or HEAD commit changed during workflow execution."""

    @staticmethod
    def detect_concurrent_change(
        baseline_repo: GitRepository,
        current_repo: GitRepository,
        current_status: GitStatus,
    ) -> tuple[bool, str | None]:
        """Verify baseline HEAD commit and branch match current status."""
        if baseline_repo.head_commit and current_repo.head_commit:
            if baseline_repo.head_commit != current_repo.head_commit:
                return False, f"CONCURRENT_REPOSITORY_CHANGE: HEAD commit changed from '{baseline_repo.head_commit[:8]}' to '{current_repo.head_commit[:8]}'."

        if baseline_repo.current_branch != current_repo.current_branch:
            return False, f"CONCURRENT_REPOSITORY_CHANGE: Active branch changed from '{baseline_repo.current_branch}' to '{current_repo.current_branch}'."

        return True, None

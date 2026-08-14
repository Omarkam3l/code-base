"""Secret Redactor for masking tokens, credentials, and API keys in logs and traces."""

import re
from typing import Any


class SecretRedactor:
    """Scans and redacts secret tokens, credentials, and sensitive patterns from logs, exceptions, and traces."""

    PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA[REDACTED_AWS_KEY]"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "ghp_[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"gho_[a-zA-Z0-9]{36}"), "gho_[REDACTED_OAUTH_TOKEN]"),
        (re.compile(r"nvapi-[a-zA-Z0-9_-]{40,64}"), "nvapi-[REDACTED_NIM_KEY]"),
        (re.compile(r"-----BEGIN\s+(?:RSA|OPENSSH|EC|PGP|PRIVATE)\s+KEY[\s\S]+?-----END\s+(?:RSA|OPENSSH|EC|PGP|PRIVATE)\s+KEY-----"), "[REDACTED_PRIVATE_KEY]"),
        (re.compile(r"Bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
        (re.compile(r"(?:password|secret|api_key|access_token)\s*[:=]\s*['\"](?![A-Za-z0-9_]*TEST[A-Za-z0-9_]*)[A-Za-z0-9_/-]{16,}['\"]", re.IGNORECASE), "secret='[REDACTED]'"),
    )

    @staticmethod
    def redact_text(text: str | None) -> str:
        """Redact known secret patterns from string output."""
        if not text:
            return ""

        result = text
        for pattern, replacement in SecretRedactor.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @staticmethod
    def redact_object(obj: Any) -> Any:
        """Recursively redact strings in dictionaries or lists."""
        if isinstance(obj, str):
            return SecretRedactor.redact_text(obj)
        elif isinstance(obj, dict):
            return {k: SecretRedactor.redact_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [SecretRedactor.redact_object(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(SecretRedactor.redact_object(item) for item in obj)
        return obj

"""Sample models module for repository ingestion testing."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User domain entity."""

    id: int
    name: str
    age: int = 18
    email: Optional[str] = None

    def display_name(self) -> str:
        """Return formatted user display name."""
        return f"{self.name} (<{self.email}>)"

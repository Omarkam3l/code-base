"""Sample main module for repository ingestion testing."""

import sys
from typing import Dict, Any

from .services import UserService
from .models import User


def calculate_total(items, discount: float = 0.0, *options, **config) -> float:
    """Top-level function calculating total price with untyped and typed parameters."""
    total = sum(items)
    return total * (1.0 - discount)


def main() -> None:
    """Entry point function."""
    service = UserService()
    user = service.add_user("Alice", age=30)
    print(f"Created user: {user.display_name()}")


if __name__ == "__main__":
    main()

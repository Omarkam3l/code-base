"""Sample services module for repository ingestion testing."""

import os
from typing import List

from .models import User


class UserService:
    """Service class for user operations."""

    def __init__(self, storage_path: str = "/tmp/users") -> None:
        self.storage_path = storage_path
        self._users: List[User] = []

    def add_user(self, name: str, age: int = 21, *tags, **metadata) -> User:
        """Create and store a new user."""
        user_id = len(self._users) + 1
        user = User(id=user_id, name=name, age=age)
        self._users.append(user)
        return user

    async def fetch_user_by_id(self, user_id: int) -> User | None:
        """Fetch user asynchronously by ID."""
        for user in self._users:
            if user.id == user_id:
                return user
        return None

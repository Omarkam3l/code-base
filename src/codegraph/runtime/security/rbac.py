"""Role-Based Access Control (RBAC) controller for Phase 14 Security."""

from enum import Enum
from dataclasses import dataclass, field


class Role(str, Enum):
    """User access role levels."""

    VIEWER = "VIEWER"
    DEVELOPER = "DEVELOPER"
    MAINTAINER = "MAINTAINER"
    ADMIN = "ADMIN"


@dataclass
class UserPermission:
    """User role and organization assignment."""

    user_id: str
    organization_id: str
    role: Role = Role.DEVELOPER


class RBACController:
    """Enforces Role-Based Access Control permissions across platform operations."""

    ROLE_HIERARCHY: dict[Role, set[str]] = {
        Role.VIEWER: {"query", "investigate", "trace"},
        Role.DEVELOPER: {"query", "investigate", "trace", "change_plan", "patch_generation", "repair"},
        Role.MAINTAINER: {"query", "investigate", "trace", "change_plan", "patch_generation", "repair", "commit", "pr_creation"},
        Role.ADMIN: {"query", "investigate", "trace", "change_plan", "patch_generation", "repair", "commit", "pr_creation", "register_repository", "remove_repository", "org_admin"},
    }

    def check_permission(self, role: Role, operation: str) -> bool:
        """Check if role is permitted to perform operation."""
        allowed = self.ROLE_HIERARCHY.get(role, set())
        return operation in allowed

    def authorize(self, role: Role, operation: str) -> None:
        """Authorize operation or raise PermissionError."""
        if not self.check_permission(role, operation):
            raise PermissionError(f"Authorization failure: Role '{role.value}' is not permitted to perform '{operation}'.")

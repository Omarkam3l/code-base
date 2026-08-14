"""Unit tests for RBACController and ResourceController."""

import pytest
from codegraph.runtime.security.budgets import ResourceBudget, ResourceController
from codegraph.runtime.security.rbac import RBACController, Role


def test_rbac_permissions() -> None:
    rbac = RBACController()
    assert rbac.check_permission(Role.VIEWER, "query") is True
    assert rbac.check_permission(Role.VIEWER, "commit") is False

    with pytest.raises(PermissionError, match="Authorization failure"):
        rbac.authorize(Role.VIEWER, "commit")


def test_resource_budget_limits() -> None:
    budget = ResourceBudget(max_concurrent_jobs=2)
    controller = ResourceController(budget=budget)

    controller.acquire_job_slot()
    controller.acquire_job_slot()

    with pytest.raises(RuntimeError, match="Resource budget exhausted"):
        controller.acquire_job_slot()

    controller.release_job_slot()
    assert controller.active_jobs == 1

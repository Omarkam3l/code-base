"""Unit tests for BranchManager and branch safety rules."""

from codegraph.git.branch import BranchManager


def test_branch_creation_and_safety() -> None:
    plan = BranchManager.create_branch_plan("fix", "auth-service")
    assert plan.branch_name == "codegraph/fix/auth-service"

    valid, err = BranchManager.validate_branch_name(plan.branch_name)
    assert valid is True
    assert err is None


def test_branch_collision_resolution() -> None:
    existing = {"codegraph/fix/auth-service"}
    plan = BranchManager.create_branch_plan("fix", "auth-service", existing_branches=existing)

    assert plan.branch_name != "codegraph/fix/auth-service"
    assert plan.branch_name.startswith("codegraph/fix/auth-service-v")


def test_branch_validation_rejects_unsafe_characters() -> None:
    valid, err = BranchManager.validate_branch_name("codegraph/fix/..escape")
    assert valid is False
    assert "forbidden" in err.lower()

    valid2, err2 = BranchManager.validate_branch_name("-invalid-leading-dash")
    assert valid2 is False

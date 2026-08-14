"""Unit tests for PRGenerator and FakePullRequestProvider."""

from codegraph.change.models import ChangePlan, ChangeRiskLevel
from codegraph.git.models import BranchPlan
from codegraph.git.pr import FakePullRequestProvider, PRGenerator


def test_pr_generator_preserves_evidence() -> None:
    change_plan = ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
        evidence_references=("E1", "E2"),
    )
    branch_plan = BranchPlan(branch_name="codegraph/fix/userservice", base_branch="main", purpose="Fix")

    pr_plan = PRGenerator.generate_pr_plan(change_plan, branch_plan)
    assert pr_plan.title.startswith("fix(userservice):")
    assert pr_plan.evidence == ("E1", "E2")
    assert pr_plan.branch == "codegraph/fix/userservice"

    provider = FakePullRequestProvider()
    res, err = provider.create_pull_request(pr_plan)
    assert err is None
    assert res["status"] == "PROPOSED"

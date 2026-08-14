"""Unit tests for CommitPlanner, CommitValidator, and SecretDetector."""

from codegraph.change.models import ChangeOperation, ChangeOperationType, ChangePlan, ChangeRiskLevel
from codegraph.git.commit import CommitPlanner, CommitValidator
from codegraph.git.models import GitDiff
from codegraph.git.validation import SecretDetector


def test_commit_planner_and_validator() -> None:
    op = ChangeOperation(
        file="services.py",
        operation_type=ChangeOperationType.MODIFY_FUNCTION,
        target="UserService",
        description="Fix authentication response model",
        rationale="Resolves auth error",
    )
    change_plan = ChangePlan(
        objective="Fix UserService auth",
        root_cause="Identity mismatch",
        affected_entities=("UserService",),
        affected_files=("services.py",),
        modifications=(op,),
        risks=ChangeRiskLevel.LOW,
        validation_strategy="AST",
        evidence_references=("E1", "E2"),
    )
    diff = GitDiff(files=("services.py",), additions=5, deletions=2, unified_diff="+ def UserService(): pass\n")

    commit_plan = CommitPlanner.plan_commit(change_plan, git_diff=diff)
    assert commit_plan.message.startswith("fix(userservice):")
    assert "services.py" in commit_plan.files

    valid, err = CommitValidator.validate_commit_plan(commit_plan, diff)
    assert valid is True
    assert err is None


def test_secret_detector_blocks_aws_and_github_tokens() -> None:
    diff_with_aws = GitDiff(
        files=("services.py",),
        additions=1,
        deletions=0,
        unified_diff="+ AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n",
    )
    clean, err = SecretDetector.scan_diff_for_secrets(diff_with_aws)
    assert clean is False
    assert "secret" in err.lower()

    diff_with_ghp = GitDiff(
        files=("services.py",),
        additions=1,
        deletions=0,
        unified_diff="+ GITHUB_TOKEN = 'ghp_1234567890abcdef1234567890abcdef1234'\n",
    )
    clean2, err2 = SecretDetector.scan_diff_for_secrets(diff_with_ghp)
    assert clean2 is False

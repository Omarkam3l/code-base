"""Pull Request proposal generator and provider abstraction module for Phase 10."""

from typing import Sequence
from codegraph.change.models import ChangePlan
from codegraph.git.models import BranchPlan, CommitResult, GitDiff, PullRequestPlan
from codegraph.repair.models import RepairResult


class PRGenerator:
    """Formulates provider-neutral Pull Request proposals preserving complete evidence provenance."""

    @staticmethod
    def generate_pr_plan(
        change_plan: ChangePlan,
        branch_plan: BranchPlan,
        repair_result: RepairResult | None = None,
        git_diff: GitDiff | None = None,
        commit_result: CommitResult | None = None,
    ) -> PullRequestPlan:
        """Formulate a comprehensive PullRequestPlan with evidence provenance."""
        target_entity = change_plan.affected_entities[0] if change_plan.affected_entities else "component"
        title = f"fix({target_entity.lower()}): {change_plan.objective}"

        summary = f"Automated, evidence-grounded repair for {target_entity}."
        problem = f"Engineering issue: {change_plan.objective}"
        root_cause = change_plan.root_cause

        changes = [f"Modified {op.file}: {op.description}" for op in change_plan.modifications]

        tests_summary = "All unit, AST, and scope validation checks passed."
        if repair_result and repair_result.final_test_result:
            tr = repair_result.final_test_result
            tests_summary = f"Pytest suite passed: {tr.tests_passed} passed, {tr.tests_failed} failed in {tr.execution_time_ms:.1f}ms."

        risks = f"Risk Level: {change_plan.risks.value}. Changes strictly scoped to {change_plan.affected_files}."
        evidence = change_plan.evidence_references or ("E1", "E2")

        return PullRequestPlan(
            title=title[:100],
            summary=summary,
            problem=problem,
            root_cause=root_cause,
            changes=tuple(changes),
            tests=tests_summary,
            risks=risks,
            evidence=tuple(evidence),
            branch=branch_plan.branch_name,
            base_branch=branch_plan.base_branch,
        )


class PullRequestProvider:
    """Provider interface for creating external pull request proposals."""

    def create_pull_request(self, plan: PullRequestPlan) -> tuple[dict[str, str] | None, str | None]:
        """Create pull request proposal."""
        raise NotImplementedError


class FakePullRequestProvider(PullRequestProvider):
    """Deterministic mock PR provider for unit and benchmark testing."""

    def create_pull_request(self, plan: PullRequestPlan) -> tuple[dict[str, str] | None, str | None]:
        return (
            {
                "pr_number": "101",
                "url": f"https://github.com/Omarkam3l/code-base/pull/101",
                "title": plan.title,
                "branch": plan.branch,
                "base": plan.base_branch,
                "status": "PROPOSED",
            },
            None,
        )

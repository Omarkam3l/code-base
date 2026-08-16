"""End-to-end Change Planning & Patch Generation Pipeline for Phase 8."""

import time
from pathlib import Path
from codegraph.change.models import (
    ChangeRequest,
    ChangeResult,
    ValidationResult,
    TestExecutionResult,
)
from codegraph.change.planner import DeterministicChangePlanner, LLMChangePlanner, ChangePlanValidator
from codegraph.change.patch import PatchGenerator, DeterministicPatchGenerator
from codegraph.change.validator import PatchValidator, ASTValidator
from codegraph.change.workspace import WorkspaceManager
from codegraph.change.tests import TestRunner
from codegraph.change.impact import ChangeImpactVerifier, ChangeRiskAnalyzer
from codegraph.agent.pipeline import AgenticPipeline
from codegraph.graph.repository import GraphRepository


class ChangePipeline:
    """Orchestrates end-to-end Investigation -> Plan -> Patch -> Workspace -> Validate -> Test."""

    def __init__(
        self,
        agent_pipeline: AgenticPipeline | None = None,
        graph_repo: GraphRepository | None = None,
        use_deterministic: bool = True,
    ) -> None:
        self.agent_pipeline = agent_pipeline
        self.graph_repo = graph_repo
        self.use_deterministic = use_deterministic

        if use_deterministic:
            self.planner = DeterministicChangePlanner(graph_repo=graph_repo)
            self.patch_generator = DeterministicPatchGenerator()
        else:
            self.planner = LLMChangePlanner(graph_repo=graph_repo)
            self.patch_generator = PatchGenerator()

        self.impact_verifier = ChangeImpactVerifier(graph_repo=graph_repo)
        self.test_runner = TestRunner()

    def process_change_request(
        self,
        request: ChangeRequest,
        source_repo_path: str | Path,
        source_code_map: dict[str, str],
        run_tests: bool = True,
    ) -> ChangeResult:
        """Execute full Phase 8 change planning, patch generation, and validation pipeline."""
        start_time = time.perf_counter()

        # Step 1: Run Phase 7 Investigation if not provided
        investigation_ctx = request.investigation_context
        if not investigation_ctx and self.agent_pipeline:
            investigation_ctx = self.agent_pipeline.investigate(
                question=request.description,
                repository_id=request.repository_id,
                source_code_map=source_code_map,
            )

        req_with_ctx = ChangeRequest(
            description=request.description,
            repository_id=request.repository_id,
            investigation_context=investigation_ctx,
        )

        # Step 2: Change Planner (receives source map for grounded patch construction)
        plan = self.planner.create_plan(req_with_ctx, source_code_map=source_code_map)
        if not plan.is_valid:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ChangeResult(
                plan=plan,
                patch=None,
                validation=ValidationResult(
                    syntax_valid=False,
                    structural_valid=False,
                    tests_passed=False,
                    failures=(f"Plan rejected: {plan.rejection_reason}",),
                ),
                test_results=None,
                status="REJECTED",
                explanation=f"Change plan validation failed: {plan.rejection_reason}",
                execution_time_ms=elapsed,
            )

        # Step 3: Impact & Risk Verification
        is_complete, missing, warnings = self.impact_verifier.verify_plan_impact(plan)
        if not is_complete:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ChangeResult(
                plan=plan,
                patch=None,
                validation=ValidationResult(
                    syntax_valid=False,
                    structural_valid=False,
                    tests_passed=False,
                    failures=missing,
                    warnings=warnings,
                ),
                test_results=None,
                status="REJECTED",
                explanation=f"Plan incomplete: misses high-confidence graph dependencies: {missing}",
                execution_time_ms=elapsed,
            )

        # Step 4: Patch Generation
        patch, patch_err = self.patch_generator.generate_patch(plan, source_code_map)
        if patch_err or not patch:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ChangeResult(
                plan=plan,
                patch=None,
                validation=ValidationResult(
                    syntax_valid=False,
                    structural_valid=False,
                    tests_passed=False,
                    failures=(f"Patch generation error: {patch_err}",),
                ),
                test_results=None,
                status="REJECTED",
                explanation=f"Patch generation failed: {patch_err}",
                execution_time_ms=elapsed,
            )

        # Step 5: Scope Validation
        valid_scope, scope_err = PatchValidator.validate_patch_scope(patch, plan)
        if not valid_scope:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ChangeResult(
                plan=plan,
                patch=patch,
                validation=ValidationResult(
                    syntax_valid=False,
                    structural_valid=False,
                    tests_passed=False,
                    failures=(scope_err,),
                ),
                test_results=None,
                status="REJECTED",
                explanation=f"Patch scope validation failed: {scope_err}",
                execution_time_ms=elapsed,
            )

        # Step 6: Workspace Isolation & Test Execution
        workspace_mgr = WorkspaceManager(source_repo_path=source_repo_path)
        with workspace_mgr.create_isolated_workspace() as ws_path:
            # Baseline test run
            baseline_result = None
            if run_tests:
                baseline_result = self.test_runner.run_tests(ws_path)

            # Apply patch inside workspace
            applied, apply_err = workspace_mgr.apply_patch_to_workspace(ws_path, patch)
            if not applied:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return ChangeResult(
                    plan=plan,
                    patch=patch,
                    validation=ValidationResult(
                        syntax_valid=False,
                        structural_valid=False,
                        tests_passed=False,
                        failures=(f"Workspace patch application error: {apply_err}",),
                    ),
                    test_results=None,
                    status="REJECTED",
                    explanation=f"Workspace application failed: {apply_err}",
                    execution_time_ms=elapsed,
                )

            # AST & Syntax Validation post-apply
            syntax_valid = True
            ast_failures = []
            for fc in patch.file_changes:
                valid_ast, ast_err = ASTValidator.validate_source_code(fc.file_path, fc.new_content)
                if not valid_ast:
                    syntax_valid = False
                    ast_failures.append(ast_err)

            if not syntax_valid:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return ChangeResult(
                    plan=plan,
                    patch=patch,
                    validation=ValidationResult(
                        syntax_valid=False,
                        structural_valid=False,
                        tests_passed=False,
                        failures=tuple(ast_failures),
                    ),
                    test_results=None,
                    status="REJECTED",
                    explanation=f"AST validation failed after patch: {ast_failures}",
                    execution_time_ms=elapsed,
                )

            # Post-patch test execution inside workspace
            test_res = None
            if run_tests:
                test_res = self.test_runner.run_tests(ws_path)
                if baseline_result and baseline_result.tests_failed > 0:
                    diff_failures = tuple(
                        f for f in test_res.test_failures
                        if f not in set(baseline_result.test_failures)
                    )
                    test_res = TestExecutionResult(
                        tests_run=test_res.tests_run,
                        tests_passed=test_res.tests_passed,
                        tests_failed=test_res.tests_failed,
                        test_failures=test_res.test_failures,
                        execution_time_ms=test_res.execution_time_ms,
                        baseline_failed=True,
                        new_failures=diff_failures,
                    )

        elapsed = (time.perf_counter() - start_time) * 1000.0
        tests_passed = (test_res.tests_failed == 0) if test_res else True
        status = "VALIDATED" if tests_passed else "TEST_FAILED"

        return ChangeResult(
            plan=plan,
            patch=patch,
            validation=ValidationResult(
                syntax_valid=True,
                structural_valid=True,
                tests_passed=tests_passed,
                failures=() if tests_passed else test_res.test_failures,
            ),
            test_results=test_res,
            status=status,
            explanation="Change plan and patch successfully validated in isolated workspace." if tests_passed else "Patch applied cleanly but tests failed inside isolated workspace.",
            execution_time_ms=elapsed,
        )

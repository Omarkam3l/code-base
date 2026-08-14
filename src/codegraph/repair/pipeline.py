"""End-to-end RepairPipeline orchestrating controlled iterative patch repair for Phase 9."""

import time
from pathlib import Path
from typing import Sequence
from codegraph.change.models import ChangePlan, Patch, TestExecutionResult, ValidationResult
from codegraph.change.pipeline import ChangePipeline
from codegraph.change.workspace import WorkspaceManager
from codegraph.graph.repository import GraphRepository
from codegraph.rag.llm import BaseLLMProvider
from codegraph.repair.diagnosis import FailureDiagnoser, FakeFailureDiagnoser, LLMFailureDiagnoser
from codegraph.repair.failure import FailureParser
from codegraph.repair.iteration import IterationController
from codegraph.repair.metrics import calculate_repair_metrics
from codegraph.repair.models import (
    FailureDiagnosis,
    FailureRecord,
    RepairIteration,
    RepairPlan,
    RepairRequest,
    RepairResult,
    RepairTrace,
)
from codegraph.repair.patch import RepairPatchGenerator
from codegraph.repair.planner import DeterministicRepairPlanner, LLMRepairPlanner
from codegraph.repair.safety import RepairSafetyValidator
from codegraph.repair.stopping import FingerprintManager, StoppingEvaluator


class RepairPipeline:
    """Orchestrates Phase 9 Controlled Iterative Patch Repair."""

    def __init__(
        self,
        change_pipeline: ChangePipeline | None = None,
        graph_repo: GraphRepository | None = None,
        llm_provider: BaseLLMProvider | None = None,
        use_deterministic: bool = True,
    ) -> None:
        self.change_pipeline = change_pipeline
        self.graph_repo = graph_repo
        self.llm_provider = llm_provider
        self.use_deterministic = use_deterministic

        if use_deterministic or not llm_provider:
            self.diagnoser = FakeFailureDiagnoser(graph_repo=graph_repo)
            self.planner = DeterministicRepairPlanner(graph_repo=graph_repo)
        else:
            self.diagnoser = LLMFailureDiagnoser(llm_provider=llm_provider, graph_repo=graph_repo)
            self.planner = LLMRepairPlanner(llm_provider=llm_provider, graph_repo=graph_repo)

        self.iteration_controller = IterationController(
            graph_repo=graph_repo,
            use_deterministic=use_deterministic,
            diagnoser=self.diagnoser,
            planner=self.planner,
        )
        self.stopping_evaluator = StoppingEvaluator()
        self.patch_generator = RepairPatchGenerator(use_deterministic=use_deterministic)

    def repair(
        self,
        request: RepairRequest,
        source_repo_path: str | Path,
        source_code_map: dict[str, str],
        run_tests: bool = True,
    ) -> RepairResult:
        """Execute full iterative repair loop until success, failure, or abstention."""
        start_time = time.perf_counter()
        iterations: list[RepairIteration] = []
        failure_history: list[FailureRecord] = []
        seen_fingerprints: list[str] = []

        total_tool_calls = 0
        total_test_runtime = 0.0
        total_changed_lines = 0
        evidence_iteration_count = 0

        workspace_mgr = WorkspaceManager(source_repo_path=source_repo_path)
        with workspace_mgr.create_isolated_workspace() as ws_path:
            # 1. Apply initial patch to workspace if present
            initial_test_res = request.initial_test_result
            if request.initial_patch:
                workspace_mgr.apply_patch_to_workspace(ws_path, request.initial_patch)
                total_changed_lines += request.initial_patch.lines_added + request.initial_patch.lines_removed

            # Parse initial failures
            if initial_test_res and initial_test_res.test_failures:
                current_failures = FailureParser.parse_test_result(initial_test_res)
            else:
                # If no test failures provided, run baseline test in workspace
                if run_tests:
                    initial_test_res = self.iteration_controller.test_runner.run_tests(ws_path)
                    current_failures = FailureParser.parse_test_result(initial_test_res)
                else:
                    current_failures = (
                        FailureRecord(
                            test_name="test_default",
                            test_file="tests/test_services.py",
                            error_type="AssertionError",
                            error_message="Assertion failed in user authorization test",
                            traceback="AssertionError: Expected status authenticated",
                        ),
                    )

            failure_history.extend(current_failures)

            # If initial tests pass, return success immediately
            if initial_test_res and initial_test_res.tests_failed == 0 and not initial_test_res.baseline_failed:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return RepairResult(
                    status="SUCCESS",
                    iterations=(),
                    final_patch=request.initial_patch,
                    final_test_result=initial_test_res,
                    failure_history=tuple(failure_history),
                    stopping_reason="Initial patch passed all tests without failures.",
                    execution_time_ms=elapsed,
                )

            # 2. Bounded Iterative Repair Loop
            iteration_count = 0
            while True:
                iteration_count += 1
                elapsed_sec = time.perf_counter() - start_time

                iteration, new_failures, total_tool_calls, evidence_iteration_count = self.iteration_controller.execute_iteration(
                    request=request,
                    iteration_number=iteration_count,
                    source_repo_path=source_repo_path,
                    source_code_map=source_code_map,
                    ws_path=ws_path,
                    failures=current_failures,
                    previous_iterations=tuple(iterations),
                    tool_call_count=total_tool_calls,
                    evidence_iteration_count=evidence_iteration_count,
                    run_tests=run_tests,
                )

                iterations.append(iteration)
                if new_failures:
                    failure_history.extend(new_failures)
                    current_failures = new_failures

                if iteration.patch:
                    total_changed_lines += iteration.patch.lines_added + iteration.patch.lines_removed

                if iteration.test_result:
                    total_test_runtime += iteration.test_result.execution_time_ms / 1000.0

                # Compute iteration fingerprint for repeated failure detection
                fingerprint = FingerprintManager.compute_iteration_fingerprint(
                    failures=current_failures,
                    diagnosis=iteration.diagnosis,
                    patch=iteration.patch,
                )
                seen_fingerprints.append(fingerprint)

                # Check stopping conditions
                should_stop, stop_status, stop_reason = self.stopping_evaluator.evaluate(
                    iterations=tuple(iterations),
                    test_result=iteration.test_result,
                    validation_result=None,
                    total_tool_calls=total_tool_calls,
                    total_test_runtime_sec=total_test_runtime,
                    elapsed_seconds=elapsed_sec,
                    total_changed_lines=total_changed_lines,
                    seen_fingerprints=tuple(seen_fingerprints),
                )

                if should_stop or iteration.status == "SUCCESS":
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    final_patch = iteration.patch if iteration.status == "SUCCESS" else request.initial_patch
                    final_status = "SUCCESS" if iteration.status == "SUCCESS" else stop_status

                    return RepairResult(
                        status=final_status,
                        iterations=tuple(iterations),
                        final_patch=final_patch,
                        final_test_result=iteration.test_result or initial_test_res,
                        failure_history=tuple(failure_history),
                        stopping_reason=stop_reason if iteration.status != "SUCCESS" else "Targeted tests passed cleanly.",
                        execution_time_ms=elapsed_ms,
                    )

    def repair_once(
        self,
        request: RepairRequest,
        source_repo_path: str | Path,
        source_code_map: dict[str, str],
    ) -> RepairResult:
        """Single-pass repair helper."""
        return self.repair(request, source_repo_path, source_code_map, run_tests=False)

    def diagnose(self, failures: Sequence[FailureRecord]) -> FailureDiagnosis:
        """Public API for failure diagnosis."""
        return self.diagnoser.diagnose_failure(failures)

    def plan(
        self,
        initial_plan: ChangePlan,
        diagnosis: FailureDiagnosis,
        failures: Sequence[FailureRecord],
    ) -> RepairPlan:
        """Public API for repair planning."""
        return self.planner.create_repair_plan(initial_plan, diagnosis, failures)

    def validate(self, plan: RepairPlan, patch: Patch | None) -> tuple[bool, str | None]:
        """Public API for repair plan & patch safety validation."""
        safe_plan, err = RepairSafetyValidator.validate_plan_safety(plan)
        if not safe_plan:
            return False, err
        if patch:
            return RepairSafetyValidator.validate_patch_safety(patch)
        return True, None

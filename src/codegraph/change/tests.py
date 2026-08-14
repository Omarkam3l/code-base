"""Pytest test runner for Phase 8 isolated workspace validation."""

import sys
import time
import subprocess
from pathlib import Path
from codegraph.change.models import TestExecutionResult
from codegraph.change.safety import DEFAULT_TEST_TIMEOUT, MAX_TEST_TIMEOUT


class TestRunner:
    """Hardcoded Pytest runner executing only inside isolated workspace."""

    def __init__(self, timeout: int = DEFAULT_TEST_TIMEOUT) -> None:
        self.timeout = min(timeout, MAX_TEST_TIMEOUT)

    def run_tests(
        self,
        workspace_path: Path,
        target_test_file: str | None = None,
    ) -> TestExecutionResult:
        """Run pytest inside isolated workspace with hardcoded subprocess arguments."""
        abs_workspace = Path(workspace_path).resolve()

        # Hardcode exact executable and arguments (prevent any injection)
        cmd = [sys.executable, "-m", "pytest", "-q"]

        if target_test_file:
            # Validate target test file exists in workspace
            test_path = (abs_workspace / target_test_file).resolve()
            try:
                test_path.relative_to(abs_workspace)
            except ValueError:
                return TestExecutionResult(
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=1,
                    test_failures=(f"Target test file outside workspace: {target_test_file}",),
                )

            if not test_path.exists():
                return TestExecutionResult(
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=1,
                    test_failures=(f"Target test file non-existent: {target_test_file}",),
                )
            cmd.append(str(test_path))
        else:
            cmd.append("tests")

        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(abs_workspace),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if res.returncode == 0:
                return TestExecutionResult(
                    tests_run=1,
                    tests_passed=1,
                    tests_failed=0,
                    execution_time_ms=elapsed_ms,
                    baseline_failed=False,
                )
            else:
                failures = [line for line in res.stdout.splitlines() if "FAILED" in line or "ERROR" in line]
                if not failures:
                    failures = [res.stderr[:500]] if res.stderr else ["Pytest execution failed"]

                return TestExecutionResult(
                    tests_run=1,
                    tests_passed=0,
                    tests_failed=len(failures),
                    test_failures=tuple(failures),
                    execution_time_ms=elapsed_ms,
                    baseline_failed=False,
                )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TestExecutionResult(
                tests_run=0,
                tests_passed=0,
                tests_failed=1,
                test_failures=(f"Pytest execution timed out after {self.timeout}s",),
                execution_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TestExecutionResult(
                tests_run=0,
                tests_passed=0,
                tests_failed=1,
                test_failures=(f"Test execution error: {e}",),
                execution_time_ms=elapsed_ms,
            )

"""Pytest test runner for Phase 8 isolated workspace validation."""

import re
import sys
import time
import subprocess
from pathlib import Path
from codegraph.change.models import TestExecutionResult
from codegraph.change.safety import DEFAULT_TEST_TIMEOUT, MAX_TEST_TIMEOUT

# Matches pytest's short summary line, e.g. "3 passed, 1 failed, 2 errors in 0.42s"
_SUMMARY_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")


def _parse_pytest_summary(stdout: str) -> dict[str, int]:
    """Parse pytest's final summary line into counts per outcome."""
    counts: dict[str, int] = {}
    for line in reversed(stdout.splitlines()):
        matches = _SUMMARY_RE.findall(line)
        if matches:
            for num, label in matches:
                key = "error" if label == "errors" else label
                counts[key] = counts.get(key, 0) + int(num)
            break
    return counts


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

            summary = _parse_pytest_summary(res.stdout)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0) + summary.get("error", 0)
            skipped = summary.get("skipped", 0)
            total_run = passed + failed + skipped

            # Pytest exits with code 5 (and no summary counts) when it collects zero
            # tests. Report tests_run=0 explicitly so callers can distinguish "no test
            # suite exists" from "tests ran and something failed".
            if res.returncode == 5 or (total_run == 0 and "no tests ran" in res.stdout.lower()):
                return TestExecutionResult(
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=0,
                    test_failures=("No tests collected in workspace (no tests ran).",),
                    execution_time_ms=elapsed_ms,
                    baseline_failed=False,
                )

            if res.returncode == 0:
                return TestExecutionResult(
                    tests_run=total_run or 1,
                    tests_passed=passed or 1,
                    tests_failed=failed,
                    execution_time_ms=elapsed_ms,
                    baseline_failed=False,
                )
            else:
                failures = [line for line in res.stdout.splitlines() if "FAILED" in line or "ERROR" in line]
                if not failures:
                    failures = [res.stderr[:500]] if res.stderr else ["Pytest execution failed"]

                return TestExecutionResult(
                    tests_run=total_run or 1,
                    tests_passed=passed,
                    tests_failed=failed or len(failures),
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

"""Deterministic stopping evaluator and repeated failure fingerprinting for Phase 9."""

import hashlib
from typing import Sequence
from codegraph.change.models import Patch, TestExecutionResult, ValidationResult
from codegraph.repair.models import FailureDiagnosis, FailureRecord, RepairIteration


class FingerprintManager:
    """Computes deterministic hashes for failures, diagnoses, and patches."""

    @staticmethod
    def compute_failure_fingerprint(failures: Sequence[FailureRecord]) -> str:
        """Hash tuple of (test_name, error_type, normalized_error_message)."""
        if not failures:
            return "EMPTY_FAILURES"
        components = [f"{f.test_name}|{f.error_type}|{f.error_message.strip().lower()}" for f in failures]
        combined = ";".join(sorted(components))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def compute_diagnosis_fingerprint(diagnosis: FailureDiagnosis | None) -> str:
        """Hash tuple of (category, root_cause, affected_entities)."""
        if not diagnosis:
            return "EMPTY_DIAGNOSIS"
        entities = ",".join(sorted(diagnosis.affected_entities))
        combined = f"{diagnosis.category.value}|{diagnosis.root_cause_hypothesis.strip().lower()}|{entities}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def compute_patch_fingerprint(patch: Patch | None) -> str:
        """Hash normalized unified diff patch string."""
        if not patch or not patch.unified_diff:
            return "EMPTY_PATCH"
        norm = patch.unified_diff.strip()
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def compute_iteration_fingerprint(
        failures: Sequence[FailureRecord],
        diagnosis: FailureDiagnosis | None,
        patch: Patch | None,
    ) -> str:
        """Combine failure, diagnosis, and patch fingerprints."""
        ff = FingerprintManager.compute_failure_fingerprint(failures)
        df = FingerprintManager.compute_diagnosis_fingerprint(diagnosis)
        pf = FingerprintManager.compute_patch_fingerprint(patch)
        return f"{ff}:{df}:{pf}"


class StoppingEvaluator:
    """Evaluates terminal criteria, budget limits, and repeated failure loops."""

    def __init__(
        self,
        max_iterations: int = 5,
        max_total_tool_calls: int = 30,
        max_total_test_runtime_sec: float = 300.0,
        max_elapsed_seconds: float = 600.0,
        max_total_changed_lines: int = 600,
    ) -> None:
        self.max_iterations = max_iterations
        self.max_total_tool_calls = max_total_tool_calls
        self.max_total_test_runtime_sec = max_total_test_runtime_sec
        self.max_elapsed_seconds = max_elapsed_seconds
        self.max_total_changed_lines = max_total_changed_lines

    def evaluate(
        self,
        iterations: Sequence[RepairIteration],
        test_result: TestExecutionResult | None,
        validation_result: ValidationResult | None,
        total_tool_calls: int = 0,
        total_test_runtime_sec: float = 0.0,
        elapsed_seconds: float = 0.0,
        total_changed_lines: int = 0,
        seen_fingerprints: Sequence[str] = (),
    ) -> tuple[bool, str, str]:
        """Returns (should_stop, status, stopping_reason).

        Status values: SUCCESS, FAILURE, ABSTAIN.
        """
        # 1. Success condition: targeted tests pass AND no new regression failures
        if test_result and test_result.tests_failed == 0 and (validation_result is None or validation_result.syntax_valid):
            if not test_result.baseline_failed or len(test_result.new_failures) == 0:
                return True, "SUCCESS", "Targeted tests passed and full regression suite clean."

        # 2. Repeated failure loop check
        if seen_fingerprints and len(seen_fingerprints) != len(set(seen_fingerprints)):
            return True, "FAILURE", "Repeated identical (failure + diagnosis + patch) attempt detected."

        # 3. Iteration limit check
        if len(iterations) >= self.max_iterations:
            return True, "FAILURE", f"Maximum iteration limit ({self.max_iterations}) reached."

        # 4. Budget limit checks
        if total_tool_calls >= self.max_total_tool_calls:
            return True, "FAILURE", f"Maximum tool call limit ({self.max_total_tool_calls}) reached."

        if total_test_runtime_sec >= self.max_total_test_runtime_sec:
            return True, "FAILURE", f"Maximum test runtime limit ({self.max_total_test_runtime_sec}s) reached."

        if elapsed_seconds >= self.max_elapsed_seconds:
            return True, "FAILURE", f"Maximum elapsed time limit ({self.max_elapsed_seconds}s) reached."

        if total_changed_lines >= self.max_total_changed_lines:
            return True, "FAILURE", f"Maximum total changed lines limit ({self.max_total_changed_lines}) reached."

        # 5. Abstention triggers (low confidence or unsupported failure)
        if iterations:
            last_it = iterations[-1]
            if last_it.diagnosis and last_it.diagnosis.confidence == "LOW":
                if last_it.diagnosis.category in ("ENVIRONMENT_FAILURE", "UNKNOWN"):
                    return True, "ABSTAIN", f"Abstaining due to {last_it.diagnosis.category.value} with low confidence."

        return False, "RUNNING", "Continuing repair loop."

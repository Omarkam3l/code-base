"""RegressionDetector comparing current run metrics against golden baselines."""

import json
from pathlib import Path
from typing import Any
from codegraph.evaluation.models import RegressionReport


class RegressionDetector:
    """Detects metric regressions against stored golden baseline thresholds."""

    DEFAULT_BASELINE_PATH = Path("tests/evaluation/baselines/golden_baselines.json")

    def __init__(self, baseline_path: str | Path | None = None) -> None:
        self.baseline_path = Path(baseline_path or self.DEFAULT_BASELINE_PATH)

    def load_baseline(self) -> dict[str, float]:
        """Load golden baseline metrics JSON file."""
        if not self.baseline_path.exists():
            return {}
        try:
            return json.loads(self.baseline_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def evaluate_regression(
        self,
        current_metrics: dict[str, float],
        tolerance_factor: float = 0.95,
    ) -> RegressionReport:
        """Compare current metrics against stored golden baselines."""
        baseline = self.load_baseline()
        if not baseline:
            return RegressionReport(is_passed=True, current_metrics=current_metrics)

        regressions: list[str] = []
        improvements: list[str] = []

        for metric_name, base_val in baseline.items():
            if metric_name not in current_metrics:
                continue

            curr_val = current_metrics[metric_name]

            # For latencies, lower is better
            if "latency" in metric_name.lower():
                if curr_val > base_val * 1.50:  # Allow up to 50% latency increase
                    regressions.append(f"Latency regression in '{metric_name}': current {curr_val:.2f}ms > baseline {base_val:.2f}ms * 1.5")
                elif curr_val < base_val:
                    improvements.append(f"Latency improvement in '{metric_name}': current {curr_val:.2f}ms < baseline {base_val:.2f}ms")
            else:
                # For accuracy/recall, higher is better
                min_acceptable = base_val * tolerance_factor
                if curr_val < min_acceptable:
                    regressions.append(f"Metric regression in '{metric_name}': current {curr_val:.4f} < threshold {min_acceptable:.4f} (baseline {base_val:.4f})")
                elif curr_val > base_val:
                    improvements.append(f"Metric improvement in '{metric_name}': current {curr_val:.4f} > baseline {base_val:.4f}")

        is_passed = len(regressions) == 0
        return RegressionReport(
            is_passed=is_passed,
            regressions=tuple(regressions),
            improvements=tuple(improvements),
            baseline_metrics=baseline,
            current_metrics=current_metrics,
        )

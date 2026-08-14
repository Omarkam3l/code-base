"""MetricsCollector for aggregating component latency percentiles, error rates, and resource usage."""

import numpy as np
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class MetricsCollector:
    """Collects system-wide metric measurements and calculates statistical percentiles."""

    latencies: list[float] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)
    gauges: dict[str, float] = field(default_factory=dict)

    def record_latency(self, latency_ms: float) -> None:
        """Record latency measurement in milliseconds."""
        self.latencies.append(latency_ms)

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment named counter."""
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge value."""
        self.gauges[name] = value

    def get_latency_stats(self) -> dict[str, float]:
        """Compute P50, P95, and P99 latency percentiles."""
        if not self.latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}

        arr = np.array(sorted(self.latencies))
        return {
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "avg": float(np.mean(arr)),
        }

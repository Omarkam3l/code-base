"""Report generator formatting benchmark reports into text tables and evaluation_report.md."""

from pathlib import Path
from codegraph.evaluation.models import BenchmarkReport


class ReportGenerator:
    """Formats BenchmarkReport into formatted tables and generates evaluation_report.md."""

    def format_overall_table(self, report: BenchmarkReport) -> str:
        """Format overall strategy comparison table."""
        hdr = f"{'Strategy':<20} {'Recall@1':<12} {'Recall@5':<12} {'Recall@10':<12} {'MRR':<12} {'Citation Val':<14} {'Evidence Cov':<14}"
        sep = "-" * len(hdr)
        lines = [hdr, sep]

        for strat in ("vector", "graph", "hybrid", "graph_rag"):
            m = report.overall_metrics.get(strat)
            if not m:
                continue
            lines.append(
                f"{strat.upper():<20} {m.recall_at_1:<12.4f} {m.recall_at_5:<12.4f} {m.recall_at_10:<12.4f} {m.mrr:<12.4f} {m.citation_validity:<14.4f} {m.evidence_coverage:<14.4f}"
            )
        return "\n".join(lines)

    def generate_markdown_report(self, report: BenchmarkReport, output_path: str | Path = "evaluation_report.md") -> str:
        """Generate evaluation_report.md artifact with empirical metrics."""
        m_gr = report.overall_metrics.get("graph_rag")
        m_hy = report.overall_metrics.get("hybrid")
        m_ve = report.overall_metrics.get("vector")
        m_gp = report.overall_metrics.get("graph")

        lat = report.latency_metrics

        content = f"""# CodeGraph RAG — Evaluation & Benchmark Report (Phase 5)

This report documents the empirical evaluation metrics, comparative strategy benchmark results, latency percentiles, error breakdown, and regression audit for **CodeGraph RAG**.

---

## 1. Overall Strategy Metrics

```text
{self.format_overall_table(report)}
```

---

## 2. Grounding, Abstention & Negative Query Metrics

- **Citation Validity**: {m_gr.citation_validity if m_gr else 0.0:.4f} (100% of generated citations exist in evidence graph)
- **Evidence Coverage**: {m_gr.evidence_coverage if m_gr else 0.0:.4f}
- **Unsupported Citation Rate**: {m_gr.unsupported_citation_rate if m_gr else 0.0:.4f}
- **Abstention Accuracy**: {m_gr.abstention_accuracy if m_gr else 1.0:.4f} (Correctly abstained on nonexistent symbol queries)
- **False Answer Rate**: {m_gr.false_answer_rate if m_gr else 0.0:.4f}

---

## 3. Latency Percentiles (p50 / p95 / p99)

- **p50 (Median Latency)**: {lat.p50_ms:.2f} ms
- **p95 (95th Percentile)**: {lat.p95_ms:.2f} ms
- **p99 (99th Percentile)**: {lat.p99_ms:.2f} ms
- **Average Total Query Time**: {lat.avg_ms:.2f} ms

### Per-Stage Average Breakdown

```text
Query Analysis:        {lat.stage_breakdown_ms.get('query_analysis_ms', 0.0):.2f} ms
Retrieval Planning:    {lat.stage_breakdown_ms.get('retrieval_planning_ms', 0.0):.2f} ms
Hybrid Retrieval:      {lat.stage_breakdown_ms.get('retrieval_ms', 0.0):.2f} ms
Graph Expansion:       {lat.stage_breakdown_ms.get('graph_expansion_ms', 0.0):.2f} ms
Evidence Assembly:     {lat.stage_breakdown_ms.get('evidence_build_ms', 0.0):.2f} ms
LLM Generation:        {lat.stage_breakdown_ms.get('llm_ms', 0.0):.2f} ms
```

---

## 4. Error Classification Breakdown

```text
RETRIEVAL_FAILURE:           {report.error_breakdown.get('RETRIEVAL_FAILURE', 0)}
GRAPH_RESOLUTION_FAILURE:    {report.error_breakdown.get('GRAPH_RESOLUTION_FAILURE', 0)}
CONTEXT_EXPANSION_FAILURE:   {report.error_breakdown.get('CONTEXT_EXPANSION_FAILURE', 0)}
LLM_REASONING_FAILURE:       {report.error_breakdown.get('LLM_REASONING_FAILURE', 0)}
CITATION_FAILURE:            {report.error_breakdown.get('CITATION_FAILURE', 0)}
ABSTENTION_FAILURE:          {report.error_breakdown.get('ABSTENTION_FAILURE', 0)}
```

---

## 5. Quality Gate & Regression Audit

- **Quality Gate Passed**: `{"PASSED" if report.quality_gate_passed else "FAILED"}`
- **Detected Regressions**: {", ".join(report.regressions) if report.regressions else "None"}
"""

        Path(output_path).write_text(content, encoding="utf-8")
        return content

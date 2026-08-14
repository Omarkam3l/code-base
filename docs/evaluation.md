# CodeGraph RAG — Evaluation Methodology & Metrics

## 1. Overview
The evaluation framework (`src/codegraph/evaluation/`) provides rigorous, system-wide benchmarking across 500 cases covering retrieval, graph reasoning, multi-hop pathfinding, agentic investigation, code change planning, iterative repair, git workflows, GitHub integration, and prompt injection defense.

---

## 2. Key Metrics & Formulas

### Retrieval
- **Recall@K**: Proportion of ground-truth relevant symbols retrieved in top-K results.
- **MRR (Mean Reciprocal Rank)**: $\frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$

### Iterative Repair
- **First-Patch Success Rate**: Proportion of patches validated on initial attempt.
- **Iterative Recovery Rate**: $\frac{\text{successful repair after first patch failure}}{\text{first patch failures}}$
- **Abstention Accuracy**: Accuracy of abstaining when evidence is missing or ambiguous.

### Regression Detection
- **Regression Gates**: `RegressionDetector` compares current run metrics against golden baselines (`tests/evaluation/baselines/golden_baselines.json`).

---

## 3. Dataset Distribution (500 Cases)
Dataset partitioning across 30 distinct categories ensures comprehensive coverage of realistic and adversarial engineering scenarios.

# CodeGraph RAG — Benchmarking & Reproducibility Methodology

## 1. Reproducibility Guarantee
Every benchmark evaluation run records a `ReproducibilityMetadata` record containing:
- Run ID, Git commit hash, dataset version
- Model & embedding model configurations
- Random seed (default: 42)
- Execution timestamp

---

## 2. Benchmark Suites
1. **500-Case Evaluation Dataset**: Full benchmark across 30 categories.
2. **Repository Size Fixtures**: Benchmarks performance scaling from small to large repositories.
3. **Adversarial Suite**: Prompt injection and malicious payload rejection benchmarks.

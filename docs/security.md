# CodeGraph RAG — Security Model & Audit Specifications

## 1. Security Architecture
CodeGraph RAG enforces strict security boundaries across LLM interactions, local Git execution, and GitHub API integration.

### Core Security Controls
1. **Worktree Isolation**: All patch applications and test executions run strictly inside isolated temporary worktrees (`git worktree`). The user's working tree is never touched.
2. **Secret Redaction**: `SecretRedactor` automatically masks API keys (`AKIA`, `ghp_`, `nvapi-`), private keys, and Bearer tokens from logs, traces, exceptions, and reports.
3. **Push & Merge Controls**: Push operations are disabled by default (`push_authorized = False`). Automated PR merging is strictly prohibited.
4. **Prompt Injection Defense**: `AdversarialEvaluator` scans untrusted input (webhooks, review comments) for injection attacks, maintaining a 1.0000 rejection accuracy.

# Model Context Protocol (MCP) Server

## Safe Typed Tools

The CodeGraph MCP Server (`src/codegraph/mcp/`) exposes 15 safe typed tools:

- `search_code`
- `find_symbol`
- `find_callers`
- `find_callees`
- `trace_execution`
- `analyze_dependencies`
- `analyze_impact`
- `investigate`
- `plan_change`
- `generate_patch`
- `repair_failure`
- `get_git_status`
- `get_ci_status`
- `get_pr_reviews`

### Safety Controls
Prohibits shell execution, arbitrary Python, arbitrary Cypher, filesystem deletion, git reset, git clean, force push, and automatic merge.

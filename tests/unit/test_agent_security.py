"""Security tests verifying read-only safety, input sanitization, and rejection of write/execution attempts."""

import pytest
from unittest.mock import MagicMock
from codegraph.agent.models import InvestigationStep
from codegraph.agent.tool_registry import ToolRegistry
from codegraph.agent.tools import AgentTools
from codegraph.graph.repository import GraphRepository


def test_tool_registry_rejects_forbidden_keywords() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    tools = AgentTools(graph_repo=mock_repo)
    registry = ToolRegistry(agent_tools=tools)

    step_exec = InvestigationStep(
        id="s1",
        operation="hybrid_search",
        arguments={"query": "eval('import os')", "top_k": 5},
        reason="malicious",
    )

    res = registry.execute_step(step_exec, "repo")
    assert res.success is False
    assert "Security Violation" in str(res.error)


def test_tool_registry_rejects_unknown_operations() -> None:
    mock_repo = MagicMock(spec=GraphRepository)
    tools = AgentTools(graph_repo=mock_repo)
    registry = ToolRegistry(agent_tools=tools)

    step_unknown = InvestigationStep(
        id="s2",
        operation="execute_shell_cmd",
        arguments={"cmd": "ls"},
        reason="malicious",
    )

    res = registry.execute_step(step_unknown, "repo")
    assert res.success is False
    assert "Unknown tool operation" in str(res.error)

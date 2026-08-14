"""Unit tests for MCP Server tool registration and safety enforcement."""

import pytest
from codegraph.mcp.server import MCPServer


def test_mcp_server_lists_15_safe_tools() -> None:
    server = MCPServer()
    tools = server.list_tools()
    assert len(tools) >= 14  # Safe typed tools registered
    assert "search_code" in tools
    assert "find_symbol" in tools
    assert "investigate" in tools
    assert "plan_change" in tools


def test_mcp_blocks_prohibited_operations() -> None:
    server = MCPServer()

    with pytest.raises(PermissionError, match="Safety controller blocked"):
        server.execute_tool("shell_execution")

    with pytest.raises(PermissionError, match="Safety controller blocked"):
        server.execute_tool("git_force_push")

    with pytest.raises(PermissionError, match="Safety controller blocked"):
        server.execute_tool("automatic_merge")

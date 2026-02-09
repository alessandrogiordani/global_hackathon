"""
Integration tests for the MCP vulnerability scanner server.

These tests start the server, verify tools are registered correctly,
and test basic functionality.
"""

import subprocess
import time
import pytest
from databricks_mcp import DatabricksMCPClient


@pytest.fixture(scope="module")
def mcp_server():
    """Start the MCP server for testing."""
    # Start server process
    process = subprocess.Popen(
        ["uv", "run", "vulnerability-scanner-mcp", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(3)

    yield "http://localhost:8001"

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


def test_server_health(mcp_server):
    """Test that the server is running and healthy."""
    import requests

    response = requests.get(f"{mcp_server}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_list_tools(mcp_server):
    """Test that all expected tools are registered."""
    client = DatabricksMCPClient(server_url=mcp_server)
    tools = client.list_tools()

    tool_names = [tool.name for tool in tools]

    # Verify all 7 tools are present
    expected_tools = [
        "scan_repo_dependencies",
        "check_vulnerabilities",
        "suggest_upgrades",
        "generate_patch_preview",
        "apply_security_patches",
        "get_vulnerability_details",
        "monitor_repo_security",
    ]

    for expected_tool in expected_tools:
        assert (
            expected_tool in tool_names
        ), f"Tool '{expected_tool}' not found in registered tools"

    assert len(tools) >= 7, f"Expected at least 7 tools, found {len(tools)}"


def test_tool_has_descriptions(mcp_server):
    """Test that all tools have proper descriptions."""
    client = DatabricksMCPClient(server_url=mcp_server)
    tools = client.list_tools()

    for tool in tools:
        assert hasattr(tool, "name"), "Tool missing name"
        assert tool.name, "Tool name is empty"
        # Check for description (tool may have different attribute names)
        has_description = (
            hasattr(tool, "description")
            and tool.description
            or hasattr(tool, "help_text")
            and tool.help_text
        )
        assert has_description, f"Tool '{tool.name}' missing description"


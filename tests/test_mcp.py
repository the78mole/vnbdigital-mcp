"""MCP-protocol-level tests for the vnbdigital MCP server.

These tests call ``mcp.list_tools()`` and ``mcp.call_tool()`` directly on the
FastMCP instance, which exercises the full MCP dispatch path (argument
validation, tool lookup, serialisation) without needing a real HTTP transport.
"""

from unittest.mock import patch

import pytest

from vnbdigital_mcp.server import mcp

# All tool names that must be registered on the server.
EXPECTED_TOOLS = {
    "get_operator",
    "get_operator_details",
    "get_operators",
    "search",
    "search_by_coordinates",
    "search_by_postcode",
    "get_nsp_operator",
    "get_msp_operator",
    "bdew_lookup_by_company_code",
    "bdew_lookup_by_market_code",
    "bdew_get_market_function_detail",
}


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_all_expected_tools_are_registered():
    tools = await mcp.list_tools()
    registered = {t.name for t in tools}
    assert EXPECTED_TOOLS == registered, (
        f"Missing: {EXPECTED_TOOLS - registered}, Extra: {registered - EXPECTED_TOOLS}"
    )


@pytest.mark.anyio
async def test_each_tool_has_description():
    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"


@pytest.mark.anyio
async def test_get_operator_has_operator_id_parameter():
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "get_operator")
    params = tool.inputSchema.get("properties", {})
    assert "operator_id" in params


# ---------------------------------------------------------------------------
# Tool call – get_operator
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_call_get_operator_returns_operator_data(mock_operator):
    with patch("vnbdigital_mcp.server._client") as mock_client:
        mock_client.get_operator.return_value = mock_operator
        result = await mcp.call_tool("get_operator", {"operator_id": "179"})

    data = _parse_result(result)
    assert data["id"] == 179
    assert data["name"] == "ESTW - Erlanger Stadtwerke AG"
    assert data["city"] == "Erlangen"


@pytest.mark.anyio
async def test_call_get_operator_not_found_returns_error_dict():
    with patch("vnbdigital_mcp.server._client") as mock_client:
        mock_client.get_operator.return_value = None
        result = await mcp.call_tool("get_operator", {"operator_id": "999"})

    data = _parse_result(result)
    assert "error" in data
    assert "999" in data["error"]


@pytest.mark.anyio
async def test_call_get_operator_connection_error_returns_error_dict():
    with patch("vnbdigital_mcp.server._client") as mock_client:
        mock_client.get_operator.side_effect = ConnectionError("timeout")
        result = await mcp.call_tool("get_operator", {"operator_id": "179"})

    data = _parse_result(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# Tool call – search
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_call_search_returns_list(mock_postcode_hit):
    with patch("vnbdigital_mcp.server._client") as mock_client:
        mock_client.search.return_value = [mock_postcode_hit]
        result = await mcp.call_tool("search", {"search_term": "63739"})

    data = _parse_result(result)
    # FastMCP wraps list return values in {"result": [...]}
    hits = data["result"] if isinstance(data, dict) and "result" in data else data
    assert isinstance(hits, list)
    assert hits[0]["type"] == "POSTCODE"


# ---------------------------------------------------------------------------
# Tool call – get_operators (batch)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_call_get_operators_empty_returns_error():
    result = await mcp.call_tool("get_operators", {"operator_ids": []})
    data = _parse_result(result)
    assert "error" in data


@pytest.mark.anyio
async def test_call_get_operators_batch(mock_operator):
    with patch("vnbdigital_mcp.server._client") as mock_client:
        mock_client.get_operator.return_value = mock_operator
        result = await mcp.call_tool("get_operators", {"operator_ids": ["179", "180"]})

    data = _parse_result(result)
    assert "179" in data
    assert "180" in data


# ---------------------------------------------------------------------------
# Tool call – BDEW tools
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_call_bdew_lookup_by_company_code(mock_operator):
    expected = {"code": 660188, "name": "ESTW", "market_functions": []}
    with patch("vnbdigital_mcp.server.lookup_bdew_by_company_code") as mock_fn:
        mock_fn.return_value = expected
        result = await mcp.call_tool("bdew_lookup_by_company_code", {"company_uid": 660188})

    data = _parse_result(result)
    assert data["code"] == 660188


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _parse_result(result):
    """Extract the raw Python value returned by mcp.call_tool().

    FastMCP returns a tuple ``(list[ContentBlock], raw_value)``.
    Index 1 is the un-serialised Python dict/list.
    """
    return result[1]

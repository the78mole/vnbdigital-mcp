"""
vnbdigital MCP Server

Exposes vnbdigital.de grid operator data (Verteilnetzbetreiber) via the
Model Context Protocol (MCP). Tools wrap the verified vnbdigital-client library.
"""

import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from vnbdigital_client import (
    Operator,
    VNBDigitalClient,
    lookup_bdew_by_company_code,
    lookup_bdew_by_market_code,
    lookup_bdew_market_function_detail,
)

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "vnbdigital",
    instructions=(
        "This server provides information about German distribution grid operators (VNB) "
        "from the vnbdigital.de database. "
        "Operators are looked up by their BDEW code number or vnbdigital ID. "
        "Known example IDs:"
        "-  179 (ESTW - Erlanger Stadtwerke AG)"
        "-  180 (Stadtwerke Eschwege GmbH)"
        "-  99 (Stadtwerke Bramsche GmbH)"
    ),
)

_api_url: str | None = os.environ.get("VNBDIGITAL_API_URL")
_timeout: int = int(os.environ.get("VNBDIGITAL_TIMEOUT", "30"))
_client = VNBDigitalClient(api_url=_api_url, timeout=_timeout)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _operator_to_dict(op: Operator) -> dict[str, Any]:
    """Serialize an Operator dataclass to a plain dict for MCP responses."""
    return {
        "id": op.id,
        "name": op.name,
        "address": op.address,
        "postcode": op.postcode,
        "city": op.city,
        "phone": op.phone,
        "contact": op.contact,
        "website": op.website,
        "description": op.description,
        "types": op.types,
        "layer_url": op.layer_url,
        "bbox": op.bbox,
        "regions": [{"id": r.id, "name": r.name} for r in op.regions],
        "image_url": op.image_url,
        "logo_url": op.logo_url,
        "public_required": op.public_required,
        "clicks": op.clicks,
        "services": op.raw.get("services", []),
        "documents": op.raw.get("documents", []),
    }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_operator(operator_id: str) -> dict[str, Any]:
    """Fetch basic information for a distribution grid operator.

    Returns name, address, phone, website, regions and bounding box
    for the specified operator.

    Args:
        operator_id: BDEW code or vnbdigital ID of the operator (e.g. "179").

    Returns:
        Dict with operator master data, or {"error": ...} if not found.
    """
    try:
        op = _client.get_operator(operator_id)
    except ConnectionError as exc:
        return {"error": f"Connection error: {exc}"}
    except RuntimeError as exc:
        return {"error": f"API error: {exc}"}

    if op is None:
        return {"error": f"Operator '{operator_id}' not found."}

    return _operator_to_dict(op)


@mcp.tool()
def get_operator_details(operator_id: str) -> dict[str, Any]:
    """Fetch detailed information for a distribution grid operator.

    Returns all basic fields plus services, documents, logo URL,
    image URL, click count and further metadata.

    Args:
        operator_id: BDEW code or vnbdigital ID of the operator (e.g. "179").

    Returns:
        Dict with all available operator data, or {"error": ...} if not found.
    """
    try:
        op = _client.get_operator_details(operator_id)
    except ConnectionError as exc:
        return {"error": f"Connection error: {exc}"}
    except RuntimeError as exc:
        return {"error": f"API error: {exc}"}

    if op is None:
        return {"error": f"Operator '{operator_id}' not found."}

    return _operator_to_dict(op)


@mcp.tool()
def get_operators(operator_ids: list[str]) -> dict[str, Any]:
    """Fetch multiple distribution grid operators in a single batch request.

    Retrieves basic master data for each given ID. IDs that cannot be
    found are returned as ``null`` in the result.

    Args:
        operator_ids: List of BDEW codes or vnbdigital IDs (e.g. ["179", "180"]).

    Returns:
        Dict {operator_id: operator dict or null} for all requested IDs.
    """
    if not operator_ids:
        return {"error": "No operator IDs provided."}
    if len(operator_ids) > 50:
        return {"error": "Maximum 50 IDs per request allowed."}

    results: dict[str, Any] = {}
    for oid in operator_ids:
        try:
            op = _client.get_operator(oid)
            results[oid] = _operator_to_dict(op) if op is not None else None
        except (ConnectionError, RuntimeError) as exc:
            results[oid] = {"error": str(exc)}

    return results


@mcp.tool()
def search(search_term: str) -> list[dict[str, Any]]:
    """Free-text search on vnbdigital.de (postcode, name, region, city).

    Uses the same search endpoint as the vnbdigital.de website. Returns
    hits of various types: ``VNB`` (grid operator), ``POSTCODE``,
    ``REGION``, ``LOCATION`` (address/city).

    Args:
        search_term: Search query, e.g. postcode ``"63739"``, city name,
            or grid operator name.

    Returns:
        List of hits with ``id``, ``title``, ``subtitle``, ``type``
        and ``url``.
    """
    try:
        results = _client.search(search_term)
    except (ConnectionError, RuntimeError) as exc:
        return [{"error": str(exc)}]

    return [
        {
            "id": r.id,
            "title": r.title,
            "subtitle": r.subtitle,
            "type": r.type,
            "url": r.url,
            "logo_url": r.logo_url,
        }
        for r in results
    ]


@mcp.tool()
def search_by_coordinates(
    lat: float,
    lon: float,
    only_nap: bool = False,
    voltage_types: list[str] | None = None,
) -> dict[str, Any]:
    """Find grid operators responsible for a GPS coordinate.

    Returns all operators covering the given location
    (low voltage and medium voltage).

    Args:
        lat: Latitude, e.g. ``49.979276``.
        lon: Longitude, e.g. ``9.587243``.
        only_nap: Return only grid connection points (default: False).
        voltage_types: Voltage levels, e.g. ``["Niederspannung"]``.
            Default: Niederspannung + Mittelspannung.

    Returns:
        Dict with ``geometry``, ``regions`` and ``vnbs`` (list of operators).
    """
    coords = f"{lat},{lon}"
    try:
        result = _client.search_by_coordinates(
            coordinates=coords,
            only_nap=only_nap,
            voltage_types=voltage_types,
        )
    except (ConnectionError, RuntimeError) as exc:
        return {"error": str(exc)}

    return result


@mcp.tool()
def search_by_postcode(
    postcode: str,
    only_nap: bool = False,
    voltage_types: list[str] | None = None,
) -> dict[str, Any]:
    """Find grid operators responsible for a German postcode.

    Automatically performs a postcode search first, then returns the
    responsible operators for the first POSTCODE hit.

    Args:
        postcode: German postcode, e.g. ``"63739"``.
        only_nap: Return only grid connection points (default: False).
        voltage_types: Voltage levels. Default: Niederspannung + Mittelspannung.

    Returns:
        Dict with ``postcode`` info, ``regions`` and ``vnbs`` (operators).
    """
    try:
        results = _client.search(postcode)
    except (ConnectionError, RuntimeError) as exc:
        return {"error": str(exc)}

    postcode_hit = next((r for r in results if r.type == "POSTCODE"), None)
    if postcode_hit is None:
        return {"error": f"Postcode '{postcode}' not found."}

    try:
        result = _client.search_by_postcode(
            postcode_id=postcode_hit.id,
            only_nap=only_nap,
            voltage_types=voltage_types,
        )
    except (ConnectionError, RuntimeError) as exc:
        return {"error": str(exc)}

    return result


# ---------------------------------------------------------------------------
# Helpers for voltage-specific lookups (shared by nsp / msp tools)
# ---------------------------------------------------------------------------


def _resolve_operators_by_voltage(location: str, voltage_type: str) -> list[dict[str, Any]]:
    """Resolve operators for a postcode or 'lat,lon' string, filtered by voltage.

    Mirrors the ``_resolve_operators`` helper from the CLI.
    """
    if location.strip().lstrip("-").replace(".", "").isdigit() and len(location.strip()) == 5:
        # 5-digit postcode
        results = _client.search(location.strip())
        postcode_hit = next((r for r in results if r.type.upper() == "POSTCODE"), None)
        if not postcode_hit:
            return []
        detail = _client.search_by_postcode(postcode_hit.id, voltage_types=[voltage_type])
    else:
        # lat,lon coordinate string
        detail = _client.search_by_coordinates(location.strip(), voltage_types=[voltage_type])
    return detail.get("vnbs", [])


@mcp.tool()
def get_nsp_operator(location: str) -> list[dict[str, Any]]:
    """Find the low-voltage (Niederspannung) grid operator for a postcode or GPS coordinate.

    Shorthand for ``search_by_coordinates`` / ``search_by_postcode`` filtered
    to low voltage. Equivalent to the CLI command ``vnbdigital nsp``.

    Args:
        location: 5-digit postcode (e.g. ``"97816"``) **or** coordinate string
            in ``"lat,lon"`` format (e.g. ``"49.998037,9.58033"``).

    Returns:
        List of responsible low-voltage operators with ``_id``, ``name``,
        ``voltageTypes``, ``types``, ``layerUrl`` and ``bbox``.
    """
    try:
        return _resolve_operators_by_voltage(location, "Niederspannung")
    except (ConnectionError, RuntimeError) as exc:
        return [{"error": str(exc)}]


@mcp.tool()
def get_msp_operator(location: str) -> list[dict[str, Any]]:
    """Find the medium-voltage (Mittelspannung) grid operator for a postcode or GPS coordinate.

    Shorthand for ``search_by_coordinates`` / ``search_by_postcode`` filtered
    to medium voltage. Equivalent to the CLI command ``vnbdigital msp``.

    Args:
        location: 5-digit postcode (e.g. ``"97816"``) **or** coordinate string
            in ``"lat,lon"`` format (e.g. ``"49.998037,9.58033"``).

    Returns:
        List of responsible medium-voltage operators with ``_id``, ``name``,
        ``voltageTypes``, ``types``, ``layerUrl`` and ``bbox``.
    """
    try:
        return _resolve_operators_by_voltage(location, "Mittelspannung")
    except (ConnectionError, RuntimeError) as exc:
        return [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# BDEW Tools (bdew-codes.de, independent of vnbdigital)
# ---------------------------------------------------------------------------


@mcp.tool()
def bdew_lookup_by_company_code(company_uid: int) -> dict[str, Any]:
    """Look up a company in the BDEW register by its 6-7 digit CompanyUId.

    Queries bdew-codes.de and returns the company name together with all
    market functions (BDEW codes) registered for that company.

    Note: Company names in the BDEW register do not always match the names
    used on vnbdigital.de.

    Args:
        company_uid: 6-7 digit BDEW company code (``CompanyUId``),
            e.g. ``660188``.

    Returns:
        Dict with ``code``, ``name`` and ``market_functions`` (list of
        ``id``, ``bdew_code``, ``function``, ``contact``), or ``{"error": ...}``.
    """
    try:
        result = lookup_bdew_by_company_code(company_uid, timeout=_timeout)
    except Exception as exc:
        return {"error": str(exc)}

    if result is None:
        return {"error": f"CompanyUId '{company_uid}' not found."}
    return result


@mcp.tool()
def bdew_lookup_by_market_code(bdew_code: str) -> dict[str, Any]:
    """Look up a company in the BDEW register by a 13-digit market function code.

    Finds the company that holds this specific BDEW code and returns
    the matching market function entry.

    Args:
        bdew_code: 13-digit BDEW market function code,
            e.g. ``"9903445000000"``.

    Returns:
        Dict with ``code``, ``name`` and ``market_functions`` (only the
        matching entry), or ``{"error": ...}``.
    """
    try:
        result = lookup_bdew_by_market_code(bdew_code, timeout=_timeout)
    except Exception as exc:
        return {"error": str(exc)}

    if result is None:
        return {"error": f"BDEW code '{bdew_code}' not found."}
    return result


@mcp.tool()
def bdew_get_market_function_detail(bdew_id: int) -> dict[str, Any]:
    """Fetch address and contact details for a single BDEW market function entry.

    The ``bdew_id`` (internal ``id`` field) comes from the ``market_functions``
    entries returned by ``bdew_lookup_by_company_code`` or
    ``bdew_lookup_by_market_code``.

    Args:
        bdew_id: Internal BDEW ID of the market function (``id`` field from
            the market function entries).

    Returns:
        Dict with ``street``, ``zip``, ``city``, ``website``, ``phone``,
        ``fax``, ``email``, ``first_name``, ``last_name``.
    """
    try:
        return lookup_bdew_market_function_detail(bdew_id, timeout=_timeout)
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the vnbdigital MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()

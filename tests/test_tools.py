"""Unit tests for vnbdigital MCP tool functions.

All tests patch the module-level ``_client`` so no real HTTP requests are made.
"""

from unittest.mock import patch

from vnbdigital_mcp.server import (
    _operator_to_dict,
    bdew_get_market_function_detail,
    bdew_lookup_by_company_code,
    bdew_lookup_by_market_code,
    get_msp_operator,
    get_nsp_operator,
    get_operator,
    get_operator_details,
    get_operators,
    search,
    search_by_coordinates,
    search_by_postcode,
)

# ---------------------------------------------------------------------------
# _operator_to_dict
# ---------------------------------------------------------------------------


class TestOperatorToDict:
    def test_all_scalar_fields_are_mapped(self, mock_operator):
        result = _operator_to_dict(mock_operator)
        assert result["id"] == 179
        assert result["name"] == "ESTW - Erlanger Stadtwerke AG"
        assert result["postcode"] == "91058"
        assert result["city"] == "Erlangen"
        assert result["phone"] == "+49 9131 823-0"
        assert result["website"] == "https://www.estw.de"

    def test_regions_are_serialized_as_dicts(self, mock_operator):
        result = _operator_to_dict(mock_operator)
        assert result["regions"] == [{"id": 10, "name": "Erlangen"}]

    def test_services_and_documents_come_from_raw(self, mock_operator):
        result = _operator_to_dict(mock_operator)
        assert result["services"] == ["Netzanschluss"]
        assert result["documents"] == []

    def test_empty_regions(self, mock_operator):
        mock_operator.regions = []
        result = _operator_to_dict(mock_operator)
        assert result["regions"] == []

    def test_raw_missing_keys_default_to_empty_list(self, mock_operator):
        mock_operator.raw = {}
        result = _operator_to_dict(mock_operator)
        assert result["services"] == []
        assert result["documents"] == []


# ---------------------------------------------------------------------------
# get_operator
# ---------------------------------------------------------------------------


class TestGetOperator:
    def test_returns_operator_dict_on_success(self, mock_operator):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.return_value = mock_operator
            result = get_operator("179")
        assert result["id"] == 179
        assert result["name"] == "ESTW - Erlanger Stadtwerke AG"

    def test_returns_error_when_not_found(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.return_value = None
            result = get_operator("999")
        assert "error" in result
        assert "999" in result["error"]

    def test_returns_error_on_connection_error(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.side_effect = ConnectionError("timeout")
            result = get_operator("179")
        assert "error" in result
        assert "Connection error" in result["error"]

    def test_returns_error_on_runtime_error(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.side_effect = RuntimeError("500 Server Error")
            result = get_operator("179")
        assert "error" in result
        assert "API error" in result["error"]


# ---------------------------------------------------------------------------
# get_operator_details
# ---------------------------------------------------------------------------


class TestGetOperatorDetails:
    def test_returns_operator_dict_on_success(self, mock_operator):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator_details.return_value = mock_operator
            result = get_operator_details("179")
        assert result["id"] == 179

    def test_returns_error_when_not_found(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator_details.return_value = None
            result = get_operator_details("999")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_operators (batch)
# ---------------------------------------------------------------------------


class TestGetOperators:
    def test_empty_list_returns_error(self):
        result = get_operators([])
        assert "error" in result

    def test_more_than_50_ids_returns_error(self):
        result = get_operators([str(i) for i in range(51)])
        assert "error" in result

    def test_exactly_50_ids_is_allowed(self, mock_operator):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.return_value = mock_operator
            result = get_operators([str(i) for i in range(50)])
        assert "error" not in result
        assert len(result) == 50

    def test_found_and_not_found_ids_in_batch(self, mock_operator):
        def _side_effect(oid):
            return mock_operator if oid == "179" else None

        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.side_effect = _side_effect
            result = get_operators(["179", "999"])

        assert result["179"] is not None
        assert result["179"]["id"] == 179
        assert result["999"] is None

    def test_error_in_one_id_does_not_abort_batch(self, mock_operator):
        def _side_effect(oid):
            if oid == "bad":
                raise ConnectionError("network fail")
            return mock_operator

        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.get_operator.side_effect = _side_effect
            result = get_operators(["179", "bad"])

        assert result["179"]["id"] == 179
        assert "error" in result["bad"]


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_returns_list_of_hits(self, mock_postcode_hit):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_postcode_hit]
            result = search("63739")
        assert len(result) == 1
        assert result[0]["title"] == "63739 Aschaffenburg"
        assert result[0]["type"] == "POSTCODE"

    def test_empty_results(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = []
            result = search("xyz")
        assert result == []

    def test_connection_error_returns_error_list(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.side_effect = ConnectionError("no route")
            result = search("test")
        assert len(result) == 1
        assert "error" in result[0]

    def test_result_contains_expected_keys(self, mock_vnb_hit):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_vnb_hit]
            result = search("ESTW")
        assert set(result[0].keys()) == {"id", "title", "subtitle", "type", "url", "logo_url"}


# ---------------------------------------------------------------------------
# search_by_coordinates
# ---------------------------------------------------------------------------


class TestSearchByCoordinates:
    def test_delegates_to_client(self):
        expected = {"geometry": {}, "vnbs": [], "regions": []}
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search_by_coordinates.return_value = expected
            result = search_by_coordinates(49.98, 9.58)
        assert result == expected
        mock_client.search_by_coordinates.assert_called_once_with(
            coordinates="49.98,9.58",
            only_nap=False,
            voltage_types=None,
        )

    def test_error_returns_dict_with_error_key(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search_by_coordinates.side_effect = RuntimeError("500")
            result = search_by_coordinates(0.0, 0.0)
        assert "error" in result


# ---------------------------------------------------------------------------
# search_by_postcode
# ---------------------------------------------------------------------------


class TestSearchByPostcode:
    def test_success(self, mock_postcode_hit):
        detail = {"postcode": "63739", "vnbs": [], "regions": []}
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_postcode_hit]
            mock_client.search_by_postcode.return_value = detail
            result = search_by_postcode("63739")
        assert result["postcode"] == "63739"
        mock_client.search_by_postcode.assert_called_once_with(
            postcode_id=mock_postcode_hit.id,
            only_nap=False,
            voltage_types=None,
        )

    def test_postcode_not_found_in_search(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = []  # no POSTCODE hit
            result = search_by_postcode("00000")
        assert "error" in result
        assert "00000" in result["error"]

    def test_non_postcode_results_are_ignored(self, mock_vnb_hit):
        """Search results that are VNB hits (not POSTCODE) must not be used."""
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_vnb_hit]
            result = search_by_postcode("12345")
        assert "error" in result

    def test_connection_error_on_search(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.side_effect = ConnectionError("timeout")
            result = search_by_postcode("63739")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_nsp_operator / get_msp_operator
# ---------------------------------------------------------------------------


class TestGetNspMspOperator:
    def _make_vnbs_response(self, voltage_type):
        return {
            "vnbs": [
                {
                    "_id": "179",
                    "name": "ESTW",
                    "voltageTypes": [voltage_type],
                }
            ]
        }

    def test_nsp_uses_niederspannung(self, mock_postcode_hit):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_postcode_hit]
            mock_client.search_by_postcode.return_value = self._make_vnbs_response("Niederspannung")
            result = get_nsp_operator("63739")
        _, kwargs = mock_client.search_by_postcode.call_args
        assert kwargs["voltage_types"] == ["Niederspannung"]
        assert result[0]["name"] == "ESTW"

    def test_msp_uses_mittelspannung(self, mock_postcode_hit):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.return_value = [mock_postcode_hit]
            mock_client.search_by_postcode.return_value = self._make_vnbs_response("Mittelspannung")
            result = get_msp_operator("63739")
        _, kwargs = mock_client.search_by_postcode.call_args
        assert kwargs["voltage_types"] == ["Mittelspannung"]
        assert result[0]["name"] == "ESTW"

    def test_connection_error_returns_error_list(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search.side_effect = ConnectionError("fail")
            result = get_nsp_operator("63739")
        assert len(result) == 1
        assert "error" in result[0]

    def test_coordinate_string_is_passed_directly(self):
        with patch("vnbdigital_mcp.server._client") as mock_client:
            mock_client.search_by_coordinates.return_value = {"vnbs": []}
            get_nsp_operator("49.98,9.58")
        mock_client.search_by_coordinates.assert_called_once_with(
            "49.98,9.58", voltage_types=["Niederspannung"]
        )


# ---------------------------------------------------------------------------
# BDEW tools
# ---------------------------------------------------------------------------


class TestBdewTools:
    def test_lookup_by_company_code_success(self):
        expected = {"code": 660188, "name": "ESTW", "market_functions": []}
        with patch("vnbdigital_mcp.server.lookup_bdew_by_company_code") as mock_fn:
            mock_fn.return_value = expected
            result = bdew_lookup_by_company_code(660188)
        assert result == expected

    def test_lookup_by_company_code_not_found(self):
        with patch("vnbdigital_mcp.server.lookup_bdew_by_company_code") as mock_fn:
            mock_fn.return_value = None
            result = bdew_lookup_by_company_code(999999)
        assert "error" in result
        assert "999999" in result["error"]

    def test_lookup_by_company_code_exception(self):
        with patch("vnbdigital_mcp.server.lookup_bdew_by_company_code") as mock_fn:
            mock_fn.side_effect = RuntimeError("network error")
            result = bdew_lookup_by_company_code(660188)
        assert "error" in result

    def test_lookup_by_market_code_success(self):
        expected = {"code": 660188, "name": "ESTW", "market_functions": []}
        with patch("vnbdigital_mcp.server.lookup_bdew_by_market_code") as mock_fn:
            mock_fn.return_value = expected
            result = bdew_lookup_by_market_code("9903445000000")
        assert result == expected

    def test_lookup_by_market_code_not_found(self):
        with patch("vnbdigital_mcp.server.lookup_bdew_by_market_code") as mock_fn:
            mock_fn.return_value = None
            result = bdew_lookup_by_market_code("0000000000000")
        assert "error" in result

    def test_get_market_function_detail_success(self):
        expected = {"street": "Musterstr. 1", "city": "Erlangen"}
        with patch("vnbdigital_mcp.server.lookup_bdew_market_function_detail") as mock_fn:
            mock_fn.return_value = expected
            result = bdew_get_market_function_detail(42)
        assert result == expected

    def test_get_market_function_detail_exception(self):
        with patch("vnbdigital_mcp.server.lookup_bdew_market_function_detail") as mock_fn:
            mock_fn.side_effect = ValueError("not found")
            result = bdew_get_market_function_detail(0)
        assert "error" in result

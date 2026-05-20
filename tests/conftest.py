"""Shared pytest fixtures for vnbdigital-mcp tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_operator():
    """A minimal mock Operator as returned by VNBDigitalClient."""
    region = MagicMock()
    region.id = 10
    region.name = "Erlangen"

    op = MagicMock()
    op.id = 179
    op.name = "ESTW - Erlanger Stadtwerke AG"
    op.address = "Äußere Bayreuther Str. 1"
    op.postcode = "91058"
    op.city = "Erlangen"
    op.phone = "+49 9131 823-0"
    op.contact = "info@estw.de"
    op.website = "https://www.estw.de"
    op.description = "Stadtwerke Erlangen"
    op.types = ["NSP"]
    op.layer_url = "https://example.com/layer"
    op.bbox = [10.8, 49.5, 11.1, 49.7]
    op.regions = [region]
    op.image_url = None
    op.logo_url = "https://example.com/logo.png"
    op.public_required = False
    op.clicks = 42
    op.raw = {"services": ["Netzanschluss"], "documents": []}
    return op


@pytest.fixture
def mock_postcode_hit():
    """A POSTCODE-type search result mock."""
    r = MagicMock()
    r.id = "postcode-63739"
    r.title = "63739 Aschaffenburg"
    r.subtitle = "Bayern"
    r.type = "POSTCODE"
    r.url = "https://vnbdigital.de/postcode/63739"
    r.logo_url = None
    return r


@pytest.fixture
def mock_vnb_hit():
    """A VNB-type search result mock."""
    r = MagicMock()
    r.id = "179"
    r.title = "ESTW - Erlanger Stadtwerke AG"
    r.subtitle = "Erlangen"
    r.type = "VNB"
    r.url = "https://vnbdigital.de/vnb/179"
    r.logo_url = "https://example.com/logo.png"
    return r

"""Core API tests for GST dashboard transaction polling and fallback behavior."""

import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Load frontend env so tests use the same public URL users hit.
load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not configured")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def test_api_root_health(api_client, api_base_url):
    """Health check for mounted /api router."""
    response = api_client.get(f"{api_base_url}/api/", timeout=10)
    assert response.status_code == 200

    payload = response.json()
    assert payload == {"message": "Hello World"}


def test_transactions_endpoint_contract(api_client, api_base_url):
    """Transactions endpoint returns data or explicit 503 when upstream is unreachable."""
    response = api_client.get(f"{api_base_url}/api/transactions", timeout=15)
    assert response.status_code in (200, 503)

    payload = response.json()
    if response.status_code == 503:
        assert payload.get("detail") == "Transactions source unreachable"
        return

    assert isinstance(payload, list)


def test_transactions_data_shape_when_available(api_client, api_base_url):
    """Validate list row shape if upstream source is available."""
    response = api_client.get(f"{api_base_url}/api/transactions", timeout=15)
    if response.status_code == 503:
        pytest.skip("Upstream localhost:8000/transactions unreachable in current environment")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    if not payload:
        # Empty list is valid and should be handled by UI empty state.
        return

    first = payload[0]
    assert isinstance(first, dict)
    assert any(k in first for k in ["time", "timestamp", "created_at", "createdAt"])
    assert any(k in first for k in ["payer", "customer", "client_name", "name"])
    assert any(k in first for k in ["amount", "total_amount"])

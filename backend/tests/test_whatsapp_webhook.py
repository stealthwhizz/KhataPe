import os
import uuid

import pytest
import requests


# Webhook + status endpoint regression tests via public backend URL
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def base_url() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def test_api_root_is_available(api_client, base_url):
    response = api_client.get(f"{base_url}/api/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "Hello World"


def test_status_post_and_get_persistence(api_client, base_url):
    payload = {"client_name": f"TEST_whatsapp_{uuid.uuid4().hex[:8]}"}
    create_response = api_client.post(f"{base_url}/api/status", json=payload)
    assert create_response.status_code == 200

    created = create_response.json()
    assert created.get("client_name") == payload["client_name"]
    assert isinstance(created.get("id"), str)
    assert created.get("timestamp")

    list_response = api_client.get(f"{base_url}/api/status")
    assert list_response.status_code == 200
    items = list_response.json()
    assert isinstance(items, list)
    assert any(item.get("id") == created["id"] for item in items)


def test_whatsapp_text_only_parses_amount_and_gst(api_client, base_url):
    form_data = {
        "Body": "Received Rs 1234.50 from Alice on 2026-02-10 GSTIN 22AAAAA0000A1Z5",
        "NumMedia": "0",
        "From": "whatsapp:+911234567890",
    }
    response = api_client.post(f"{base_url}/api/webhook/whatsapp", data=form_data)
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "processed"
    assert data.get("source") == "message_text"

    transaction = data.get("transaction", {})
    assert transaction.get("amount") == 1234.5
    assert isinstance(transaction.get("payer"), (str, type(None)))
    assert isinstance(transaction.get("date"), (str, type(None)))
    assert isinstance(transaction.get("gstin"), (str, type(None)))

    gst = data.get("gst", {})
    assert gst.get("taxable_amount") == 1234.5
    assert gst.get("gst_rate") == 0.18
    assert gst.get("gst_amount") == 222.21
    assert gst.get("total_amount") == 1456.71


def test_whatsapp_image_fallback_graceful_when_no_amount_in_text(api_client, base_url):
    form_data = {
        "Body": "Invoice attached from Charlie",
        "NumMedia": "1",
        "MediaUrl0": "https://example.com/invoice-2.jpg",
        "MediaContentType0": "image/jpeg",
        "From": "whatsapp:+918888888888",
    }
    response = api_client.post(f"{base_url}/api/webhook/whatsapp", data=form_data)
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "processed"
    assert data.get("source") == "message_text"

    transaction = data.get("transaction", {})
    assert transaction.get("amount") is None
    assert transaction.get("raw_invoice") is None

    gst = data.get("gst", {})
    assert gst.get("taxable_amount") is None
    assert gst.get("gst_amount") is None
    assert gst.get("total_amount") is None


def test_whatsapp_image_fallback_to_text_when_unsiloed_unavailable(api_client, base_url):
    form_data = {
        "Body": "Amount INR 890 from Bob on 12/02/2026 GSTIN 29ABCDE1234F1Z5",
        "NumMedia": "1",
        "MediaUrl0": "https://example.com/invoice.jpg",
        "MediaContentType0": "image/jpeg",
        "From": "whatsapp:+919999999999",
    }
    response = api_client.post(f"{base_url}/api/webhook/whatsapp", data=form_data)
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "processed"
    assert data.get("source") == "message_text"

    transaction = data.get("transaction", {})
    assert transaction.get("amount") == 890.0
    assert transaction.get("payer") == "Bob"
    assert transaction.get("date") == "12/02/2026"
    assert transaction.get("gstin") == "29ABCDE1234F1Z5"
    assert transaction.get("raw_invoice") is None

    gst = data.get("gst", {})
    assert gst.get("taxable_amount") == 890.0
    assert gst.get("gst_amount") == 160.2
    assert gst.get("total_amount") == 1050.2

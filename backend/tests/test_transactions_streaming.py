import os
import uuid

import pytest
import requests


# Transaction streaming + polling fallback regression tests via public URL
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


def test_api_root_regression(api_client, base_url):
    response = api_client.get(f"{base_url}/api/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "Hello World"


def test_status_post_and_list_regression(api_client, base_url):
    payload = {"client_name": f"TEST_streaming_{uuid.uuid4().hex[:8]}"}
    create_response = api_client.post(f"{base_url}/api/status", json=payload)
    assert create_response.status_code == 200

    created = create_response.json()
    assert created.get("client_name") == payload["client_name"]
    assert isinstance(created.get("id"), str)

    list_response = api_client.get(f"{base_url}/api/status")
    assert list_response.status_code == 200
    items = list_response.json()
    assert any(item.get("id") == created["id"] for item in items)


def test_whatsapp_webhook_logs_transaction_and_gst(api_client, base_url):
    form_data = {
        "Body": "Received INR 1500 from TEST_Acme Corp on 2026-02-14 GSTIN 22AAAAA0000A1Z5",
        "NumMedia": "0",
        "From": "whatsapp:+910000000001",
    }
    response = api_client.post(f"{base_url}/api/webhook/whatsapp", data=form_data)
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "processed"
    assert data.get("source") == "message_text"

    tx = data.get("transaction", {})
    assert isinstance(tx.get("id"), str)
    assert tx.get("amount") == 1500.0
    assert tx.get("payer") == "TEST_Acme Corp"

    gst = data.get("gst", {})
    assert gst.get("taxable_amount") == 1500.0
    assert gst.get("gst_amount") == 270.0
    assert gst.get("total_amount") == 1770.0

    recent = api_client.get(f"{base_url}/api/transactions/recent?limit=10")
    assert recent.status_code == 200
    rows = recent.json().get("transactions", [])
    assert any(row.get("id") == tx["id"] for row in rows)


def test_razorpay_webhook_accepts_payload_and_logs_transaction(api_client, base_url):
    payload = {
        "event": "payment.captured",
        "account_id": "acc_TEST123",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 250000,
                    "email": "test-payer@example.com",
                    "created_at": 1767225600,
                }
            }
        },
    }
    response = api_client.post(f"{base_url}/api/webhook/razorpay", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "processed"
    assert data.get("event") == "payment.captured"

    tx = data.get("transaction", {})
    assert isinstance(tx.get("id"), str)
    assert tx.get("source") == "razorpay:payment.captured"
    assert tx.get("amount") == 2500.0
    assert tx.get("payer") == "test-payer@example.com"

    gst = data.get("gst", {})
    assert gst.get("gst_amount") == 450.0
    assert gst.get("total_amount") == 2950.0

    recent = api_client.get(f"{base_url}/api/transactions/recent?limit=10")
    assert recent.status_code == 200
    rows = recent.json().get("transactions", [])
    assert any(row.get("id") == tx["id"] for row in rows)


def test_transactions_recent_returns_latest_with_limit(api_client, base_url):
    response = api_client.get(f"{base_url}/api/transactions/recent?limit=3")
    assert response.status_code == 200

    data = response.json()
    rows = data.get("transactions")
    assert isinstance(rows, list)
    assert len(rows) <= 3

    for row in rows:
        assert isinstance(row.get("id"), str)
        assert "timestamp" in row

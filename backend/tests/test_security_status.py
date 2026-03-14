import json
import os
import subprocess
from pathlib import Path

import pytest
import requests


# Security scan status + dashboard data regression tests via public URL
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
REPORT_PATH = Path("/app/safedep_report.json")


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


def _read_report_backup() -> str:
    if not REPORT_PATH.exists():
        return ""
    return REPORT_PATH.read_text(encoding="utf-8")


def _write_report(payload: dict) -> None:
    REPORT_PATH.write_text(json.dumps(payload), encoding="utf-8")


def test_safedep_scan_script_runs_and_report_exists(api_client, base_url):
    before = api_client.get(f"{base_url}/api/")
    assert before.status_code == 200

    run = subprocess.run(["/bin/bash", "/app/safedep_scan.sh"], capture_output=True, text=True)
    assert run.returncode == 0

    after = api_client.get(f"{base_url}/api/")
    assert after.status_code == 200

    assert REPORT_PATH.exists(), "Expected /app/safedep_report.json to exist"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert isinstance(payload.get("packages", []), list)


def test_security_status_matches_critical_count_from_report(api_client, base_url):
    response = api_client.get(f"{base_url}/api/security/status")
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") in ["red", "green"]
    assert isinstance(data.get("critical_count"), int)
    assert isinstance(data.get("scan_available"), bool)

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    critical_count = 0
    for package in report.get("packages", []):
        for vulnerability in package.get("vulnerabilities", []):
            for severity in vulnerability.get("severities", []):
                if str(severity.get("risk", "")).upper() == "CRITICAL":
                    critical_count += 1

    assert data["critical_count"] == critical_count
    expected_status = "green" if critical_count == 0 else "red"
    assert data["status"] == expected_status
    assert data["scan_available"] is True


def test_security_status_stable_when_report_missing(api_client, base_url):
    backup = _read_report_backup()
    try:
        if REPORT_PATH.exists():
            REPORT_PATH.unlink()

        response = api_client.get(f"{base_url}/api/security/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "red"
        assert data["critical_count"] == 0
        assert data["scan_available"] is False
    finally:
        if backup:
            REPORT_PATH.write_text(backup, encoding="utf-8")


def test_security_status_turns_green_when_no_critical(api_client, base_url):
    backup = _read_report_backup()
    try:
        _write_report(
            {
                "packages": [
                    {
                        "vulnerabilities": [
                            {
                                "severities": [
                                    {"risk": "LOW"},
                                    {"risk": "HIGH"},
                                ]
                            }
                        ]
                    }
                ]
            }
        )

        response = api_client.get(f"{base_url}/api/security/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "green"
        assert data["critical_count"] == 0
        assert data["scan_available"] is True
    finally:
        if backup:
            REPORT_PATH.write_text(backup, encoding="utf-8")


def test_security_status_turns_red_when_critical_exists(api_client, base_url):
    backup = _read_report_backup()
    try:
        _write_report(
            {
                "packages": [
                    {
                        "vulnerabilities": [
                            {
                                "severities": [
                                    {"risk": "CRITICAL"},
                                    {"risk": "MEDIUM"},
                                ]
                            },
                            {
                                "severities": [
                                    {"risk": "critical"},
                                ]
                            },
                        ]
                    }
                ]
            }
        )

        response = api_client.get(f"{base_url}/api/security/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "red"
        assert data["critical_count"] == 2
        assert data["scan_available"] is True
    finally:
        if backup:
            REPORT_PATH.write_text(backup, encoding="utf-8")


def test_security_status_stable_when_report_unreadable_json(api_client, base_url):
    backup = _read_report_backup()
    try:
        REPORT_PATH.write_text("{ invalid json", encoding="utf-8")

        response = api_client.get(f"{base_url}/api/security/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "red"
        assert data["critical_count"] == 0
        assert data["scan_available"] is False
    finally:
        if backup:
            REPORT_PATH.write_text(backup, encoding="utf-8")


def test_transactions_recent_regression_still_works(api_client, base_url):
    response = api_client.get(f"{base_url}/api/transactions/recent?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("transactions"), list)

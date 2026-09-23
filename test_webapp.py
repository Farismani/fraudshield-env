"""Focused regression tests for the synthetic FraudShield Pay webapp."""

from fastapi.testclient import TestClient

from backend.app import app


def login(client: TestClient, profile: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"identifier": profile, "password": password, "device_id": f"test-{profile}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def test_authentication_and_pin_protection():
    with TestClient(app) as client:
        wrong = client.post(
            "/api/auth/login",
            json={"identifier": "faris", "password": "wrong"},
        )
        assert wrong.status_code == 401

        token = login(client, "faris", "pass001")
        invalid_pin = client.post(
            "/api/payments/send",
            json={"token": token, "receiver": "rahul", "amount": 1, "pin": "0000"},
        )
        assert invalid_pin.status_code == 403


def test_insufficient_balance_is_rejected():
    with TestClient(app) as client:
        token = login(client, "faris", "pass001")
        response = client.post(
            "/api/payments/send",
            json={"token": token, "receiver": "rahul", "amount": 10_000_000, "pin": "1234"},
        )
        assert response.status_code == 400
        assert "Insufficient" in response.json()["detail"]


def test_transfer_persists_fraud_decision_and_receipt():
    with TestClient(app) as client:
        token = login(client, "faris", "pass001")
        response = client.post(
            "/api/payments/send",
            json={
                "token": token,
                "receiver": "rahul",
                "amount": 1,
                "pin": "1234",
                "note": "phase14 test",
            },
        )
        assert response.status_code == 200, response.text
        transaction = response.json()["transaction"]
        assert transaction["status"] in {"COMPLETED", "WARNING", "BLOCKED"}
        assert isinstance(transaction["risk_score"], (int, float))

        receipt = client.get(
            f"/api/transactions/{transaction['transaction_id']}/receipt",
            params={"token": token},
        )
        assert receipt.status_code == 200
        assert receipt.json()["transaction"]["transaction_id"] == transaction["transaction_id"]


def test_admin_devices_and_risk_endpoints():
    with TestClient(app) as client:
        token = login(client, "faris", "pass001")
        assert client.get("/api/devices", params={"token": token}).status_code == 200
        assert client.get("/api/risk-trend", params={"token": token}).status_code == 200

        admin_login = client.post(
            "/api/admin/login",
            json={"username": "analyst", "password": "admin001"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["token"]
        dashboard = client.get("/api/admin/dashboard", params={"token": admin_token})
        assert dashboard.status_code == 200
        assert "metrics" in dashboard.json()

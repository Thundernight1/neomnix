import os

from fastapi.testclient import TestClient

from src.api.main import app


def test_billing_status_default_disabled(monkeypatch):
    monkeypatch.delenv("STRIPE_ENABLED", raising=False)
    client = TestClient(app)
    r = client.get("/billing/status")
    assert r.status_code == 200
    assert r.json().get("enabled") is False


def test_billing_webhook_disabled(monkeypatch):
    monkeypatch.delenv("STRIPE_ENABLED", raising=False)
    client = TestClient(app)
    r = client.post("/billing/webhook", content=b"{}", headers={"Stripe-Signature": "t=0,v1=x"})
    assert r.status_code == 404

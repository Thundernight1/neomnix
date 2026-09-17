"""Regression checks using real SQLAlchemy models and HTTP routing."""
from tests.test_gap import client, db_session, test_db_engine, auth_header, populated_db
from src.db.models import ScanJob, AuditLog
from src.services.gap_analyzer import analyze_gaps


def test_foreign_gap_org_rejected(client, auth_header):
    assert client.post("/gap/analyze", json={"org_id": "foreign"}, headers=auth_header).status_code == 403
    assert client.get("/gap/report/foreign", headers=auth_header).status_code == 403


def test_foreign_task_hidden(client, auth_header, db_session):
    db_session.add(AuditLog(tenant_id="foreign", user_email="other", action="gap_requested", resource_id="foreign-task"))
    db_session.commit()
    assert client.get("/gap/results/foreign-task", headers=auth_header).status_code == 404


def test_scan_tenant_isolation(client, auth_header, db_session):
    db_session.add_all([
        ScanJob(id="own", tenant_id="tenant-gap-test", target="127.0.0.1", status="completed", findings=[]),
        ScanJob(id="foreign", tenant_id="foreign", target="127.0.0.2", status="completed", findings=[]),
    ])
    db_session.commit()
    assert [row["id"] for row in client.get("/scans", headers=auth_header).json()] == ["own"]
    assert client.get("/scan/foreign", headers=auth_header).status_code == 404
    assert client.get("/scan/own", headers=auth_header).json()["findings_count"] == 0


def test_no_scans_is_not_full_compliance(client, auth_header):
    assert client.get("/stats", headers=auth_header).json()["compliance_score"] is None


def test_targets_fail_closed(client, auth_header, monkeypatch):
    monkeypatch.delenv("SCAN_ALLOWED_CIDRS", raising=False)
    assert client.post("/scan", json={"target": "127.0.0.1"}, headers=auth_header).status_code == 403
    assert client.post("/scan", json={"target": "-oN /tmp/file"}, headers=auth_header).status_code == 422


def test_real_gap_model_citation(db_session, populated_db):
    report = analyze_gaps(db_session, ["UCL-001"], ["hipaa"])
    assert report.total_controls == 2
    assert report.score == 50
    assert report.gaps[0].citations == {"hipaa": ["HIPAA-164.312(b)"]}


def test_role_validation(client, auth_header):
    response = client.post("/auth/register", headers=auth_header, json={
        "email": "new@example.com", "password": "StrongPassword123", "role": "superuser",
    })
    assert response.status_code == 422

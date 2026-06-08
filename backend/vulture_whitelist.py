"""
Vulture configuration for Neomnix backend.

Vulture is run with: `vulture src tests --min-confidence 80`

This file documents the known false-positive warnings that Vulture flags but
which are intentional in our codebase. To suppress a specific warning,
add `# noqa: vulture` to the line in the source file, or add the name to
the `_NEOMNIX_VULTURE_IGNORE` set below and re-run with:

    vulture src tests --min-confidence 80 --ignore-names-from-file vulture_whitelist.py

(Note: the file extension must be the default `.py` for vulture to load it as
a names list. The file is therefore syntactically valid Python.)
"""

# Set of (qualified.name, comment) pairs that are intentional false positives.
# These are FastAPI route handlers, ORM-managed columns/relationships, and
# Pydantic field conventions that vulture's static analysis cannot detect.
_NEOMNIX_VULTURE_IGNORE = {
    # FastAPI route handlers — called via HTTP, not statically.
    "src.api.main.login",
    "src.api.main.register_user",
    "src.api.main.get_me",
    "src.api.main.change_password",
    "src.api.main.get_dashboard_stats",
    "src.api.main.get_pdf_report",
    "src.api.main.ws_alerts",
    "src.api.main.health_check",
    "src.api.main.on_startup",
    "src.api.main._authenticate_ws",
    # FastAPI 'request' parameter convention.
    "src.api.main.request",
    # SQLAlchemy ORM relationship and column false positives.
    "src.db.models.Tenant.users",
    "src.db.models.Tenant.scan_jobs",
    "src.db.models.Tenant.audit_logs",
    "src.db.models.User.tenant",
    "src.db.models.ScanJob.tenant",
    "src.db.models.AuditLog.tenant",
    "src.db.models.ControlCitation.control_id",
    "src.db.models.ControlMapping.source_control_id",
    "src.db.models.ControlMapping.target_control_id",
    "src.db.models.ControlCitation.citation",
    "src.db.models.ControlMapping.source_framework",
    "src.db.models.ControlMapping.target_framework",
    # Pydantic classmethod convention (cls is the class, not an instance).
    "src.models.contracts.cls",
    "src.models.contracts.required_evidence",
    "src.models.contracts.loop_triggered",
    "src.models.contracts.check_ambiguity",
    # ComplianceGapError is raised by ComplianceAgent; needed for type matching.
    "src.agents.compliance.ComplianceGapError",
    # Pydantic TokenData / TokenResponse fields.
    "src.api.auth.TokenData",
    "src.api.auth.access_token",
    "src.api.auth.token_type",
    # Test fixtures used by some tests but not all.
    "tests.test_ws_alerts.analyst_user",
    "tests.test_ws_alerts.viewer_user",
    "tests.test_pdf_chunk4.capsys",
}

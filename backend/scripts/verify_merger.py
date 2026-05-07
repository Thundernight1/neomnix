#!/usr/bin/env python3
"""
Phase 5: End-to-end integration verification for the cross-mapping engine.

This script exercises every new and existing data path to confirm the
merged platform is ready for end-user delivery.

Usage:
    cd backend
    DATABASE_URL=sqlite:///:memory: python scripts/verify_merger.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db.models import init_db, SessionLocal, UnifiedControl, ControlCitation, ControlMapping, User, ScanJob, AuditLog
from services.crossmap_engine import (
    cosine_similarity,
    keyword_match,
    overlap_score,
    match_bucket,
    map_controls,
    compute_framework_overlap,
    get_framework_matrix,
    find_controls_for_vulnerability,
    compute_all_control_mappings,
    get_controls_by_framework,
)

# Import migration functions directly (scripts/ is not a package)
import importlib.util
_migrate_path = os.path.join(os.path.dirname(__file__), "migrate_ucl_data.py")
_spec = importlib.util.spec_from_file_location("migrate_ucl_data", _migrate_path)
_migrate_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migrate_module)
migrate_unified_controls = _migrate_module.migrate_unified_controls
migrate_control_citations = _migrate_module.migrate_control_citations


def section(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def test_core_algorithms():
    section("1. Core Algorithms")
    assert cosine_similarity("access control", "access control policy") > 0.5
    assert cosine_similarity("unrelated text", "totally different") < 0.3
    assert keyword_match("access control policy", "access control policy document") == 0.75
    assert overlap_score(0.8, 0.6, 0.0) == 66
    assert match_bucket(0.8) == "auto_match"
    assert match_bucket(0.6) == "review_required"
    assert match_bucket(0.3) == "unique"
    print("  PASS: cosine_similarity, keyword_match, overlap_score, match_bucket")


def test_database_schema():
    section("2. Database Schema")
    init_db()
    db = SessionLocal()
    try:
        uc_count = db.query(UnifiedControl).count()
        cc_count = db.query(ControlCitation).count()
        cm_count = db.query(ControlMapping).count()
        assert uc_count == 0, "Schema should start empty"
        assert cc_count == 0
        assert cm_count == 0
        print("  PASS: Schema initialized, all new tables empty")
    finally:
        db.close()


def test_ucl_migration():
    section("3. UCL Data Migration")
    db = SessionLocal()
    try:
        controls = migrate_unified_controls(db)
        assert len(controls) == 50, f"Expected 50 controls, got {len(controls)}"

        migrate_control_citations(db, controls)
        cc_count = db.query(ControlCitation).count()
        assert cc_count > 0, "Citations should exist"

        print(f"  PASS: Migrated {len(controls)} controls, {cc_count} citations")
    finally:
        db.close()


def test_framework_overlap():
    section("4. Framework Overlap Matrix")
    db = SessionLocal()
    try:
        matrix = get_framework_matrix(db)
        assert "soc2" in matrix
        assert "hipaa" in matrix
        assert matrix["soc2"]["soc2"] == 100
        assert 0 <= matrix["soc2"]["hipaa"] <= 100
        print(f"  PASS: Matrix computed — soc2↔hipaa = {matrix['soc2']['hipaa']}%")
    finally:
        db.close()


def test_control_mapping():
    section("5. Control-to-Control Mapping")
    db = SessionLocal()
    try:
        all_ids = [c.id for c in db.query(UnifiedControl).all()]
        results = map_controls(db, [all_ids[0]], [all_ids[1], all_ids[2]])
        assert len(results) == 1
        r = results[0]
        assert r.left_id == all_ids[0]
        assert r.decision in ("auto_match", "review_required", "unique")
        assert 0 <= r.overlap_score <= 100
        print(f"  PASS: {r.left_id} -> {r.right_id} | decision={r.decision} score={r.overlap_score}")
    finally:
        db.close()


def test_vulnerability_search():
    section("6. Vulnerability-to-Control Search")
    db = SessionLocal()
    try:
        results = find_controls_for_vulnerability(
            db, "unencrypted database connection without TLS", limit=5, min_score=0.1
        )
        assert len(results) > 0, "Should find at least one relevant control"
        top = results[0]
        assert "control_id" in top
        assert "semantic_similarity" in top
        print(f"  PASS: Found {len(results)} controls, top={top['control_id']} score={top['semantic_similarity']}")
    finally:
        db.close()


def test_compute_all_mappings():
    section("7. Batch Mapping Computation")
    db = SessionLocal()
    try:
        count = compute_all_control_mappings(db, force_recompute=True)
        assert count > 0, "Should create mappings"
        db_count = db.query(ControlMapping).count()
        assert db_count == count
        print(f"  PASS: Computed and stored {count} control mappings")
    finally:
        db.close()


def test_existing_models_unchanged():
    section("8. Existing Models Integrity")
    db = SessionLocal()
    try:
        # User model
        user = User(email="test@verify.local", hashed_password="fake", role="viewer")
        db.add(user)
        db.commit()
        fetched = db.query(User).filter(User.email == "test@verify.local").first()
        assert fetched is not None
        assert fetched.role == "viewer"

        # ScanJob model
        job = ScanJob(id="verify-001", target="localhost", status="pending", initiated_by="test@verify.local")
        db.add(job)
        db.commit()
        fetched_job = db.query(ScanJob).filter(ScanJob.id == "verify-001").first()
        assert fetched_job.status == "pending"

        # AuditLog model
        log = AuditLog(user_email="test@verify.local", action="verify_test")
        db.add(log)
        db.commit()
        fetched_log = db.query(AuditLog).filter(AuditLog.action == "verify_test").first()
        assert fetched_log is not None

        print("  PASS: User, ScanJob, AuditLog all work unchanged")
    finally:
        db.close()


def main():
    print("\n" + "=" * 60)
    print("  PHASE 5: END-TO-END MERGER VERIFICATION")
    print("=" * 60)

    test_core_algorithms()
    test_database_schema()
    test_ucl_migration()
    test_framework_overlap()
    test_control_mapping()
    test_vulnerability_search()
    test_compute_all_mappings()
    test_existing_models_unchanged()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
    print("\nThe merged platform is ready for end-user delivery.")
    print("Next steps:")
    print("  1. Run 'alembic upgrade head' to apply migrations")
    print("  2. Run 'python scripts/migrate_ucl_data.py' to seed UCL")
    print("  3. Run 'uvicorn src.api.main:app --reload' to boot FastAPI")
    print("  4. Visit /docs to test new /crossmap/* endpoints")


if __name__ == "__main__":
    main()

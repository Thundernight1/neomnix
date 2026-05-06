#!/usr/bin/env python3
"""
Phase 2: Migrate Unified Control Library (UCL) data into Neomnix.

Usage:
    cd backend
    python scripts/migrate_ucl_data.py

Environment:
    DATABASE_URL — defaults to sqlite:///./neomnix.db
"""
import os
import sys

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db.models import SessionLocal, UnifiedControl, ControlCitation, ControlMapping, init_db


def _load_ucl_catalog():
    """Import the UCL catalog from the source checkout."""
    source_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "New-CSX-main", "backend", "app", "services"
    )
    sys.path.insert(0, source_path)
    try:
        from ucl_catalog import get_ucl
        data = get_ucl()
        return data.get("ucl", [])
    finally:
        sys.path.pop(0)


def _extract_framework_citations(control: dict) -> list[dict]:
    """Turn per-framework citation lists into flat (framework, citation) pairs."""
    results = []
    mapping = {
        "soc2_citations": "soc2",
        "hipaa_citations": "hipaa",
        "nist_citations": "nist",
        "washington_mhmda_citations": "mhmda",
    }
    for key, framework in mapping.items():
        for citation in control.get(key, []):
            results.append({"framework": framework, "citation": citation})
    return results


def migrate_unified_controls(db) -> dict[str, UnifiedControl]:
    """Insert UnifiedControl records and return a lookup by UCL ID."""
    ucl_data = _load_ucl_catalog()
    if not ucl_data:
        raise RuntimeError("UCL catalog is empty — check source path.")

    print(f"[migrate] Loaded {len(ucl_data)} controls from UCL source")

    lookup = {}
    for ctrl in ucl_data:
        ucl_id = ctrl.get("ucl_id")
        if not ucl_id:
            continue

        uc = UnifiedControl(
            id=ucl_id,
            title=ctrl.get("title", ""),
            description=ctrl.get("description", ""),
            priority_level=ctrl.get("priority_level", "MEDIUM"),
            overlap_score=ctrl.get("overlap_score", 0),
            required_evidence=ctrl.get("required_evidence", []),
            category=_infer_category(ctrl.get("title", "")),
        )
        db.add(uc)
        lookup[ucl_id] = uc

    db.commit()
    print(f"[migrate] Inserted {len(lookup)} unified controls")
    return lookup


def _infer_category(title: str) -> str | None:
    """Infer a broad category from the control title for UI grouping."""
    title_lower = title.lower()
    keywords = {
        "Access Control": ["access", "authentication", "mfa", "rbac", "password", "session", "privileged"],
        "Audit & Monitoring": ["audit", "logging", "monitoring", "alerting"],
        "Incident Response": ["incident", "breach", "notification"],
        "Risk Management": ["risk", "vulnerability", "penetration", "patch", "change"],
        "Network Security": ["network", "firewall", "segmentation", "waf"],
        "Data Protection": ["encryption", "key management", "classification", "retention", "phi"],
        "Disaster Recovery": ["backup", "disaster", "business continuity", "availability"],
        "Human Resources": ["training", "sanctions", "background", "awareness"],
        "Privacy & Consent": ["privacy", "consent", "data subject", "de-identification"],
        "Development Security": ["sdlc", "code review", "dependency", "supply chain"],
        "Vendor Management": ["vendor", "third-party", "business associate"],
        "Physical Security": ["physical", "workstation", "device", "media"],
    }
    for category, terms in keywords.items():
        if any(term in title_lower for term in terms):
            return category
    return "General"


def migrate_control_citations(db, controls: dict[str, UnifiedControl]) -> int:
    """Insert ControlCitation records for every framework citation."""
    ucl_data = _load_ucl_catalog()
    total = 0
    for ctrl in ucl_data:
        ucl_id = ctrl.get("ucl_id")
        if ucl_id not in controls:
            continue
        for citation in _extract_framework_citations(ctrl):
            cc = ControlCitation(
                control_id=ucl_id,
                framework=citation["framework"],
                citation=citation["citation"],
            )
            db.add(cc)
            total += 1

    db.commit()
    print(f"[migrate] Inserted {total} control citations")
    return total


def verify_migration(db) -> dict:
    """Return counts for sanity-checking."""
    uc_count = db.query(UnifiedControl).count()
    cc_count = db.query(ControlCitation).count()
    cm_count = db.query(ControlMapping).count()

    # Spot-check: count controls per framework
    framework_counts = {}
    for fw in ["soc2", "hipaa", "nist", "mhmda"]:
        framework_counts[fw] = (
            db.query(ControlCitation)
            .filter(ControlCitation.framework == fw)
            .count()
        )

    return {
        "unified_controls": uc_count,
        "control_citations": cc_count,
        "control_mappings": cm_count,
        "frameworks": framework_counts,
    }


def main():
    print("=" * 60)
    print("Phase 2: UCL Data Migration")
    print("=" * 60)

    # Ensure tables exist (safe to call multiple times)
    init_db()

    db = SessionLocal()
    try:
        # Clear existing data for idempotency
        db.query(ControlMapping).delete()
        db.query(ControlCitation).delete()
        db.query(UnifiedControl).delete()
        db.commit()
        print("[migrate] Cleared existing cross-mapping data")

        # Migrate
        controls = migrate_unified_controls(db)
        migrate_control_citations(db, controls)

        # Verify
        stats = verify_migration(db)
        print("\n[migrate] Verification results:")
        print(f"  Unified controls : {stats['unified_controls']}")
        print(f"  Citations total  : {stats['control_citations']}")
        print(f"  Pre-computed maps: {stats['control_mappings']}")
        print("  Per-framework citations:")
        for fw, count in stats["frameworks"].items():
            print(f"    {fw:12s}: {count}")

        if stats["unified_controls"] == 50:
            print("\n[migrate] SUCCESS: All 50 UCL controls migrated")
        else:
            print(f"\n[migrate] WARNING: Expected 50 controls, got {stats['unified_controls']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

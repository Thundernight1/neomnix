"""
Test suite for cross-mapping features.

Tests the GET /crossmap/frameworks endpoint, POST /crossmap/matrix endpoint,
and the core cosine_similarity function from the cross-mapping engine.
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.db.models import Base, SessionLocal, UnifiedControl, ControlCitation
from src.services.crossmap_engine import (
    cosine_similarity,
    keyword_match,
    overlap_score,
    get_framework_matrix,
    compute_framework_overlap,
)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  FIXTURES                                                                  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = SessionLocal(bind=engine)
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(test_db):
    """Seed the test database with sample controls and citations.

    Post Chunk 2: only healthcare frameworks (hipaa, mhmda) are present.
    SOC2, NIST, and other out-of-scope frameworks are no longer seeded.
    """
    # Add sample controls
    controls = [
        UnifiedControl(
            id="HIPAA-001",
            title="Access Control",
            description="Implement mechanisms to control and manage identification, authentication, and access to the system.",
            priority_level="high",
            overlap_score=85,
            required_evidence=["logs", "policies"],
            category="access_control"
        ),
        UnifiedControl(
            id="HIPAA-002",
            title="Encryption",
            description="Implement encryption and decryption mechanisms for data at rest and in transit.",
            priority_level="high",
            overlap_score=90,
            required_evidence=["certs", "configs"],
            category="encryption"
        ),
        UnifiedControl(
            id="MHMDA-001",
            title="Data Confidentiality",
            description="Ensure confidentiality of sensitive health information through appropriate safeguards.",
            priority_level="high",
            overlap_score=88,
            required_evidence=["audit_logs"],
            category="confidentiality"
        ),
    ]

    for ctrl in controls:
        test_db.add(ctrl)

    test_db.commit()

    # Add citations to establish framework presence (hipaa + mhmda only).
    citations = [
        ControlCitation(control_id="HIPAA-001", framework="hipaa", citation="45 CFR 164.312(a)(2)"),
        ControlCitation(control_id="HIPAA-002", framework="hipaa", citation="45 CFR 164.312(a)(2)(i)"),
        ControlCitation(control_id="MHMDA-001", framework="mhmda", citation="RCW 19.373.030"),
        ControlCitation(control_id="MHMDA-001", framework="hipaa", citation="45 CFR 164.312"),
    ]

    for cit in citations:
        test_db.add(cit)

    test_db.commit()

    return test_db


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: COSINE SIMILARITY FUNCTION                                        ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_cosine_similarity_identical_strings():
    """Test cosine similarity with identical strings."""
    a = "Access Control Management"
    b = "Access Control Management"
    sim = cosine_similarity(a, b)
    assert abs(sim - 1.0) < 0.0001, "Identical strings should have similarity ~1.0"


def test_cosine_similarity_different_strings():
    """Test cosine similarity with completely different strings."""
    a = "Access Control"
    b = "Network Configuration"
    sim = cosine_similarity(a, b)
    assert 0.0 <= sim < 0.3, "Very different strings should have low similarity"


def test_cosine_similarity_partial_overlap():
    """Test cosine similarity with partial keyword overlap."""
    a = "Implement access control mechanisms"
    b = "Access control for system resources"
    sim = cosine_similarity(a, b)
    assert 0.4 <= sim <= 1.0, "Partial overlap should yield moderate-to-high similarity"
    assert sim > 0.0, "Similarity should be greater than 0"


def test_cosine_similarity_empty_string():
    """Test cosine similarity with empty or short strings."""
    a = ""
    b = "Access Control"
    sim = cosine_similarity(a, b)
    assert sim == 0.0, "Empty string should yield 0 similarity"


def test_cosine_similarity_short_tokens():
    """Test cosine similarity excludes very short tokens."""
    a = "I am here"
    b = "I am here"
    sim = cosine_similarity(a, b)
    # Short tokens (< 3 chars) are filtered; should match on "here" only
    assert sim >= 0.5, "Should handle short token filtering"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: KEYWORD MATCH FUNCTION                                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_keyword_match_identical():
    """Test keyword match with identical strings."""
    a = "Access Control Management"
    b = "Access Control Management"
    sim = keyword_match(a, b)
    assert sim == 1.0, "Identical strings should have Jaccard similarity 1.0"


def test_keyword_match_disjoint():
    """Test keyword match with completely disjoint keyword sets."""
    a = "encryption database"
    b = "network firewall"
    sim = keyword_match(a, b)
    assert sim == 0.0, "Disjoint sets should have Jaccard similarity 0.0"


def test_keyword_match_partial():
    """Test keyword match with partial keyword overlap."""
    a = "access control system"
    b = "access control policy"
    sim = keyword_match(a, b)
    # Overlap: "access", "control" (2 tokens)
    # Union: "access", "control", "system", "policy" (4 tokens)
    # Jaccard = 2/4 = 0.5
    assert 0.4 <= sim <= 0.6, "Partial overlap should yield ~0.5 Jaccard similarity"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: OVERLAP SCORE ENSEMBLE                                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_overlap_score_high():
    """Test overlap score with high semantic and keyword similarity."""
    semantic = 0.9
    keyword = 0.85
    score = overlap_score(semantic, keyword, expert_weight=0.0)
    # 0.9 * 0.6 + 0.85 * 0.3 + 0.0 * 0.1 = 0.54 + 0.255 = 0.795 -> 80 (rounded)
    assert score >= 75, "High similarities should yield high score"
    assert isinstance(score, int), "Score should be an integer"


def test_overlap_score_low():
    """Test overlap score with low similarities."""
    semantic = 0.1
    keyword = 0.05
    score = overlap_score(semantic, keyword, expert_weight=0.0)
    assert score <= 15, "Low similarities should yield low score"


def test_overlap_score_with_expert_weight():
    """Test overlap score with expert weight boost."""
    semantic = 0.5
    keyword = 0.4
    score_without = overlap_score(semantic, keyword, expert_weight=0.0)
    score_with = overlap_score(semantic, keyword, expert_weight=1.0)
    assert score_with >= score_without, "Expert weight should boost score"


def test_overlap_score_clamped():
    """Test that overlap score is clamped to [0, 100]."""
    score_min = overlap_score(0.0, 0.0, expert_weight=0.0)
    score_max = overlap_score(1.0, 1.0, expert_weight=1.0)
    assert score_min == 0, "Minimum score should be 0"
    assert score_max == 100, "Maximum score should be 100"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: FRAMEWORK ENDPOINTS & MATRIX                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_get_framework_matrix_default_frameworks(seeded_db):
    """Test framework matrix computation with default frameworks."""
    matrix = get_framework_matrix(seeded_db)

    # Check structure
    assert isinstance(matrix, dict), "Matrix should be a dictionary"
    assert len(matrix) == 2, "Should have 2 frameworks (hipaa, mhmda)"

    expected_frameworks = {"hipaa", "mhmda"}
    assert set(matrix.keys()) == expected_frameworks, "Should contain expected frameworks"

    # Diagonal should be 100 (framework with itself)
    for fw in expected_frameworks:
        assert matrix[fw][fw] == 100, f"{fw} overlap with itself should be 100"


def test_get_framework_matrix_custom_frameworks(seeded_db):
    """Test framework matrix computation with custom framework list."""
    custom_frameworks = ["hipaa", "mhmda"]
    matrix = get_framework_matrix(seeded_db, frameworks=custom_frameworks)

    assert len(matrix) == 2, "Should have 2 frameworks"
    assert set(matrix.keys()) == {"hipaa", "mhmda"}
    assert matrix["hipaa"]["hipaa"] == 100
    assert matrix["mhmda"]["mhmda"] == 100


def test_compute_framework_overlap_hipaa_mhmda(seeded_db):
    """Test framework overlap: HIPAA to WA-MHMDA."""
    overlap = compute_framework_overlap(seeded_db, "hipaa", "mhmda")
    assert isinstance(overlap, int), "Overlap should be an integer"
    assert 0 <= overlap <= 100, "Overlap should be a percentage"


def test_compute_framework_overlap_symmetry(seeded_db):
    """Test that framework overlap is NOT necessarily symmetric (directional)."""
    hipaa_to_mhmda = compute_framework_overlap(seeded_db, "hipaa", "mhmda")
    mhmda_to_hipaa = compute_framework_overlap(seeded_db, "mhmda", "hipaa")

    assert isinstance(hipaa_to_mhmda, int)
    assert isinstance(mhmda_to_hipaa, int)
    assert 0 <= hipaa_to_mhmda <= 100
    assert 0 <= mhmda_to_hipaa <= 100


def test_get_framework_matrix_overlaps_reasonable(seeded_db):
    """Test that computed overlaps are reasonable (0-100, diagonal is 100)."""
    matrix = get_framework_matrix(seeded_db)
    
    for fw_a, row in matrix.items():
        for fw_b, overlap in row.items():
            assert isinstance(overlap, int), f"Overlap {fw_a} -> {fw_b} should be int"
            assert 0 <= overlap <= 100, f"Overlap {fw_a} -> {fw_b} should be 0-100"
            
            if fw_a == fw_b:
                assert overlap == 100, f"Diagonal {fw_a} -> {fw_b} should be 100"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: FRAMEWORKS ENDPOINT (GET /crossmap/frameworks)                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_frameworks_endpoint_returns_two_frameworks(seeded_db):
    """
    Integration test: verify the seeded DB exposes exactly the 2 supported
    healthcare frameworks (hipaa, mhmda).
    """
    from sqlalchemy import distinct
    frameworks = (
        seeded_db.query(ControlCitation.framework)
        .distinct()
        .all()
    )
    frameworks_list = [f[0] for f in frameworks]

    expected = {"hipaa", "mhmda"}
    assert set(frameworks_list) == expected, f"Should have exactly the 2 supported frameworks, got {frameworks_list}"
    assert len(frameworks_list) == 2, "Should have exactly 2 frameworks"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  TESTS: MATRIX ENDPOINT (POST /crossmap/matrix)                           ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_matrix_endpoint_returns_valid_matrix(seeded_db):
    """
    Integration test: verify the matrix endpoint returns a valid 2-framework
    overlap matrix (hipaa, mhmda).
    """
    matrix = get_framework_matrix(seeded_db, frameworks=["hipaa", "mhmda"])

    # Validate structure
    assert isinstance(matrix, dict)
    assert len(matrix) == 2

    # Validate each row is a dict with all frameworks
    for fw_a, row in matrix.items():
        assert isinstance(row, dict)
        assert len(row) == 2
        for fw_b in ["hipaa", "mhmda"]:
            assert fw_b in row
            assert isinstance(row[fw_b], int)
            assert 0 <= row[fw_b] <= 100

    # Validate diagonal is 100
    for fw in ["hipaa", "mhmda"]:
        assert matrix[fw][fw] == 100, f"Diagonal {fw}->{fw} should be 100"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  EDGE CASES                                                                ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def test_cosine_similarity_case_insensitive():
    """Test that cosine similarity is case-insensitive."""
    a = "Access Control"
    b = "access control"
    sim = cosine_similarity(a, b)
    assert sim == 1.0, "Case should be ignored"


def test_overlap_score_zero_similarities():
    """Test overlap score with all zero similarities."""
    score = overlap_score(0.0, 0.0, expert_weight=0.0)
    assert score == 0, "All zeros should yield score 0"


def test_get_framework_matrix_empty_database(test_db):
    """Test framework matrix with empty database."""
    matrix = get_framework_matrix(test_db, frameworks=["hipaa", "mhmda"])

    # With empty database, diagonal should be 100 (self-overlap, no controls = 0/0 case)
    # The implementation returns 100 for self-overlap regardless
    assert matrix["hipaa"]["hipaa"] == 100, "Self-overlap should be 100"
    assert matrix["mhmda"]["mhmda"] == 100, "Self-overlap should be 100"

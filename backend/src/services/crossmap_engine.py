"""
Cross-mapping engine — integrated with SQLAlchemy.

Scope (post Chunk 2 — healthcare-only refactor):
  - Supports only HIPAA-2026 and WA-MHMDA (RCW 19.373.030).

Core algorithms (cosine similarity, keyword matching, overlap scoring) are
implemented with TF-IDF vectorization and Jaccard set similarity.

Features:
  - SQLAlchemy I/O replacing in-memory JSON lists
  - Healthcare-only framework overlap matrix computation via SQL
  - Vulnerability-to-control semantic search
  - Batch control mapping with database persistence
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import UnifiedControl, ControlCitation


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CORE ALGORITHMS                                                           ║
# ╚════════════════════════════════════════════════════════════════════════════╝


def _tokens(a: str) -> List[str]:
    """Simple tokenizer: lower-case, split on non-word chars, drop empties."""
    return [t for t in re.split(r"\W+", a.lower()) if t and len(t) > 2]


def _tf(tokens: List[str]) -> Dict[str, float]:
    """Term frequency with log scaling."""
    counts = Counter(tokens)
    total = sum(counts.values())
    if total == 0:
        return {}
    return {token: math.log1p(count) for token, count in counts.items()}


def cosine_similarity(a: str, b: str) -> float:
    """
    Compute cosine similarity between two text strings.
    """
    tokens_a = _tokens(a)
    tokens_b = _tokens(b)
    if not tokens_a or not tokens_b:
        return 0.0

    tf_a = _tf(tokens_a)
    tf_b = _tf(tokens_b)

    # Document frequency: 2 documents, so a token's idf is always log(2/df).
    # For 2 docs the idf is non-zero only for terms present in exactly one.
    # We approximate the per-token presence in each document.
    common = set(tf_a) & set(tf_b)
    if not common:
        return 0.0

    num = sum(tf_a[t] * tf_b[t] for t in common)
    den_a = math.sqrt(sum(v * v for v in tf_a.values()))
    den_b = math.sqrt(sum(v * v for v in tf_b.values()))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def keyword_match(a: str, b: str) -> float:
    """Jaccard keyword overlap between two strings, restricted to tokens with len>2."""
    set_a = set(_tokens(a))
    set_b = set(_tokens(b))
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def overlap_score(semantic_sim: float, keyword: float, expert_weight: float = 0.0) -> int:
    """Combine semantic similarity and keyword match into a 0-100 score."""
    combined = (semantic_sim * 0.6) + (keyword * 0.3) + (expert_weight * 0.1)
    return int(round(max(0.0, min(1.0, combined)) * 100))


def match_bucket(sim: float) -> str:
    """Map a similarity score to a decision bucket."""
    if sim >= 0.75:
        return "auto_match"
    if sim >= 0.50:
        return "review_required"
    return "unique"


def compute_framework_overlap(db: Session, framework_a: str, framework_b: str) -> int:
    """
    Compute the percentage of framework-A controls that also have a citation
    in framework B (based on the UCL data).

    Pure-SQL framework overlap computation.
    """
    # Count controls that have at least one citation in framework A
    a_count = (
        db.query(ControlCitation.control_id)
        .filter(ControlCitation.framework == framework_a)
        .distinct()
        .count()
    )
    if a_count == 0:
        return 0

    # Count controls that have citations in BOTH frameworks
    both = (
        db.query(ControlCitation.control_id)
        .filter(ControlCitation.framework == framework_a)
        .filter(
            ControlCitation.control_id.in_(
                db.query(ControlCitation.control_id)
                .filter(ControlCitation.framework == framework_b)
                .distinct()
            )
        )
        .distinct()
        .count()
    )

    return int(round((both / a_count) * 100))


def get_framework_matrix(db: Session, frameworks: Optional[List[str]] = None) -> Dict[str, Dict[str, int]]:
    """
    Return the N×N overlap matrix for the healthcare frameworks.

    Defaults to HIPAA-2026 and WA-MHMDA only.
    """
    if frameworks is None:
        frameworks = ["hipaa", "mhmda"]

    matrix: Dict[str, Dict[str, int]] = {}
    for a in frameworks:
        row: Dict[str, int] = {}
        for b in frameworks:
            row[b] = 100 if a == b else compute_framework_overlap(db, a, b)
        matrix[a] = row

    return matrix

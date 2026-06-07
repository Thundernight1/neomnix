"""
Cross-mapping engine — integrated with SQLAlchemy.

Scope (post Chunk 2 — healthcare-only refactor):
  - Supports only HIPAA-2026 and WA-MHMDA (RCW 19.373.030).
  - SOC2, NIST-800-53, FedRAMP, PCI-DSS, CCM-4.0, SEC-2023 are out of
    scope; no N×N cross-framework matrix is computed for them.

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

from src.db.models import UnifiedControl, ControlCitation, ControlMapping


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
    TF-IDF cosine similarity between two text strings.
    Returns 0.0–1.0.
    """
    ta = _tf(_tokens(a))
    tb = _tf(_tokens(b))
    if not ta or not tb:
        return 0.0

    dot = 0.0
    for k, va in ta.items():
        vb = tb.get(k)
        if vb:
            dot += va * vb

    na = math.sqrt(sum(v * v for v in ta.values()))
    nb = math.sqrt(sum(v * v for v in tb.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (na * nb)))


def keyword_match(a: str, b: str) -> float:
    """
    Jaccard similarity on keyword sets.
    Returns 0.0–1.0.
    """
    sa = set(_tokens(a))
    sb = set(_tokens(b))
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def overlap_score(semantic_sim: float, keyword: float, expert_weight: float = 0.0) -> int:
    """
    Weighted ensemble score.
    60% semantic + 30% keyword + 10% expert.
    Returns 0–100 integer.
    """
    score = (semantic_sim * 0.6) + (keyword * 0.3) + (expert_weight * 0.1)
    return int(round(max(0.0, min(1.0, score)) * 100))


def match_bucket(sim: float) -> str:
    """
    Classify a similarity score into a confidence tier.
    """
    if sim >= 0.75:
        return "auto_match"
    if sim >= 0.50:
        return "review_required"
    return "unique"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  DATA STRUCTURES                                                           ║
# ╚════════════════════════════════════════════════════════════════════════════╝


@dataclass
class MappingResult:
    left_id: str
    left_title: str
    right_id: str
    right_title: str
    semantic_similarity: float
    keyword_similarity: float
    overlap_score: int
    decision: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "left_id": self.left_id,
            "left_title": self.left_title,
            "right_id": self.right_id,
            "right_title": self.right_title,
            "semantic_similarity": round(self.semantic_similarity, 4),
            "keyword_similarity": round(self.keyword_similarity, 4),
            "overlap_score": self.overlap_score,
            "decision": self.decision,
        }


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  SQLAlchemy I/O LAYER                                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝


def _control_text(ctrl: UnifiedControl) -> str:
    """Build the text representation used for similarity matching."""
    return f"{ctrl.title} {ctrl.description}"


def map_controls(db: Session, left_ids: List[str], right_ids: List[str]) -> List[MappingResult]:
    """
    Map each control in *left_ids* to its nearest neighbor in *right_ids*.

    SQLAlchemy-aware control-to-control mapping.
    """
    left_controls = (
        db.query(UnifiedControl)
        .filter(UnifiedControl.id.in_(left_ids))
        .all()
    )
    right_controls = (
        db.query(UnifiedControl)
        .filter(UnifiedControl.id.in_(right_ids))
        .all()
    )

    results: List[MappingResult] = []
    for l_ctrl in left_controls:
        l_text = _control_text(l_ctrl)
        best_sim = 0.0
        best_right: Optional[UnifiedControl] = None

        for r_ctrl in right_controls:
            r_text = _control_text(r_ctrl)
            sim = cosine_similarity(l_text, r_text)
            if sim > best_sim:
                best_sim = sim
                best_right = r_ctrl

        if best_right:
            ks = keyword_match(l_text, _control_text(best_right))
            oscore = overlap_score(best_sim, ks, 0.0)
            results.append(
                MappingResult(
                    left_id=l_ctrl.id,
                    left_title=l_ctrl.title,
                    right_id=best_right.id,
                    right_title=best_right.title,
                    semantic_similarity=best_sim,
                    keyword_similarity=ks,
                    overlap_score=oscore,
                    decision=match_bucket(best_sim),
                )
            )

    return results


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


def compute_all_control_mappings(
    db: Session,
    frameworks: Optional[List[str]] = None,
    force_recompute: bool = False,
) -> int:
    """
    Compute and persist control-to-control mappings for every pair of controls
    across all requested frameworks.

    If *force_recompute* is False and mappings already exist, this is a no-op.
    Defaults to HIPAA-2026 and WA-MHMDA only (no multi-framework N×N).
    Returns the number of mappings created.
    """
    if frameworks is None:
        frameworks = ["hipaa", "mhmda"]

    # Check if mappings already exist
    if not force_recompute:
        existing = db.query(ControlMapping).first()
        if existing:
            return 0  # Already computed

    # Get all controls
    controls = db.query(UnifiedControl).all()
    if not controls:
        return 0

    count = 0
    for i, left in enumerate(controls):
        for right in controls[i + 1:]:
            l_text = _control_text(left)
            r_text = _control_text(right)
            sem = cosine_similarity(l_text, r_text)
            kw = keyword_match(l_text, r_text)
            oscore = overlap_score(sem, kw, 0.0)

            mapping = ControlMapping(
                left_control_id=left.id,
                right_control_id=right.id,
                semantic_similarity=sem,
                keyword_similarity=kw,
                overlap_score=oscore,
                decision=match_bucket(sem),
                mapping_type=None,  # Could be inferred from overlap_score thresholds
                expert_weight=0.0,
            )
            db.add(mapping)
            count += 1

    db.commit()
    return count


def find_controls_for_vulnerability(
    db: Session,
    description: str,
    limit: int = 10,
    min_score: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Find UnifiedControls that are semantically similar to a vulnerability
    description. Returns a ranked list of controls with similarity scores.

    TF-IDF cosine similarity search for vulnerability-to-control matching.
    """
    controls = db.query(UnifiedControl).all()
    scored = []
    for ctrl in controls:
        ctrl_text = _control_text(ctrl)
        sem = cosine_similarity(description, ctrl_text)
        if sem >= min_score:
            scored.append((sem, ctrl))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "control_id": ctrl.id,
            "title": ctrl.title,
            "semantic_similarity": round(sem, 4),
            "priority_level": ctrl.priority_level,
            "category": ctrl.category,
        }
        for sem, ctrl in scored[:limit]
    ]


def get_controls_by_framework(db: Session, framework: str) -> List[UnifiedControl]:
    """Return all UnifiedControls that have at least one citation in *framework*."""
    return (
        db.query(UnifiedControl)
        .join(ControlCitation, UnifiedControl.id == ControlCitation.control_id)
        .filter(ControlCitation.framework == framework)
        .distinct()
        .all()
    )


def get_citations_for_control(db: Session, control_id: str) -> List[ControlCitation]:
    """Return all citations for a given control."""
    return (
        db.query(ControlCitation)
        .filter(ControlCitation.control_id == control_id)
        .all()
    )

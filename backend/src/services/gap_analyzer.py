"""
Gap Analyzer — mevcut UnifiedControl + ControlCitation modellerini kullanır.
AWS yok. Sadece local PostgreSQL.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.db.models import UnifiedControl, ControlCitation


@dataclass
class GapItem:
    ucl_id: str
    title: str
    description: str
    priority_level: str
    affected_frameworks: List[str]
    citations: Dict[str, List[str]]
    recommendation: Optional[dict] = None

    def to_dict(self):
        return {
            "ucl_id": self.ucl_id,
            "title": self.title,
            "description": self.description,
            "priority_level": self.priority_level,
            "affected_frameworks": self.affected_frameworks,
            "citations": self.citations,
            "recommendation": self.recommendation,
        }


@dataclass
class GapReport:
    total_controls: int
    passing_controls: int
    failing_controls: int
    score: int
    gaps: List[GapItem] = field(default_factory=list)
    gaps_by_priority: Dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        return {
            "total_controls": self.total_controls,
            "passing_controls": self.passing_controls,
            "failing_controls": self.failing_controls,
            "score": self.score,
            "gaps_by_priority": self.gaps_by_priority,
            "gaps": [g.to_dict() for g in self.gaps],
        }


SUPPORTED_FRAMEWORKS = ["soc2", "hipaa", "nist", "mhmda"]


def analyze_gaps(db: Session, completed_ucl_ids: List[str], target_frameworks=None) -> GapReport:
    if target_frameworks is None:
        target_frameworks = SUPPORTED_FRAMEWORKS

    all_controls = db.query(UnifiedControl).all()
    total = len(all_controls)
    if total == 0:
        return GapReport(total_controls=0, passing_controls=0, failing_controls=0, score=0)

    completed_set = set(completed_ucl_ids)
    gaps = []

    for ctrl in all_controls:
        if ctrl.id in completed_set:
            continue

        citations_qs = (
            db.query(ControlCitation)
            .filter(ControlCitation.control_id == ctrl.id)
            .filter(ControlCitation.framework.in_(target_frameworks))
            .all()
        )
        if not citations_qs:
            continue

        affected = list({c.framework for c in citations_qs})
        citations_map = {}
        for c in citations_qs:
            citations_map.setdefault(c.framework, []).append(c.citation_id)

        gaps.append(GapItem(
            ucl_id=ctrl.id,
            title=ctrl.title,
            description=ctrl.description or "",
            priority_level=ctrl.priority_level or "MEDIUM",
            affected_frameworks=sorted(affected),
            citations=citations_map,
        ))

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    gaps.sort(key=lambda g: priority_order.get(g.priority_level, 1))

    passing = total - len(gaps)
    score = int(round((passing / total) * 100)) if total else 0

    by_priority = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for g in gaps:
        by_priority[g.priority_level] = by_priority.get(g.priority_level, 0) + 1

    return GapReport(
        total_controls=total,
        passing_controls=passing,
        failing_controls=len(gaps),
        score=score,
        gaps=gaps,
        gaps_by_priority=by_priority,
    )

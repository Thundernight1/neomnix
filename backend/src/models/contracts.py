from datetime import datetime
from typing import Literal, List, Optional, TypedDict, Union, Any, Dict
from pydantic import BaseModel, Field, field_validator

class VulnerabilityArtifact(BaseModel):
    """Immutable contract for a raw security finding."""
    severity: Literal['low', 'medium', 'high', 'critical']
    description: str = Field(min_length=5, strict=True)
    evidence: str = Field(min_length=5, strict=True)
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('description', 'evidence')
    @classmethod
    def check_ambiguity(cls, v: str) -> str:
        ambiguous_terms = {'unknown', 'n/a', 'tbd', ''}
        if v.lower().strip() in ambiguous_terms:
            raise ValueError(f"Ambiguous data rejected: '{v}' violates zero-trust contracts.")
        return v

class ComplianceVerdict(BaseModel):
    """Final compliance assessment contract."""
    determination: Literal['compliant', 'non_compliant', 'partial_compliance', 'gap']
    confidence_score: float = Field(ge=0.0, le=1.0)
    mapped_controls: List[str]
    unmapped_findings: List[str] = Field(default_factory=list)
    reasoning: str

class ScanContext(BaseModel):
    """Metadata container for the scan session."""
    intensity: int = Field(ge=1, le=10)
    attempt_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    target: str
    job_id: str = Field(default="")

class NeomnixState(TypedDict):
    """State definition for the LangGraph workflow."""
    artifacts: List[VulnerabilityArtifact]
    context: ScanContext
    verdict: Union[ComplianceVerdict, None]
    confidence: float
    loop_triggered: bool

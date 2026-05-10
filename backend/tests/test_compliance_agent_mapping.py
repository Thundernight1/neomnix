import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.compliance import ComplianceAgent
from src.models.contracts import ComplianceVerdict, VulnerabilityArtifact


def test_extract_frameworks_includes_wa_when_mixed_controls():
    agent = ComplianceAgent()
    verdict = ComplianceVerdict(
        determination="non_compliant",
        confidence_score=0.9,
        mapped_controls=[
            "SOC2-CC6.1",
            "WA-MHMDA-RCW-19.373.010",
        ],
        unmapped_findings=[],
        reasoning="test",
    )

    frameworks = agent._extract_frameworks(verdict)
    assert "SOC2" in frameworks
    assert "WA-MHMDA" in frameworks


def test_mapping_is_case_insensitive_for_known_trigger():
    agent = ComplianceAgent()
    agent._generate_framework_reports = lambda *args, **kwargs: None
    agent._generate_pdf_reports = lambda *args, **kwargs: None

    artifacts = [
        VulnerabilityArtifact(
            severity="critical",
            description="open port 23/tcp (telnet)",
            evidence="23/tcp open telnet",
        )
    ]

    verdict = agent.evaluate(artifacts, confidence=0.95, job_id="job-test")
    assert verdict.determination == "non_compliant"
    assert verdict.unmapped_findings == []
    assert any(c.startswith("WA-MHMDA") for c in verdict.mapped_controls)

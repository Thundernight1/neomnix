import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.contracts import VulnerabilityArtifact, ComplianceVerdict
from src.worker.tasks import serialize_artifacts, serialize_verdict


def test_serialize_artifacts_produces_json_serializable_dicts():
    artifacts = [
        VulnerabilityArtifact(
            severity="critical",
            description="Open Port 23/tcp (telnet)",
            evidence="evidence",
        )
    ]
    payload = serialize_artifacts(artifacts)
    json.dumps(payload)


def test_serialize_verdict_produces_json_serializable_dict():
    verdict = ComplianceVerdict(
        determination="non_compliant",
        confidence_score=0.9,
        mapped_controls=["WA-MHMDA-RCW-19.373.030"],
        unmapped_findings=[],
        reasoning="test",
    )
    payload = serialize_verdict(verdict)
    json.dumps(payload)

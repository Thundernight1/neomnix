import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.models.contracts import (
    VulnerabilityArtifact, 
    ComplianceVerdict, 
    ScanContext
)
from src.agents.compliance import ComplianceGapError
from src.agents.scanner import ScannerAgent
from src.orchestrator import CyberSurXOrchestrator, RalphState
from pydantic import ValidationError

# --- Phase 1: Data Contract Tests ---

@pytest.mark.unit
def test_vulnerability_artifact_valid():
    """Test that a valid artifact is created successfully."""
    artifact = VulnerabilityArtifact(
        severity='high',
        description='Open Port 22',
        evidence='SSH banner found'
    )
    assert artifact.severity == 'high'
    assert artifact.description == 'Open Port 22'

@pytest.mark.unit
def test_vulnerability_artifact_ambiguity_check():
    """Test that ambiguous descriptions raise ValidationError."""
    # Terms that pass length check (>=5) but fail ambiguity check
    ambiguous_terms_long = ['unknown']
    
    for term in ambiguous_terms_long:
        with pytest.raises(ValidationError) as excinfo:
            VulnerabilityArtifact(
                severity='low',
                description=term,
                evidence='some evidence'
            )
        assert "Ambiguous data rejected" in str(excinfo.value)

    # Terms that fail length check (<5)
    short_terms = ['n/a', 'tbd', '']
    for term in short_terms:
        with pytest.raises(ValidationError) as excinfo:
            VulnerabilityArtifact(
                severity='low',
                description=term,
                evidence='some evidence'
            )
        # Just ensure it raises ValidationError, likely for length or ambiguity
        assert "String should have at least 5 characters" in str(excinfo.value) or "Ambiguous data rejected" in str(excinfo.value)

# --- Phase 2: Scanner Agent Tests (Mocked) ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_scanner_agent_execution_nmap():
    """Test execution path with Nmap mock."""
    # Mocking appropriate paths in src hierarchy
    with patch('src.skills.nmap_skill.nmap.PortScanner') as MockScanner, \
         patch('src.skills.zap_skill.ZAPv2') as MockZap: # Mock ZAP to prevent connection
        
        # Setup Mock Nmap
        mock_nm = MockScanner.return_value
        mock_nm.scan = MagicMock()
        mock_nm.all_hosts.return_value = ['127.0.0.1']
        mock_nm.__getitem__.return_value.all_protocols.return_value = ['tcp']
        mock_nm.__getitem__.return_value.__getitem__.return_value.keys.return_value = [80]
        # service info
        mock_nm.__getitem__.return_value.__getitem__.return_value.__getitem__.return_value = {
            'state': 'open',
            'name': 'http',
            'product': 'Apache',
            'version': '2.4'
        }
        
        # Setup Mock ZAP to return nothing "informational" or empty
        mock_zap_instance = MockZap.return_value
        mock_zap_instance.core.alerts.return_value = []
        mock_zap_instance.core.version = "2.14" # satisfy version check
        
        scanner = ScannerAgent(target='localhost', intensity=5)
        
        results = await scanner.execute()
        
        # We expect 1 nmap finding. ZAP is triggered (port 80 http) but returns 0 findings.
        assert len(results) == 1
        assert results[0].severity == 'medium' # HTTP default is medium
        assert 'Open Port 80' in results[0].description

@pytest.mark.integration
@pytest.mark.asyncio
async def test_scanner_agent_execution_zap_trigger():
    """Test that ZAP is triggered for web targets."""
    with patch('src.skills.nmap_skill.nmap.PortScanner') as MockNmap, \
         patch('src.skills.zap_skill.ZAPv2') as MockZap:
        
        # Mock Nmap finding a web port
        mock_nm = MockNmap.return_value
        mock_nm.all_hosts.return_value = ['127.0.0.1']
        mock_nm.__getitem__.return_value.all_protocols.return_value = ['tcp']
        mock_nm.__getitem__.return_value.__getitem__.return_value.keys.return_value = [80]
        mock_nm.__getitem__.return_value.__getitem__.return_value.__getitem__.return_value = {
            'state': 'open', 'name': 'http', 'product': 'nginx', 'version': '1.0'
        }
        
        # Mock ZAP response
        mock_zap = MockZap.return_value
        mock_zap.core.version = "2.14"
        mock_zap.core.alerts.return_value = [{
            'risk': 'High', 
            'alert': 'SQL Injection', 
            'description': 'sqli found', 
            'url': 'http://localhost'
        }]
        
        scanner = ScannerAgent(target='localhost', intensity=5)
        
        results = await scanner.execute()
        
        # Should have 1 nmap finding + 1 zap finding
        assert len(results) == 2
        assert any(r.description == "ZAP Alert: SQL Injection" for r in results)

# --- Phase 3: Logic & Routing Tests ---

@pytest.mark.unit
@pytest.mark.asyncio
async def test_quality_check_low_confidence():
    """Test that low severity findings result in low confidence."""
    artifact = VulnerabilityArtifact(severity='low', description='foo_desc', evidence='bar_evidence')
    state = RalphState(
        artifacts=[artifact],
        context=ScanContext(intensity=1, target='test'),
        verdict=None,
        confidence=0.0,
        loop_triggered=False
    )
    
    # Needs orchestrator instance to call method
    orch = CyberSurXOrchestrator()
    new_state = await orch.quality_check_node(state)
    assert new_state['confidence'] == 0.4

@pytest.mark.unit
@pytest.mark.asyncio
async def test_routing_logic_rescan():
    """Test that low confidence triggers rescan if retries available."""
    state = RalphState(
        artifacts=[],
        context=ScanContext(intensity=1, target='test', attempt_count=0, max_retries=3),
        verdict=None,
        confidence=0.4, # Low confidence
        loop_triggered=False
    )
    
    orch = CyberSurXOrchestrator()
    route = orch.routing_logic(state)
    assert route == 'rescan'
    assert state['loop_triggered'] is True
    assert state['context'].intensity == 6 # Should have boosted intensity

@pytest.mark.unit
@pytest.mark.asyncio
async def test_routing_logic_circuit_breaker():
    """Test that max retries stops the loop even if confidence is low."""
    state = RalphState(
        artifacts=[],
        context=ScanContext(intensity=1, target='test', attempt_count=3, max_retries=3),
        verdict=None,
        confidence=0.4,
        loop_triggered=False
    )
    
    orch = CyberSurXOrchestrator()
    route = orch.routing_logic(state)
    assert route == 'finalize'

@pytest.mark.integration
@pytest.mark.asyncio
async def test_regulatory_mapper_success():
    """Test mapping of known critical finding."""
    artifact = VulnerabilityArtifact(
        severity='critical',
        description='Unencrypted database connection detected', # Matches rules
        evidence='found'
    )
    state = RalphState(
        artifacts=[artifact],
        context=ScanContext(intensity=1, target='test'),
        verdict=None,
        confidence=0.9,
        loop_triggered=False
    )
    
    orch = CyberSurXOrchestrator()
    # Mocking internal agent to avoid file I/O or just rely on existence of compliance_rules.json
    # Ideally should use a test rules file, but we will rely on integration for now
    # or mock the mapping_db loading if file is missing. 
    # But since compliance_rules.json exists in root, the agent should find it if path logic is correct.
    
    # We might need to adjust rules path in ComplianceAgent if running from tests folder
    # but the agent uses abs path relative to file location, so it should be fine.
    
    new_state = await orch.regulatory_mapper_node(state)
    assert new_state['verdict'].determination == 'non_compliant'
    assert 'HIPAA-2026-164.312(a)(1)' in new_state['verdict'].mapped_controls

@pytest.mark.integration
@pytest.mark.asyncio
async def test_regulatory_mapper_gap():
    """Test that unmapped high severity finding raises ComplianceGapError."""
    artifact = VulnerabilityArtifact(
        severity='critical',
        description='Unknown Critical Issue', # Not in mapping DB
        evidence='found'
    )
    state = RalphState(
        artifacts=[artifact],
        context=ScanContext(intensity=1, target='test'),
        verdict=None,
        confidence=0.9,
        loop_triggered=False
    )
    
    orch = CyberSurXOrchestrator()
    
    with pytest.raises(ComplianceGapError):
        await orch.regulatory_mapper_node(state)

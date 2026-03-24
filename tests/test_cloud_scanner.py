import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from src.agents.cloud_scanner import CloudScannerAgent
from src.agents.ai_hub import AIHub

@pytest.fixture
def mock_prowler_installed():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/prowler"
        yield mock_which

def test_cloud_scanner_init(mock_prowler_installed):
    agent = CloudScannerAgent()
    assert agent.output_dir == "/tmp/prowler_output"

@pytest.mark.asyncio
async def test_cloud_scanner_execute_success(mock_prowler_installed):
    agent = CloudScannerAgent()
    
    # Mock finding the latest output file
    with patch.object(agent, "_get_latest_file") as mock_get_file:
        mock_get_file.return_value = "/tmp/prowler_output/output.json"
        
        # Mocking file open and json load
        mock_findings = [
            {"Status": "PASS", "CheckID": "check1"},
            {"Status": "FAIL", "CheckID": "check2"}
        ]
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_findings))):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                result = await agent.execute(provider="aws")
                
                assert result["status"] == "completed"
                assert result["total_checks"] == 2
                assert result["failed_checks"] == 1
                assert result["provider"] == "aws"
                
                # Verify command
                args, _ = mock_run.call_args
                command = args[0]
                assert "prowler" in command
                assert "aws" in command

@pytest.mark.asyncio
async def test_ai_hub_routing_cloud(mock_prowler_installed):
    hub = AIHub()
    mock_agent = MagicMock()
    mock_agent.execute.return_value = {"status": "mock_started"}
    
    # Register mock instead of real agent to test routing logic only
    hub.register_agent("cloud_scanner", mock_agent)
    
    # Test "scan aws" intent (keywords handled in DetermineIntent or default intent map)
    # "aws" is in intent_map
    await hub.process_command("scan aws environment", {})
    
    mock_agent.execute.assert_called_once()
    kwargs = mock_agent.execute.call_args[1]
    assert kwargs["provider"] == "aws"

@pytest.mark.asyncio
async def test_ai_hub_routing_azure(mock_prowler_installed):
    hub = AIHub()
    mock_agent = MagicMock()
    mock_agent.execute.return_value = {"status": "mock_started"}
    hub.register_agent("cloud_scanner", mock_agent)
    
    await hub.process_command("check azure compliance", {})
    
    # Should detect "azure" in command and pass provider="azure"
    kwargs = mock_agent.execute.call_args[1]
    assert kwargs["provider"] == "azure"

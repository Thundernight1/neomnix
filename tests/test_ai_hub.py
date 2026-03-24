import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.ai_hub import AIHub

@pytest.mark.asyncio
async def test_ai_hub_registration():
    hub = AIHub()
    mock_agent = AsyncMock()
    hub.register_agent("test_agent", mock_agent)
    assert "test_agent" in hub.agents
    assert hub.agents["test_agent"] == mock_agent

@pytest.mark.asyncio
async def test_ai_hub_routing_scan():
    hub = AIHub()
    mock_scanner = AsyncMock()
    mock_scanner.execute.return_value = {"status": "started"}
    
    hub.register_agent("scanner", mock_scanner)
    
    # Test "scan" intent
    await hub.process_command("scan localhost", {})
    
    # Verify called with correct arguments
    mock_scanner.execute.assert_called_once()
    _, kwargs = mock_scanner.execute.call_args
    assert kwargs.get("target") == "localhost"

@pytest.mark.asyncio
async def test_ai_hub_routing_explain():
    hub = AIHub()
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = "Explanation"
    
    hub.register_agent("llm", mock_llm)
    
    # Test "explain" intent
    result = await hub.process_command("explain CVE-2024-123", {})
    
    assert result == "Explanation"
    mock_llm.chat.assert_called_once()

@pytest.mark.asyncio
async def test_ai_hub_routing_analyze():
    hub = AIHub()
    mock_mapper = AsyncMock()
    mock_mapper.analyze.return_value = {"analysis": "data"}
    
    hub.register_agent("cross_mapper", mock_mapper)
    
    # Test "analyze" intent
    result = await hub.process_command("analyze CVE-2024-5678", {})
    
    assert result == {"analysis": "data"}
    mock_mapper.analyze.assert_called_once()
    args, _ = mock_mapper.analyze.call_args
    assert "CVE-2024-5678" in args[0] or "analyze CVE-2024-5678" in args[0]

@pytest.mark.asyncio
async def test_ai_hub_routing_unknown():
    hub = AIHub()
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = "I don't understand"
    
    # Register LLM as fallback
    hub.register_agent("llm", mock_llm)
    
    # Unknown commands should default to LLM
    await hub.process_command("unknown command", {})
    mock_llm.chat.assert_called_once()

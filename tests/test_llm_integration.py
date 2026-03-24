import os
import pytest
from unittest.mock import patch, Mock
from src.agents.llm_agent import LLMAgent

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "test_key")
    monkeypatch.setenv("LLM_MODEL", "test_model")
    monkeypatch.setenv("LLM_API_BASE", "https://api.ollama.com")

def test_llm_agent_init_mock():
    # Test initialization without API key (should be mock)
    with patch.dict(os.environ, {}, clear=True):
        agent = LLMAgent()
        assert agent.provider == "mock"

def test_llm_agent_init_ollama(mock_env_vars):
    # Test initialization with API key (should be ollama)
    agent = LLMAgent()
    assert agent.provider == "ollama"
    assert agent.api_key == "test_key"
    assert agent.model == "test_model"

@pytest.mark.asyncio
async def test_llm_agent_chat_ollama_payload(mock_env_vars):
    agent = LLMAgent()
    
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"message": {"content": "Test response"}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Execute
        result = await agent.chat("Hello")

        # Verify network call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check URL
        assert args[0] == "https://api.ollama.com/chat"
        
        # Check Headers
        assert kwargs["headers"]["Authorization"] == "Bearer test_key"
        
        # Check Payload
        payload = kwargs["json"]
        assert payload["model"] == "test_model"
        assert payload["messages"][1]["content"] == "Hello"
        assert result["response"] == "Test response"
        assert result["provider"] == "ollama"

@pytest.mark.asyncio
async def test_llm_agent_context_injection(mock_env_vars):
    agent = LLMAgent()
    context = {"findings": [{"id": "CVE-123"}]}
    
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_post.return_value = mock_response

        await agent.chat("Explain", context=context)
        
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        system_prompt = payload["messages"][0]["content"]
        
        assert "CVE-123" in system_prompt

import requests

@pytest.mark.asyncio
async def test_llm_agent_error_handling(mock_env_vars):
    agent = LLMAgent()
    
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException("Network Error")
        
        result = await agent.chat("fail")
        
        assert result["status"] == "error"
        assert "Network Error" in result["response"]

import os
import requests
import json
from typing import Dict, Any, Optional

class LLMAgent:
    """
    Agent responsible for Natural Language Understanding and Generation.
    Supports Ollama Cloud API and Mock mode.
    """
    def __init__(self):
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.api_base = os.getenv("LLM_API_BASE", "https://ollama.com/api")
        self.model = os.getenv("LLM_MODEL", "qwen3-coder-next:cloud")
        
        # Determine provider based on config
        if self.api_key:
            self.provider = "ollama"
        else:
            self.provider = "mock"
            print(f"[{self.__class__.__name__}] No API Key found. Running in MOCK mode.")

    async def chat(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process natural language query.
        """
        if self.provider == "mock":
            return self._mock_response(user_query)
        
        if self.provider == "ollama":
            return self._call_ollama(user_query, context)
            
        return {"response": "LLM Provider not configured."}

    def _call_ollama(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Call Ollama Cloud API (Sync call wrapped in async agent method).
        Note: In production, use httpx or run_in_executor for non-blocking IO.
        """
        url = f"{self.api_base}/chat"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct system prompt based on context
        system_prompt = "You are CyberSurX, an AI Security Compliance Assistant. Answer queries about security findings, compliance gaps, and remediation."
        
        if context and context.get("findings"):
             system_prompt += f"\nContext Findings: {json.dumps(context['findings'])}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "stream": False
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Ollama API response structure: {"message": {"content": "..."}}
            content = data.get("message", {}).get("content", "No response content.")
            
            return {
                "response": content,
                "provider": "ollama",
                "model": self.model
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Ollama API Error: {e}")
            return {
                "response": f"Error communicating with AI Brain: {str(e)}",
                "status": "error"
            }

    def _mock_response(self, query: str) -> Dict[str, Any]:
        """
        Simple rule-based responses for testing.
        """
        query_lower = query.lower()
        
        if "explain" in query_lower:
            return {
                "response": "I can explain the compliance impact of specific vulnerabilities. Try asking 'explain CVE-202X-XXXX'."
            }
        
        if "hello" in query_lower:
            return {
                "response": "Hello! I am the CyberSurX AI Assistant. I can help you run scans, analyze compliance, or explain findings."
            }

        return {
            "response": f"I understood your query '{query}', but I am running in Mock Mode. Set OLLAMA_API_KEY to enable real intelligence."
        }

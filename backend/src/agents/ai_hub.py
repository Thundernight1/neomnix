from typing import Dict, Any, List, Optional
from src.agents.scanner import ScannerAgent
# We will import CrossMappingAnalyzer and LLMAgent here once created
# For now, we mock or allow deferred registration if they cause circular imports

class AIHub:
    """
    Central Orchestrator for AI Agents.
    Routes user commands to the appropriate specialized agent.
    """
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.intent_map = {
            "cloud": "cloud_scanner",
            "aws": "cloud_scanner",
            "azure": "cloud_scanner",
            "gcp": "cloud_scanner",
            "scan": "scanner",
            "verify": "scanner",
            "analyze": "cross_mapper",
            "map": "cross_mapper",
            "explain": "llm",
            "chat": "llm"
        }


    def register_agent(self, name: str, agent_instance: Any):
        """Register a new agent capability."""
        self.agents[name] = agent_instance

    async def process_command(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Determine intent and dispatch to the correct agent.
        """
        agent_name = self._determine_intent(command)
        # agent_name = self.intent_map.get(intent, "llm") # REMOVED duplicated lookup
        
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not available.", "status": "failed"}

        try:
            # Dispatch based on agent interface
            # Assuming agents have a standard 'execute' or we handle specific methods
            if agent_name == "scanner":
                # contextual extraction needed here (e.g. target from command)
                # For MVP, we might expect structured context or use LLM to parse
                target = context.get('target', 'localhost') if context else 'localhost'
                # If target is in command, we need to extract it (LLM would do this in real implementation)
                
                # Pass context (which might contain DB session) to the agent
                return await agent.execute(target=target, context=context)
            
            elif agent_name == "cross_mapper":
                return await agent.analyze(command)
            
            elif agent_name == "llm":
                return await agent.chat(command, context=context)

            elif agent_name == "cloud_scanner":
                # Default to AWS, or extract from command/context
                provider = "aws"
                if "azure" in command.lower():
                    provider = "azure"
                elif "gcp" in command.lower():
                    provider = "gcp"
                
                return await agent.execute(provider=provider, context=context)
                
            return {"error": "Unknown agent interface", "status": "failed"}
            
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _determine_intent(self, command: str) -> str:
        """
        Simple keyword-based intent detection.
        Will be replaced by specific LLM classifier later.
        """
        cmd_lower = command.lower()
        for key in self.intent_map:
            if key in cmd_lower:
                return self.intent_map[key]
        return "llm"

from typing import Dict, Any, List, Optional
from src.agents.scanner import ScannerAgent

# Post-DCE: only PCAP-scope agents remain. The previous LLM and
# cloud_scanner agents were removed because the platform no longer
# serves cloud-provider or open-ended chat workloads — it is
# strictly a network-PCAP compliance scanner for HIPAA-2026 and
# WA-MHMDA.

class AIHub:
    """
    Central Orchestrator for AI Agents.
    Routes user commands to the appropriate specialized agent.
    """
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.intent_map = {
            "scan": "scanner",
            "verify": "scanner",
            "analyze": "cross_mapper",
            "map": "cross_mapper",
        }


    def register_agent(self, name: str, agent_instance: Any):
        """Register a new agent capability."""
        self.agents[name] = agent_instance

    async def process_command(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Determine intent and dispatch to the correct agent.
        """
        agent_name = self._determine_intent(command)

        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not available.", "status": "failed"}

        try:
            # Dispatch based on agent interface
            if agent_name == "scanner":
                # contextual extraction needed here (e.g. target from command)
                # For MVP, we might expect structured context or use LLM to parse
                target = context.get('target', 'localhost') if context else 'localhost'

                # Pass context (which might contain DB session) to the agent
                return await agent.execute(target=target, context=context)

            elif agent_name == "cross_mapper":
                return await agent.analyze(command)

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
        return "scanner"

import asyncio
from typing import TypedDict, Union, List, Literal
from langgraph.graph import StateGraph, END # type: ignore
from src.models.contracts import VulnerabilityArtifact, ScanContext, ComplianceVerdict, RalphState
from src.agents.scanner import ScannerAgent
from src.agents.compliance import ComplianceAgent, ComplianceGapError

class CyberSurXOrchestrator:
    """
    Principal Architect Agent.
    Orchestrates the recursive loop between Scanner and Compliance agents.
    """
    
    def __init__(self):
        self.workflow = StateGraph(RalphState)
        self._build_graph()
        self.compliance_agent = ComplianceAgent()

    def _build_graph(self):
        self.workflow.add_node("scanner", self.scanner_node)
        self.workflow.add_node("quality_check", self.quality_check_node)
        self.workflow.add_node("regulatory_mapper", self.regulatory_mapper_node)
        
        self.workflow.set_entry_point("scanner")
        
        self.workflow.add_edge("scanner", "quality_check")
        
        self.workflow.add_conditional_edges(
            "quality_check",
            self.routing_logic,
            {
                "rescan": "scanner",
                "finalize": "regulatory_mapper"
            }
        )
        
        self.workflow.add_edge("regulatory_mapper", END)
        self.app = self.workflow.compile()

    async def scanner_node(self, state: RalphState) -> RalphState:
        print(f"--- [Orchestrator] Dispatching ScannerAgent (Intensity: {state['context'].intensity}) ---")
        agent = ScannerAgent(
            target=state['context'].target,
            intensity=state['context'].intensity
        )
        new_artifacts = await agent.execute()
        state['artifacts'] = new_artifacts
        state['context'].attempt_count += 1
        return state

    async def quality_check_node(self, state: RalphState) -> RalphState:
        print("--- [Orchestrator] Performing Quality Check ---")
        artifacts = state['artifacts']
        if not artifacts:
            state['confidence'] = 0.0
            return state
        
        has_critical = any(a.severity in ('high', 'critical') for a in artifacts)
        has_medium = any(a.severity == 'medium' for a in artifacts)
        
        if has_critical:
            confidence = 0.95
        elif has_medium:
            confidence = 0.7
        else:
            confidence = 0.4
            
        state['confidence'] = confidence
        print(f"--- [Orchestrator] Confidence Score: {confidence} ---")
        return state

    async def regulatory_mapper_node(self, state: RalphState) -> RalphState:
        print("--- [Orchestrator] Dispatching ComplianceAgent ---")
        try:
            job_id = state['context'].job_id or self.compliance_agent.run_id
            verdict = self.compliance_agent.evaluate(
                state['artifacts'], 
                state['confidence'],
                job_id=job_id
            )
            state['verdict'] = verdict
            print(f"--- [Orchestrator] Verdict: {verdict.determination} ---")
            return state
        except Exception as e:
            print(f"!!! [Orchestrator] ComplianceAgent error: {e} !!!")
            raise e

    def routing_logic(self, state: RalphState) -> Literal['rescan', 'finalize']:
        confidence = state['confidence']
        ctx = state['context']
        
        if confidence < 0.8 and ctx.attempt_count < ctx.max_retries:
            print(">>> [CyberSurX] Low confidence detected. Triggering recursive intensity boost. <<<")
            ctx.intensity += 5 
            state['loop_triggered'] = True
            return 'rescan'
        
        print(">>> [CyberSurX] Confidence threshold met. Proceeding to verdict. <<<")
        return 'finalize'

    async def run(self, target: str):
        print("\n=== Initializing CyberSurX (Zero-Trust Compliance System) ===\n")
        initial_state = RalphState(
            artifacts=[],
            context=ScanContext(intensity=1, target=target),
            verdict=None,
            confidence=0.0,
            loop_triggered=False
        )
        
        try:
            final_state = await self.app.ainvoke(initial_state)
            print("\n=== Execution Complete ===")
            if final_state['verdict']:
                print(f"Final Determination: {final_state['verdict'].determination}")
                print(f"Mapped Controls: {final_state['verdict'].mapped_controls}")
        except Exception as e:
            print(f"\n!!! SYSTEM ERROR: {e} !!!")

if __name__ == "__main__":
    orchestrator = CyberSurXOrchestrator()
    asyncio.run(orchestrator.run("localhost"))

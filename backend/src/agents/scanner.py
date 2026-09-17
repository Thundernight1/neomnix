from typing import List
from src.models.contracts import VulnerabilityArtifact
from src.skills.nmap_skill import NmapSkill
from src.skills.zap_skill import ZapSkill

class ScannerAgent:
    """
    Agent responsible for technical security scanning.
    Orchestrates specialized Skills (Nmap, ZAP).
    """
    
    def __init__(self, target: str, intensity: int):
        self.target = target
        self.intensity = intensity
        self.nmap_skill = NmapSkill()
        self.zap_skill = ZapSkill()

    async def execute(self) -> List[VulnerabilityArtifact]:
        """Execute scan based on configured tools."""
        findings = []
        
        # 1. Execute Nmap Skill
        nmap_result = await self.nmap_skill.execute(self.target, self.intensity)
        if nmap_result.get("error"):
            raise RuntimeError("Network scan failed")
        nmap_findings = nmap_result.get("artifacts", [])
        findings.extend(nmap_findings)
        
        # 2. Decide if ZAP is needed
        is_web_target = self.target.startswith("http") or any(
            "http" in f.description.lower() for f in nmap_findings
        )
        
        if is_web_target:
             zap_target = self.target
             if not zap_target.startswith(("http://", "https://")):
                 zap_target = f"http://{zap_target}"
                 
             zap_result = await self.zap_skill.execute(zap_target, self.intensity)
             if zap_result.get("error"):
                 raise RuntimeError("Web scan failed")
             findings.extend(zap_result.get("artifacts", []))
             
        return findings

    async def _execute_zap(self) -> List[VulnerabilityArtifact]:
        """Reuse the configured scanner rather than a second incomplete implementation."""
        result = await self.zap_skill.execute(self.target, self.intensity)
        if result.get("error"):
            raise RuntimeError("Web scan failed")
        return result.get("artifacts", [])

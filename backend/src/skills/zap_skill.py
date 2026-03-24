import asyncio
from zapv2 import ZAPv2 # type: ignore
from typing import Dict, Any, List
from src.skills.base import BaseSkill
from src.models.contracts import VulnerabilityArtifact

class ZapSkill(BaseSkill):
    """
    Skill: Web Application Security Scanning.
    Wraps OWASP ZAP API.
    """
    
    def __init__(self):
        super().__init__(name="zap")
        import os
        zap_host = os.getenv("ZAP_HOST", "127.0.0.1")
        zap_port = os.getenv("ZAP_PORT", "8080")
        self.zap_url = f"http://{zap_host}:{zap_port}"
        print(f"--- [Skill: ZAP] Initialized with proxy {self.zap_url} ---")
        self.zap = ZAPv2(proxies={'http': self.zap_url, 'https': self.zap_url})
        
    async def execute(self, target: str, intensity: int = 1) -> Dict[str, Any]:
        print(f"--- [Skill: ZAP] Initiating Scan on {target} ---")
        
        try:
            # Check Connection
            version = await asyncio.to_thread(lambda: self.zap.core.version)
            print(f"--- [Skill: ZAP] Connected to ZAP {version} ---")
            
            # Spider
            scan_id = await asyncio.to_thread(self.zap.spider.scan, target)
            await self._poll_status(self.zap.spider.status, scan_id, "Spider")
            
            # Active Scan (High Intensity)
            if intensity >= 5:
                scan_id = await asyncio.to_thread(self.zap.ascan.scan, target)
                await self._poll_status(self.zap.ascan.status, scan_id, "Active Scan", interval=5)
            
            # Retrieve Alerts (Raw Data)
            alerts = await asyncio.to_thread(self.zap.core.alerts, baseurl=target)
            
            # Save Raw Data
            self.save_data(alerts, subfolder="raw", prefix="scan_")
            
            # Parse Artifacts
            artifacts = self._parse_results(alerts)
            
            return {
                "raw_file": f"data/raw/scan_zap_{self.run_id}.json",
                "artifacts": artifacts
            }
            
        except Exception as e:
            print(f"!!! [Skill: ZAP] Failed: {e} !!!")
            # Fail gracefully
            return {"error": str(e), "artifacts": []}

    async def _poll_status(self, status_method, scan_id, name, interval=2):
        while True:
            try:
                progress = await asyncio.to_thread(lambda: int(status_method(scan_id)))
                print(f"--- [Skill: ZAP] {name} Progress: {progress}% ---")
                if progress >= 100: break
            except:
                break # Exit if status check fails (scan likely finished or errored)
            await asyncio.sleep(interval)

    def _parse_results(self, alerts) -> List[VulnerabilityArtifact]:
        artifacts = []
        for alert in alerts:
            risk = alert.get('risk')
            if risk == 'Informational': continue
            
            severity = 'low'
            if risk == 'Medium': severity = 'medium'
            if risk == 'High': severity = 'high'
            
            artifacts.append(VulnerabilityArtifact(
                severity=severity,
                description=f"ZAP Alert: {alert.get('alert')}",
                evidence=f"URL: {alert.get('url')}\nDetails: {alert.get('description')[:200]}"
            ))
        return artifacts

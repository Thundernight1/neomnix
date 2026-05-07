import asyncio
import nmap # type: ignore
from typing import Dict, Any, List
from src.skills.base import BaseSkill
from src.models.contracts import VulnerabilityArtifact

class NmapSkill(BaseSkill):
    """
    Skill: Network Mapping & Port Scanning.
    Wraps python-nmap to perform actual scans and save raw output.
    """
    
    def __init__(self):
        super().__init__(name="nmap")
        
    async def execute(self, target: str, intensity: int = 1) -> Dict[str, Any]:
        print(f"--- [Skill: Nmap] Initiating Scan on {target} (Intensity: {intensity}) ---")
        nm = nmap.PortScanner()
        
        # Base arguments
        args = "-T4"
        
        # Add version detection and SSL scripts
        args += " -sV --script ssl-cert,ssl-enum-ciphers"
        
        if intensity <= 3:
            args += " -F"
        elif intensity >= 8:
            args += " -A"
            
        try:
            # Execute Scan
            await asyncio.to_thread(nm.scan, target, arguments=args)
            
            # 1. Get RAW Data (The full XML/JSON structure from Nmap)
            # This answers: "Where is the data?" -> Saved to data/raw/
            raw_data = {}
            for host in nm.all_hosts():
                 raw_data[host] = nm[host]
            
            self.save_data(raw_data, subfolder="raw", prefix="scan_")
            
            # 2. Parse into Artifacts (The "Processed" Data)
            artifacts = self._parse_results(nm)
            
            return {
                "raw_file": f"data/raw/scan_nmap_{self.run_id}.json",
                "artifacts": artifacts
            }
            
        except Exception as e:
            print(f"!!! [Skill: Nmap] Failed: {e} !!!")
            return {"error": str(e), "artifacts": []}

    def _parse_results(self, nm) -> List[VulnerabilityArtifact]:
        artifacts = []
        for host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                ports = nm[host][proto].keys()
                for port in ports:
                    service = nm[host][proto][port]
                    state = service['state']
                    name = service['name']
                    product = service.get('product', '')
                    version = service.get('version', '')
                    
                    if state == 'open':
                        severity = 'low'
                        if 'http' in name or port in [80, 443, 8080]: severity = 'medium'
                        if 'telnet' in name or port == 23: severity = 'critical'
                        if 'ftp' in name or port == 21: severity = 'high'
                        
                        # Check for SSL script output
                        script_out = ""
                        if 'script' in service:
                            for script_name, output in service['script'].items():
                                script_out += f"\n[{script_name}]: {output}"
                                if "ssl" in script_name and ("expired" in output or "weak" in output):
                                    severity = 'high' # Elevate severity for bad certs
                            
                        artifacts.append(VulnerabilityArtifact(
                            severity=severity,
                            description=f"Open Port {port}/{proto} ({name})",
                            evidence=f"Product: {product} {version}, State: {state}{script_out}"
                        ))
        return artifacts

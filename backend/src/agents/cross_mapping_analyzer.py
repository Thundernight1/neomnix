import json
import os
from typing import Dict, List, Any

class CrossMappingAnalyzer:
    """
    Analyzes intersection of compliance frameworks.
    Maps vulnerabilities to multiple regulatory standards simultaneously.
    """
    def __init__(self, rules_path: str = "src/core/compliance_rules.json"):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.rules_path = os.path.join(base_dir, rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict:
        if not os.path.exists(self.rules_path):
            return {}
        with open(self.rules_path, "r") as f:
            data = json.load(f)
            # Flatten mappings: { "trigger": {frameworks...} }
            # Since JSON has list of controls like "HIPAA...", we group them.
            rules = {}
            for item in data.get("mappings", []):
                trigger = item.get("technical_trigger")
                controls = item.get("controls", [])
                # Extract framework names for analysis
                frameworks = list(set([self._framework_of_control(c) for c in controls]))
                rules[trigger] = {
                    "frameworks": frameworks,
                    "controls": controls,
                    "description": item.get("description", "")
                }
            return rules

    def _framework_of_control(self, control: str) -> str:
        if control.startswith("HIPAA-"):
            return "HIPAA-2026" if control.startswith("HIPAA-2026") else "HIPAA"
        if control.startswith("WA-MHMDA"):
            return "WA-MHMDA"
        if control.startswith("NIST-800-53"):
            return "NIST-800-53"
        if control.startswith("SOC2"):
            return "SOC2"
        if control.startswith("CCM-"):
            return "CCM-4.0" if control.startswith("CCM-4.0") else "CCM"
        if control.startswith("SEC-"):
            return "SEC-2023" if control.startswith("SEC-2023") else "SEC"
        return control.split("-", 1)[0]

    async def analyze(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query to find relevant framework mappings.
        Query can be a vulnerability name or a control ID.
        """
        results = {}
        query_lower = query.lower()
        
        # Search in rules
        # Structure: {"vulnerability_id": {"framework": ["controls"]}}
        # Or {"mappings": ...} depending on exact JSON structure. 
        # Assuming simple dict for now based on file name imply mappings.
        
        matches = []
        for vuln, details in self.rules.items():
            match_found = False
            # Check vulnerability name
            if query_lower in vuln.lower():
                match_found = True
            # Check description
            elif query_lower in details.get("description", "").lower():
                match_found = True
            # Check controls
            elif any(query_lower in c.lower() for c in details.get("controls", [])):
                match_found = True
                
            if match_found:
                matches.append({
                    "vulnerability": vuln,
                    "impact": details["frameworks"],
                    "controls": details["controls"]
                })
        
        # Analyze overlaps (Cross-Walk)
        impact_analysis = {}
        for match in matches:
            frameworks = match['impact']
            impact_analysis[match['vulnerability']] = {
                "message": f"Affects {len(frameworks)} frameworks: {', '.join(frameworks)}",
                "frameworks": list(frameworks),
                "controls": match['controls']
            }

        return {
            "query": query,
            "matches": len(matches),
            "analysis": impact_analysis
        }

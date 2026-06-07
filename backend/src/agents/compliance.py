import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.models.contracts import VulnerabilityArtifact, ComplianceVerdict
from src.utils.pdf_exporter import PDFReportExporter

class ComplianceGapError(Exception):
    pass

class ComplianceAgent:
    """
    Agent responsible for mapping technical findings to regulatory controls.
    Generates and saves final compliance reports.
    """
    
    def __init__(self, rules_path: str = "src/core/compliance_rules.json"):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.rules_path = os.path.join(base_dir, rules_path)
        self.mapping_db = self._load_rules()
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pdf_exporter = PDFReportExporter()

    def _load_rules(self) -> Dict[str, List[str]]:
        try:
            with open(self.rules_path, "r") as f:
                data = json.load(f)
                return {
                    self._normalize_trigger_key(m["technical_trigger"]): m["controls"]
                    for m in data.get("mappings", [])
                }
        except Exception as e:
            raise RuntimeError(f"Failed to load compliance rules from {self.rules_path}: {e}")

    def _normalize_trigger_key(self, value: str) -> str:
        return " ".join(value.lower().split())

    def evaluate(self, artifacts: List[VulnerabilityArtifact], confidence: float, job_id: str = "") -> ComplianceVerdict:
        print("--- [ComplianceAgent] Evaluating Compliance against Multiple Frameworks ---")
        
        # Use the provided job_id (UUID) or fall back to timestamp
        effective_job_id = job_id or self.run_id
        
        mapped_controls = []
        unmapped_findings = []
        
        for artifact in artifacts:
            if artifact.severity in ('high', 'critical'):
                artifact_key = self._normalize_trigger_key(artifact.description)
                controls = self.mapping_db.get(artifact_key)
                
                if not controls:
                    # Fuzzy match — check if any rule key is a substring of the finding or vice versa
                    for key, val in self.mapping_db.items():
                        if key in artifact_key or artifact_key in key:
                            controls = val
                            break
                
                if not controls:
                    # --- FIX 2: Graceful handling instead of crash ---
                    print(f"⚠️  [ComplianceAgent] WARNING: No regulatory mapping for: '{artifact.description}' — logged as unmapped.")
                    unmapped_findings.append(artifact.description)
                    continue
                    
                mapped_controls.extend(controls)
        
        unique_controls = list(set(mapped_controls))
        
        # Determine verdict with nuance
        if unique_controls and unmapped_findings:
            determination = 'partial_compliance'
            reasoning = f"Violations detected with {len(unmapped_findings)} unmapped finding(s) requiring manual review."
        elif unique_controls:
            determination = 'non_compliant'
            reasoning = "Critical violations detected across mapped regulatory controls."
        elif unmapped_findings:
            determination = 'partial_compliance'
            reasoning = f"No mapped violations, but {len(unmapped_findings)} finding(s) lack regulatory mapping."
        else:
            determination = 'compliant'
            reasoning = "No mapped violations found."
        
        verdict = ComplianceVerdict(
            determination=determination,
            confidence_score=confidence,
            mapped_controls=unique_controls,
            unmapped_findings=unmapped_findings,
            reasoning=reasoning
        )
        
        # Save reports with the correct UUID job_id
        self._generate_framework_reports(verdict, artifacts, effective_job_id)
        self._generate_pdf_reports(verdict, artifacts, effective_job_id)
        
        return verdict

    def _generate_framework_reports(self, verdict: ComplianceVerdict, artifacts: List[VulnerabilityArtifact], job_id: str):
        """Generates separate Markdown reports for each compliance framework."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        directory = os.path.join(base_dir, "reports")
        os.makedirs(directory, exist_ok=True)
        
        frameworks = self._extract_frameworks(verdict)

        for fw in frameworks:
            self._save_markdown_report(fw, verdict, artifacts, directory, job_id)
            
    def _save_markdown_report(self, framework: str, verdict: ComplianceVerdict, artifacts: List[VulnerabilityArtifact], directory: str, job_id: str):
        filename = f"{framework}_Report_{job_id}.md"
        filepath = os.path.join(directory, filename)
        
        relevant_controls = [c for c in verdict.mapped_controls if framework in c or (framework == "NIST-800-53" and "NIST" in c)]
        
        md_content = f"""# {framework} Compliance Report
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Scan ID:** {job_id}
**Overall Status:** {verdict.determination.upper()}
**Confidence Score:** {verdict.confidence_score}

## Executive Summary
The automated Neomnix system performed a zero-trust security scan.
{'CRITICAL VIOLATIONS FOUND.' if relevant_controls else 'No critical violations mapped to this framework.'}

## Mapped Controls ({len(relevant_controls)})
"""
        for control in relevant_controls:
            md_content += f"- **{control}**\n"

        if verdict.unmapped_findings:
            md_content += f"\n## ⚠️ Unmapped Findings ({len(verdict.unmapped_findings)})\n"
            for uf in verdict.unmapped_findings:
                md_content += f"- {uf}\n"
            
        md_content += "\n## Technical Findings & Evidence\n"
        
        for artifact in artifacts:
            if artifact.severity in ('high', 'critical'):
                md_content += f"### [{artifact.severity.upper()}] {artifact.description}\n"
                md_content += f"- **Evidence:** `{artifact.evidence}`\n"
                md_content += f"- **Timestamp:** {artifact.timestamp}\n\n"
        
        with open(filepath, "w") as f:
            f.write(md_content)
            
        print(f"--- [ComplianceAgent] Generated Report: {filepath} ---")

    def _extract_frameworks(self, verdict: ComplianceVerdict) -> set:
        """Extract active frameworks from mapped controls."""
        frameworks = set()
        for control in verdict.mapped_controls:
            if control.startswith("HIPAA"): frameworks.add("HIPAA-2026")
            elif control.startswith("WA-MHMDA"): frameworks.add("WA-MHMDA")
            elif control.startswith("NIST"): frameworks.add("NIST-800-53")
            elif control.startswith("SOC2"): frameworks.add("SOC2")
        if not frameworks:
            frameworks = {"HIPAA-2026", "WA-MHMDA"}
        return frameworks

    def _generate_pdf_reports(self, verdict: ComplianceVerdict, artifacts: List[VulnerabilityArtifact], job_id: str):
        """Generates PDF versions of the reports for commercial use."""
        frameworks = self._extract_frameworks(verdict)

        for fw in frameworks:
            try:
                findings_dicts = [a.model_dump() for a in artifacts if a.severity in ('high', 'critical')]
                pdf_path = self.pdf_exporter.generate_report(
                    framework=fw,
                    findings=findings_dicts,
                    status=verdict.determination,
                    confidence=verdict.confidence_score,
                    job_id=job_id
                )
                print(f"--- [ComplianceAgent] Generated PDF Report: {pdf_path} ---")
            except Exception as e:
                print(f"!!! [ComplianceAgent] Failed to generate PDF for {fw}: {e} !!!")

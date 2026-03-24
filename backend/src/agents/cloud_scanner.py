import subprocess
import json
import os
import shutil
from typing import Dict, Any, List

class CloudScannerAgent:
    """
    Agent responsible for Cloud Security Posture Management (CSPM) scanning using Prowler.
    Wraps the 'prowler' CLI tool.
    """
    def __init__(self):
        self.output_dir = "/tmp/prowler_output"
        os.makedirs(self.output_dir, exist_ok=True)
        # Check if prowler is installed
        if not shutil.which("prowler"):
            print("WARNING: 'prowler' executable not found in PATH. Cloud scanning will fail.")

    async def execute(self, provider: str = "aws", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a cloud scan using Prowler.
        
        Args:
            provider: Cloud provider ('aws', 'azure', 'gcp'). Default: 'aws'.
            context: Additional context (regions, specific services).
        """
        if provider not in ["aws", "azure", "gcp"]:
            return {"status": "error", "message": f"Unsupported provider: {provider}"}

        # Construct command
        # Note: In a real environment, we might need to handle authentication explicitly 
        # if not using environment variables or instance roles.
        command = ["prowler", provider, "--json-output", "--output-directory", self.output_dir]
        
        # Add basic filters/regions if in context
        if context:
            if context.get("region"):
                command.extend(["-f", context["region"]]) # Example flag, check prowler docs for specific provider flags
            # Add more flags as needed

        try:
            # Run Prowler
            # capture_output=True might be heavy for large scans, reusing file output
            print(f"Running Prowler command: {' '.join(command)}")
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False # Prowler might exit with non-zero if findings are found
            )
            
            # Prowler generates a JSON file in the output directory. 
            # We need to find the latest file.
            output_file = self._get_latest_file(self.output_dir, ".json")
            
            if not output_file:
                return {
                    "status": "failed", 
                    "message": "Prowler ran but no output file was generated.",
                    "stderr": process.stderr
                }

            with open(output_file, 'r') as f:
                # Prowler JSON output can be a list of JSON objects or a single JSON array
                # Depending on version. Prowler v3+ usually outputs a JSON array.
                try:
                    findings = json.load(f)
                except json.JSONDecodeError:
                    # Fallback for line-delimited JSON if configured that way
                    f.seek(0)
                    findings = [json.loads(line) for line in f]

            # Summary
            failed_checks = [f for f in findings if f.get("Status") == "FAIL"]
            
            return {
                "status": "completed",
                "provider": provider,
                "total_checks": len(findings),
                "failed_checks": len(failed_checks),
                "findings_summary": f"Found {len(failed_checks)} failures out of {len(findings)} checks.",
                "report_path": output_file,
                # "details": failed_checks # Optional: include full details
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _get_latest_file(self, directory: str, extension: str) -> str:
        files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]
        if not files:
            return None
        return max(files, key=os.path.getctime)

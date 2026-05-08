"""
SharkTap Passive Network Analysis Skill
========================================
Processes PCAP files captured by a SharkTap inline network tap and converts
detected network threats into VulnerabilityArtifacts that flow through the
standard Neomnix compliance pipeline.

Workflow:
  Analyst (on-site) → SharkTap → capture.pcap → Upload to API →
  SharkTapSkill.analyze_pcap() → VulnerabilityArtifacts →
  ComplianceAgent → HIPAA/SOC2/NIST/CCM/SEC cross-mapped PDF report

This skill uses tshark (Wireshark CLI) for PCAP analysis. tshark must be
installed in the Docker image (wireshark-common package).
"""

import subprocess
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List

from src.skills.base import BaseSkill
from src.models.contracts import VulnerabilityArtifact


# ── Threat → Severity map ─────────────────────────────────────────────────────
THREAT_SEVERITY = {
    "PORT_SCAN":                  "high",
    "DNS_TUNNELING_SUSPECTED":    "high",
    "CLEARTEXT_HTTP_POST":        "medium",
    "CLEARTEXT_TELNET_SESSION":   "critical",
    "CLEARTEXT_FTP_SESSION":      "high",
    "UNENCRYPTED_DATABASE":       "high",
    "LARGE_OUTBOUND_TRANSFER":    "medium",
    "BROADCAST_STORM":            "low",
}


class SharkTapSkill(BaseSkill):
    """
    Analyzes PCAP files from a SharkTap passive network tap.
    Converts network threats to VulnerabilityArtifacts for compliance mapping.
    """

    def __init__(self):
        super().__init__(name="sharktap")
        self._check_tshark()

    def _check_tshark(self):
        result = subprocess.run(["which", "tshark"], capture_output=True)
        if result.returncode != 0:
            print("⚠️  [SharkTap] tshark not found. Install: apt install tshark  |  brew install wireshark")

    # ─── Main entry point ────────────────────────────────────────────────────
    async def execute(self, target: str, intensity: int = 1) -> Dict[str, Any]:
        """
        BaseSkill interface. `target` here is the path to a PCAP file.
        Used when SharkTapSkill is called through the standard scan pipeline.
        """
        if not os.path.exists(target):
            return {"error": f"PCAP file not found: {target}", "artifacts": []}
        return self.analyze_pcap(target, intensity)

    def analyze_pcap(self, pcap_file: str, intensity: int = 1) -> Dict[str, Any]:
        """
        Full PCAP analysis: stats, protocol hierarchy, top talkers,
        DNS queries, HTTP hosts, and threat detection.
        Returns structured results + VulnerabilityArtifacts.
        """
        results = {
            "file":        pcap_file,
            "timestamp":   datetime.now().isoformat(),
            "summary":     {},
            "protocols":   {},
            "top_talkers": [],
            "dns_queries": [],
            "http_hosts":  [],
            "threats":     [],
            "artifacts":   [],
        }

        if not os.path.exists(pcap_file):
            results["error"] = "PCAP file not found"
            return results

        print(f"--- [SharkTap] Analyzing PCAP: {pcap_file} ---")

        # Packet summary
        results["summary"] = self._get_summary(pcap_file)

        # Protocol breakdown
        results["protocols"] = self._get_protocols(pcap_file)

        # Who is talking to whom
        results["top_talkers"] = self._get_top_talkers(pcap_file)

        # DNS queries made on the network
        results["dns_queries"] = self._get_dns_queries(pcap_file)

        # HTTP hosts contacted
        results["http_hosts"] = self._get_http_hosts(pcap_file)

        # Threat detection → this is the compliance-relevant output
        raw_threats = self._detect_threats(pcap_file, intensity)
        results["threats"] = raw_threats

        # Convert threats to VulnerabilityArtifacts for the compliance pipeline
        results["artifacts"] = self._threats_to_artifacts(raw_threats, pcap_file)

        self.save_data(
            {k: v for k, v in results.items() if k != "artifacts"},
            subfolder="raw",
            prefix="sharktap_"
        )

        print(f"--- [SharkTap] Analysis complete: {len(raw_threats)} threats, "
              f"{len(results['artifacts'])} compliance artifacts ---")

        return results

    # ─── tshark queries ───────────────────────────────────────────────────────
    def _run_tshark(self, args: List[str], timeout: int = 60) -> str:
        """Run a tshark command and return stdout, empty string on error."""
        try:
            r = subprocess.run(
                ["tshark"] + args,
                capture_output=True, text=True, timeout=timeout
            )
            return r.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _get_summary(self, pcap_file: str) -> Dict:
        out = self._run_tshark(["-r", pcap_file, "-q", "-z", "io,stat,0"])
        summary = {"total_packets": "unknown", "total_bytes": "unknown"}
        for line in out.split("\n"):
            if "Frames" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    summary["total_packets"] = parts[1].strip()
                    summary["total_bytes"]   = parts[2].strip()
        return summary

    def _get_protocols(self, pcap_file: str) -> Dict:
        out = self._run_tshark(["-r", pcap_file, "-q", "-z", "io,phs"])
        return {"hierarchy": out.strip()}

    def _get_top_talkers(self, pcap_file: str) -> List[Dict]:
        out = self._run_tshark(["-r", pcap_file, "-q", "-z", "conv,ip"])
        conversations = []
        for line in out.split("\n"):
            if "<->" in line:
                parts = line.split()
                if len(parts) >= 5:
                    conversations.append({
                        "src":     parts[0],
                        "dst":     parts[2],
                        "packets": parts[3],
                        "bytes":   parts[4],
                    })
        return conversations[:20]

    def _get_dns_queries(self, pcap_file: str) -> List[str]:
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "dns.flags.response==0",
            "-T", "fields",
            "-e", "dns.qry.name"
        ])
        queries = [q for q in out.strip().split("\n") if q]
        return list(set(queries))[:50]

    def _get_http_hosts(self, pcap_file: str) -> List[str]:
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "http.request",
            "-T", "fields",
            "-e", "http.host"
        ])
        hosts = [h for h in out.strip().split("\n") if h]
        return list(set(hosts))[:50]

    # ─── Threat detection ─────────────────────────────────────────────────────
    def _detect_threats(self, pcap_file: str, intensity: int = 1) -> List[Dict]:
        threats = []

        # 1. Port scan detection (many SYN to different ports from one source)
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "tcp.flags.syn==1 and tcp.flags.ack==0",
            "-T", "fields", "-e", "ip.src", "-e", "tcp.dstport"
        ])
        src_ports: Dict[str, set] = defaultdict(set)
        for line in out.strip().split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) == 2 and parts[0] and parts[1]:
                    src_ports[parts[0]].add(parts[1])
        for src, ports in src_ports.items():
            if len(ports) > 15:
                threats.append({
                    "type":     "PORT_SCAN",
                    "severity": "HIGH",
                    "source":   src,
                    "detail":   f"Scanned {len(ports)} distinct ports — possible reconnaissance",
                    "ports_sample": sorted(list(ports))[:10],
                })

        # 2. Cleartext HTTP POST (potential credential/data exposure)
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "http.request.method==POST",
            "-T", "fields", "-e", "ip.src", "-e", "http.host", "-e", "http.request.uri"
        ])
        post_hosts = set()
        for line in out.strip().split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    post_hosts.add(parts[1] if parts[1] else parts[0])
        if post_hosts:
            threats.append({
                "type":     "CLEARTEXT_HTTP_POST",
                "severity": "MEDIUM",
                "detail":   f"HTTP POST requests over cleartext on {len(post_hosts)} host(s): {', '.join(list(post_hosts)[:5])}",
            })

        # 3. Telnet sessions (cleartext remote admin — always critical)
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "tcp.port==23",
            "-T", "fields", "-e", "ip.src", "-e", "ip.dst"
        ])
        telnet_pairs = set()
        for line in out.strip().split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) == 2 and parts[0] and parts[1]:
                    telnet_pairs.add((parts[0], parts[1]))
        if telnet_pairs:
            threats.append({
                "type":     "CLEARTEXT_TELNET_SESSION",
                "severity": "CRITICAL",
                "detail":   f"Active Telnet sessions detected between {len(telnet_pairs)} host pair(s) — plaintext remote access",
                "sessions": [f"{s[0]} → {s[1]}" for s in list(telnet_pairs)[:5]],
            })

        # 4. FTP sessions (cleartext file transfer)
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "ftp",
            "-T", "fields", "-e", "ip.src", "-e", "ip.dst"
        ])
        ftp_pairs = set()
        for line in out.strip().split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) == 2 and parts[0] and parts[1]:
                    ftp_pairs.add((parts[0], parts[1]))
        if ftp_pairs:
            threats.append({
                "type":     "CLEARTEXT_FTP_SESSION",
                "severity": "HIGH",
                "detail":   f"FTP file transfers detected — plaintext protocol transmitting credentials and data",
                "sessions": [f"{s[0]} → {s[1]}" for s in list(ftp_pairs)[:5]],
            })

        # 5. DNS tunneling (unusually long hostnames = data exfiltration signal)
        out = self._run_tshark([
            "-r", pcap_file,
            "-Y", "dns.qry.name",
            "-T", "fields", "-e", "dns.qry.name"
        ])
        long_dns = [q for q in out.strip().split("\n") if len(q) > 60]
        if long_dns:
            threats.append({
                "type":     "DNS_TUNNELING_SUSPECTED",
                "severity": "HIGH",
                "detail":   f"{len(long_dns)} suspiciously long DNS queries detected — possible data exfiltration",
                "samples":  long_dns[:3],
            })

        # 6. Unencrypted database traffic (MySQL 3306 / PostgreSQL 5432 / MongoDB 27017)
        db_ports = {"3306": "MySQL", "5432": "PostgreSQL", "27017": "MongoDB"}
        for port, db_name in db_ports.items():
            out = self._run_tshark([
                "-r", pcap_file,
                "-Y", f"tcp.port=={port}",
                "-T", "fields", "-e", "ip.src"
            ])
            sources = [s for s in out.strip().split("\n") if s]
            if sources:
                threats.append({
                    "type":     "UNENCRYPTED_DATABASE",
                    "severity": "HIGH",
                    "detail":   f"Unencrypted {db_name} traffic detected on port {port} from {len(set(sources))} source(s)",
                    "database": db_name,
                    "port":     port,
                })

        # 7. Large outbound data transfers (> 1400 byte packets, possible exfiltration)
        if intensity >= 3:
            out = self._run_tshark([
                "-r", pcap_file,
                "-Y", "frame.len > 1400",
                "-T", "fields", "-e", "ip.src", "-e", "ip.dst", "-e", "frame.len"
            ])
            large_transfers = [l for l in out.strip().split("\n") if l]
            if len(large_transfers) > 50:
                threats.append({
                    "type":    "LARGE_OUTBOUND_TRANSFER",
                    "severity": "MEDIUM",
                    "detail":  f"{len(large_transfers)} large packets (>1400 bytes) detected — review for data exfiltration",
                })

        return threats

    # ─── Convert threats → VulnerabilityArtifacts ────────────────────────────
    def _threats_to_artifacts(
        self,
        threats: List[Dict],
        pcap_file: str
    ) -> List[VulnerabilityArtifact]:
        """
        Maps SharkTap threat dicts to the standard VulnerabilityArtifact
        contract so they flow through the ComplianceAgent pipeline unchanged.
        """
        artifacts = []
        pcap_name = os.path.basename(pcap_file)

        DESCRIPTION_MAP = {
            "PORT_SCAN":
                "Active Port Scan Detected from Internal Host",
            "DNS_TUNNELING_SUSPECTED":
                "DNS Tunneling Suspected — Potential Data Exfiltration",
            "CLEARTEXT_HTTP_POST":
                "Unencrypted Credential Transmission via HTTP POST",
            "CLEARTEXT_TELNET_SESSION":
                "Active Cleartext Remote Administration (Telnet)",
            "CLEARTEXT_FTP_SESSION":
                "Cleartext File Transfer Protocol (FTP) Session Detected",
            "UNENCRYPTED_DATABASE":
                "Unencrypted Database Connection Traffic Detected",
            "LARGE_OUTBOUND_TRANSFER":
                "Large Outbound Data Transfer — Possible Exfiltration",
        }

        for threat in threats:
            threat_type = threat.get("type", "UNKNOWN")
            severity    = THREAT_SEVERITY.get(threat_type, "medium")
            description = DESCRIPTION_MAP.get(threat_type, f"SharkTap: {threat_type}")
            evidence    = (
                f"[PassiveTap/{pcap_name}] {threat.get('detail', '')} "
                f"| Source: {threat.get('source', 'N/A')} "
                f"| DB: {threat.get('database', '')} "
                f"| Sessions: {'; '.join(threat.get('sessions', []))}"
            ).strip(" |")

            # Validate minimum evidence string
            if len(evidence) < 5:
                evidence = f"Detected via SharkTap passive analysis of {pcap_name}"

            try:
                artifacts.append(VulnerabilityArtifact(
                    severity=severity,
                    description=description,
                    evidence=evidence,
                ))
            except Exception as e:
                print(f"⚠️  [SharkTap] Could not create artifact for {threat_type}: {e}")

        return artifacts

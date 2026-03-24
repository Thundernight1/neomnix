#!/usr/bin/env python3
"""
SharkTap Advanced Packet Capture & Analysis
Automated inline network tap with threat detection and reporting
"""

import subprocess
import os
import json
import signal
import argparse
import threading
import time
from datetime import datetime
from typing import Optional, List, Dict
from collections import defaultdict


class SharkTapCapture:
    """SharkTap packet capture controller with threat detection"""

    def __init__(self, interface: str = None):
        self.interface = interface or self._find_sharktap_interface()
        self.capture_process = None
        self.stats = defaultdict(int)

    def _find_sharktap_interface(self) -> str:
        """Auto-detect SharkTap USB Ethernet interface"""
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'enx' in line or 'usb' in line.lower():
                    iface = line.split(':')[1].strip()
                    print(f"✅ Auto-detected SharkTap interface: {iface}")
                    return iface
        except Exception:
            pass
        # macOS fallback
        try:
            result = subprocess.run(["ifconfig"], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'en' in line and 'Ethernet' in line:
                    return line.split(':')[0]
        except Exception:
            pass
        print("⚠️  Could not auto-detect interface, defaulting to eth1")
        return "eth1"

    # ─── Capture ───────────────────────────────────────────────────
    def start_capture(self, output_file: str = None, filter_expr: str = None,
                      duration: int = None, rotate_mb: int = None) -> bool:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not output_file:
            output_file = f"sharktap_{timestamp}.pcap"

        cmd = ["sudo", "tcpdump", "-i", self.interface, "-w", output_file, "-nn"]

        if rotate_mb:
            cmd += ["-C", str(rotate_mb)]

        if filter_expr:
            cmd += filter_expr.split()

        try:
            print(f"📡 Starting capture on {self.interface}")
            print(f"   Output: {output_file}")
            if filter_expr:
                print(f"   Filter: {filter_expr}")

            self.capture_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            if duration:
                print(f"   Duration: {duration}s")
                time.sleep(duration)
                self.stop_capture()
            else:
                print("   Press Ctrl+C to stop")
                try:
                    self.capture_process.wait()
                except KeyboardInterrupt:
                    self.stop_capture()

            return True

        except Exception as e:
            print(f"❌ Capture failed: {e}")
            return False

    def stop_capture(self):
        if self.capture_process:
            self.capture_process.send_signal(signal.SIGTERM)
            self.capture_process.wait()
            print("✅ Capture stopped")
            self.capture_process = None

    # ─── Analysis ──────────────────────────────────────────────────
    def analyze_pcap(self, pcap_file: str, verbose: bool = False) -> Dict:
        """Comprehensive PCAP analysis"""
        if not os.path.exists(pcap_file):
            return {"error": "File not found"}

        results = {
            "file": pcap_file,
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "protocols": {},
            "top_talkers": [],
            "dns_queries": [],
            "http_hosts": [],
            "threats": []
        }

        # Packet count and basic stats
        r = subprocess.run(
            ["tshark", "-r", pcap_file, "-q", "-z", "io,stat,0"],
            capture_output=True, text=True
        )
        for line in r.stdout.split('\n'):
            if "Frames" in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    results["summary"]["total_packets"] = parts[1].strip()
                    results["summary"]["total_bytes"] = parts[2].strip()

        # Protocol hierarchy
        r = subprocess.run(
            ["tshark", "-r", pcap_file, "-q", "-z", "io,phs"],
            capture_output=True, text=True
        )
        results["protocols"]["hierarchy"] = r.stdout

        # Top IP talkers
        r = subprocess.run(
            ["tshark", "-r", pcap_file, "-q", "-z", "conv,ip"],
            capture_output=True, text=True
        )
        results["top_talkers"] = self._parse_conversations(r.stdout)

        # DNS queries
        r = subprocess.run(
            ["tshark", "-r", pcap_file, "-Y", "dns.flags.response==0",
             "-T", "fields", "-e", "dns.qry.name"],
            capture_output=True, text=True
        )
        results["dns_queries"] = list(set(r.stdout.strip().split('\n')))[:50]

        # HTTP hosts
        r = subprocess.run(
            ["tshark", "-r", pcap_file, "-Y", "http.request",
             "-T", "fields", "-e", "http.host"],
            capture_output=True, text=True
        )
        results["http_hosts"] = list(set(r.stdout.strip().split('\n')))[:50]

        # Threat detection
        results["threats"] = self._detect_threats(pcap_file)

        return results

    def _parse_conversations(self, output: str) -> List[Dict]:
        conversations = []
        for line in output.split('\n'):
            if '<->' in line:
                parts = line.split()
                if len(parts) >= 8:
                    conversations.append({
                        "src": parts[0],
                        "dst": parts[2],
                        "packets": parts[3],
                        "bytes": parts[4]
                    })
        return conversations[:20]

    def _detect_threats(self, pcap_file: str) -> List[Dict]:
        """Basic threat detection"""
        threats = []

        # Port scan detection (many SYN to different ports)
        r = subprocess.run(
            ["tshark", "-r", pcap_file,
             "-Y", "tcp.flags.syn==1 and tcp.flags.ack==0",
             "-T", "fields", "-e", "ip.src", "-e", "tcp.dstport"],
            capture_output=True, text=True
        )
        src_ports = defaultdict(set)
        for line in r.stdout.strip().split('\n'):
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) == 2:
                    src_ports[parts[0]].add(parts[1])

        for src, ports in src_ports.items():
            if len(ports) > 20:
                threats.append({
                    "type": "PORT_SCAN",
                    "severity": "HIGH",
                    "source": src,
                    "detail": f"Scanned {len(ports)} ports"
                })

        # Cleartext credential detection
        r = subprocess.run(
            ["tshark", "-r", pcap_file,
             "-Y", "http.request.method==POST",
             "-T", "fields", "-e", "ip.src", "-e", "http.host"],
            capture_output=True, text=True
        )
        if r.stdout.strip():
            threats.append({
                "type": "CLEARTEXT_HTTP_POST",
                "severity": "MEDIUM",
                "detail": "HTTP POST requests detected (potential credential exposure)"
            })

        # DNS tunneling (unusually long DNS queries)
        r = subprocess.run(
            ["tshark", "-r", pcap_file,
             "-Y", "dns.qry.name",
             "-T", "fields", "-e", "dns.qry.name"],
            capture_output=True, text=True
        )
        long_dns = [q for q in r.stdout.strip().split('\n') if len(q) > 60]
        if long_dns:
            threats.append({
                "type": "DNS_TUNNELING_SUSPECTED",
                "severity": "HIGH",
                "detail": f"{len(long_dns)} suspiciously long DNS queries",
                "samples": long_dns[:3]
            })

        return threats

    # ─── Real-time Monitor ─────────────────────────────────────────
    def live_monitor(self, filter_expr: str = None, alert_patterns: List[str] = None):
        """Real-time traffic monitoring with alerting"""
        cmd = ["sudo", "tcpdump", "-i", self.interface, "-l", "-nn", "-A"]
        if filter_expr:
            cmd += filter_expr.split()

        alert_patterns = alert_patterns or ["password", "passwd", "credential", "token", "secret"]

        print(f"🔍 Live monitoring on {self.interface}")
        print(f"   Alert patterns: {alert_patterns}")
        print("   Press Ctrl+C to stop\n")

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    universal_newlines=True)
            for line in proc.stdout:
                # Check for sensitive patterns
                lower = line.lower()
                for pattern in alert_patterns:
                    if pattern in lower:
                        print(f"🚨 ALERT [{pattern.upper()}]: {line.strip()[:120]}")
                        break
                else:
                    if len(line.strip()) > 10:
                        print(line.strip()[:100])

        except KeyboardInterrupt:
            proc.terminate()
            print("\n✅ Monitoring stopped")

    # ─── Export ────────────────────────────────────────────────────
    def export_http_objects(self, pcap_file: str, output_dir: str = "http_objects"):
        os.makedirs(output_dir, exist_ok=True)
        result = subprocess.run(
            ["tshark", "-r", pcap_file, "--export-objects", f"http,{output_dir}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            files = os.listdir(output_dir)
            print(f"✅ Extracted {len(files)} HTTP objects to {output_dir}/")
        else:
            print(f"⚠️  Extraction failed: {result.stderr}")

    def save_report(self, analysis: Dict, output_file: str = None):
        if not output_file:
            output_file = f"sharktap_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"📁 Report saved: {output_file}")

        # Print threat summary
        threats = analysis.get("threats", [])
        if threats:
            print(f"\n🚨 {len(threats)} THREATS DETECTED:")
            for t in threats:
                print(f"   [{t['severity']}] {t['type']}: {t.get('detail', '')}")
        else:
            print("\n✅ No threats detected")


def main():
    parser = argparse.ArgumentParser(description="SharkTap Network Capture & Analysis")
    parser.add_argument("action", choices=[
        "capture", "capture-http", "capture-dns", "analyze",
        "monitor", "monitor-creds", "extract-http"
    ])
    parser.add_argument("--iface", help="Interface name")
    parser.add_argument("--file", help="PCAP file for analysis")
    parser.add_argument("--duration", type=int, default=60, help="Capture duration")
    parser.add_argument("--output", help="Output file")
    args = parser.parse_args()

    cap = SharkTapCapture(interface=args.iface)

    if args.action == "capture":
        cap.start_capture(duration=args.duration, output_file=args.output)

    elif args.action == "capture-http":
        cap.start_capture(filter_expr="tcp port 80 or tcp port 8080",
                          duration=args.duration, output_file=args.output)

    elif args.action == "capture-dns":
        cap.start_capture(filter_expr="udp port 53",
                          duration=args.duration, output_file=args.output)

    elif args.action == "analyze":
        if not args.file:
            print("❌ --file required")
            return
        analysis = cap.analyze_pcap(args.file)
        cap.save_report(analysis, args.output)

    elif args.action == "monitor":
        cap.live_monitor()

    elif args.action == "monitor-creds":
        cap.live_monitor(
            filter_expr="tcp port 80",
            alert_patterns=["password", "passwd", "user", "login", "token", "secret", "key"]
        )

    elif args.action == "extract-http":
        if not args.file:
            print("❌ --file required")
            return
        cap.export_http_objects(args.file, args.output or "http_objects")


if __name__ == "__main__":
    main()

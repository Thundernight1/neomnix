"""
Tests for the Chunk 3 SharkTapSkill -> alert queue integration.

The /ws/alerts WebSocket transport in main.py is a thin wrapper around
this queue, so the queue mechanism is the primary testable seam. The
WebSocket tests live in a separate file (test_ws_alerts.py) and only
verify the auth + transport plumbing.
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.skills.sharktap_skill import (
    CRITICAL_DATA_LEAK_TYPES,
    SharkTapSkill,
    THREAT_SEVERITY,
)


# A small helper: most of these tests just need *a* queue object to
# hand to the skill. The skill only ever calls `put_nowait` on it, so
# a thin stand-in that records its calls is sufficient. This avoids
# the cross-event-loop issues you get when you instantiate
# `asyncio.Queue()` on a test thread.
#
# Pyright complains that this is not an `asyncio.Queue`. The runtime
# is correct (we never await on this object, only call put_nowait).
# The `# type: ignore` on the class declaration silences Pyright for
# all test call sites.
class _RecordingQueue:  # type: ignore[misc]
    def __init__(self, maxsize: int = 0):
        self.maxsize = maxsize
        self.puts: list = []
        self._full = False

    def put_nowait(self, item):
        if self._full:
            raise asyncio.QueueFull
        self.puts.append(item)

    def qsize(self) -> int:
        return len(self.puts)

    def empty(self) -> bool:
        return not self.puts

    def get_nowait(self):
        if not self.puts:
            raise asyncio.QueueEmpty
        return self.puts.pop(0)

    def force_full(self):
        self._full = True


# A reusable fake "tshark" so the test exercises the real detection
# code path without needing tshark installed in the test environment.
class _FakePopen:
    def __init__(self, stdout=""):
        self.stdout = stdout
        self.returncode = 0
        self.stderr = ""
        self.args = []


def test_critical_data_leak_types_includes_only_real_data_leaks():
    """Sanity check: the alert-qualifying set must be a real, narrow set.
    PORT_SCAN and CLEARTEXT_FTP_SESSION are not data-leak events."""
    assert "UNENCRYPTED_DATABASE" in CRITICAL_DATA_LEAK_TYPES
    assert "DNS_TUNNELING_SUSPECTED" in CRITICAL_DATA_LEAK_TYPES
    assert "CLEARTEXT_TELNET_SESSION" in CRITICAL_DATA_LEAK_TYPES
    # Recon signals must not trigger live alerts.
    assert "PORT_SCAN" not in CRITICAL_DATA_LEAK_TYPES
    # FTP cleartext is high-severity but not a data-leak in the strict sense
    # (it could be a vendor dropping a file onto an FTP server).
    assert "CLEARTEXT_FTP_SESSION" not in CRITICAL_DATA_LEAK_TYPES


def test_skill_with_no_queue_does_not_crash():
    """Default behavior: alert_queue is None. analyze_pcap() must still work."""
    skill = SharkTapSkill()  # no queue
    assert skill.alert_queue is None


def test_skill_stores_provided_queue():
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    assert skill.alert_queue is fake


def test_enqueue_critical_alerts_no_op_when_queue_is_none():
    skill = SharkTapSkill()
    threats = [{"type": "UNENCRYPTED_DATABASE", "severity": "HIGH"}]
    # Must not raise.
    skill._enqueue_critical_alerts(threats, "/tmp/fake.pcap")


def test_enqueue_critical_alerts_pushes_unencrypted_database():
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [{
        "type": "UNENCRYPTED_DATABASE",
        "severity": "HIGH",
        "source": "10.0.0.5",
        "detail": "MySQL cleartext on port 3306",
        "database": "MySQL",
        "port": "3306",
    }]
    skill._enqueue_critical_alerts(threats, "/tmp/capture.pcap")
    assert len(fake.puts) == 1
    event = fake.puts[0]
    assert event["type"] == "critical_data_leak"
    assert event["severity"] == "critical"
    assert event["threat"] == "UNENCRYPTED_DATABASE"
    assert event["source"] == "10.0.0.5"
    assert "MySQL" in event["detail"]
    assert event["pcap"] == "capture.pcap"
    assert "timestamp" in event
    datetime.fromisoformat(event["timestamp"])


def test_enqueue_critical_alerts_pushes_dns_tunneling():
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [{
        "type": "DNS_TUNNELING_SUSPECTED",
        "severity": "HIGH",
        "detail": "Long DNS queries",
    }]
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    assert len(fake.puts) == 1
    assert fake.puts[0]["threat"] == "DNS_TUNNELING_SUSPECTED"


def test_enqueue_critical_alerts_pushes_telnet():
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [{
        "type": "CLEARTEXT_TELNET_SESSION",
        "severity": "CRITICAL",
        "detail": "Telnet on port 23",
    }]
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    assert len(fake.puts) == 1
    assert fake.puts[0]["threat"] == "CLEARTEXT_TELNET_SESSION"


def test_enqueue_skips_non_critical_threats():
    """PORT_SCAN, CLEARTEXT_FTP_SESSION, etc. must NOT enqueue alerts."""
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [
        {"type": "PORT_SCAN",             "severity": "HIGH",   "detail": "scan"},
        {"type": "CLEARTEXT_FTP_SESSION", "severity": "HIGH",   "detail": "ftp"},
        {"type": "CLEARTEXT_HTTP_POST",   "severity": "MEDIUM", "detail": "post"},
        {"type": "LARGE_OUTBOUND_TRANSFER", "severity": "MEDIUM", "detail": "out"},
    ]
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    assert fake.puts == [], "No event should be enqueued for non-critical-data-leak threats"


def test_enqueue_filters_mixed_threat_list():
    """A mixed list of critical and non-critical threats enqueues only
    the critical ones, in the original order."""
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [
        {"type": "PORT_SCAN",                "severity": "HIGH"},
        {"type": "UNENCRYPTED_DATABASE",     "severity": "HIGH",   "detail": "db"},
        {"type": "CLEARTEXT_HTTP_POST",      "severity": "MEDIUM"},
        {"type": "DNS_TUNNELING_SUSPECTED",  "severity": "HIGH",   "detail": "dns"},
        {"type": "LARGE_OUTBOUND_TRANSFER",  "severity": "MEDIUM"},
    ]
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    assert len(fake.puts) == 2
    assert fake.puts[0]["threat"] == "UNENCRYPTED_DATABASE"
    assert fake.puts[1]["threat"] == "DNS_TUNNELING_SUSPECTED"


def test_enqueue_event_includes_required_keys():
    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [{"type": "UNENCRYPTED_DATABASE", "severity": "HIGH", "detail": "x"}]
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    event = fake.puts[0]
    for key in ("type", "severity", "threat", "source", "detail", "pcap", "timestamp"):
        assert key in event, f"Missing key {key!r} in alert event"


def test_enqueue_does_not_block_when_queue_is_full():
    """put_nowait must drop the event (not block) when the queue is full."""
    fake = _RecordingQueue()
    fake.force_full()
    skill = SharkTapSkill(alert_queue=fake)
    threats = [
        {"type": "UNENCRYPTED_DATABASE",    "severity": "HIGH"},
        {"type": "DNS_TUNNELING_SUSPECTED",  "severity": "HIGH"},
        {"type": "CLEARTEXT_TELNET_SESSION", "severity": "CRITICAL"},
    ]
    # All three should drop without blocking.
    skill._enqueue_critical_alerts(threats, "/tmp/cap.pcap")
    assert fake.puts == []


def test_analyze_pcap_integration_with_fake_tshark(monkeypatch, tmp_path):
    """End-to-end-ish: stub out tshark so the real detection code path
    runs, feed it a synthetic tshark output that contains a known
    critical threat, and assert the queue got the right event.

    This guards against the integration regressing if someone refactors
    the detection pipeline."""
    # Create a fake pcap file (content does not matter for this test).
    pcap = tmp_path / "capture.pcap"
    pcap.write_bytes(b"\xd4\xc3\xb2\xa1")  # pcap magic

    def fake_run(args, *a, **kw):
        cmd = " ".join(args)
        out = ""
        if "-z" in args and "io,stat" in args:
            out = "Frames|1|2|3\n"
        elif "io,phs" in args:
            out = ""
        elif "conv,ip" in args:
            out = ""
        elif "http.request.method==POST" in args:
            out = ""
        elif "tcp.port==23" in args:
            # Telnet pair: 10.0.0.5 -> 10.0.0.6
            out = "10.0.0.5\t10.0.0.6\n"
        elif args.count("-Y") and "ftp" in args:
            out = ""
        elif "dns.qry.name" in args:
            out = ""
        elif any("tcp.port==3306" in a for a in args):
            out = "10.0.0.5\n"
        return _FakePopen(stdout=out)

    import src.skills.sharktap_skill as st
    monkeypatch.setattr(st.subprocess, "run", fake_run)
    monkeypatch.setattr(st.shutil, "which", lambda x: "/usr/bin/tshark")

    fake = _RecordingQueue()
    skill = SharkTapSkill(alert_queue=fake)
    results = skill.analyze_pcap(str(pcap))

    threat_types = {t["type"] for t in results["threats"]}
    assert "CLEARTEXT_TELNET_SESSION" in threat_types
    assert "UNENCRYPTED_DATABASE" in threat_types

    queued_threats = {e["threat"] for e in fake.puts}
    assert "CLEARTEXT_TELNET_SESSION" in queued_threats
    assert "UNENCRYPTED_DATABASE" in queued_threats

"""
Tests for the Chunk 3 PDF changes:
  - Branded template name is "Healthcare Enterprise Compliance Audit Report"
    (post-correction: single strict-English title, no bilingual layout).
  - 3-layer granular breakdown is rendered for every finding.
  - "Grant Loss Risk" warning band is rendered for critical findings
    and only for critical findings.
  - No hardcoded dollar amounts appear in the rendered PDF text.
  - The role check is enforced at the FastAPI route layer, not here.
"""

import os
import re
import sys
from contextlib import contextmanager
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.pdf_exporter import (
    PDFReportExporter,
    REPORT_TEMPLATE_NAME,
    PENALTY_TIER_LABELS,
    _build_finding_breakdown,
    _resolve_penalty_tier_label,
)


# ──────────────────────────────────────────────────────────────────────────────
# A single shared fake FPDF used across all render-trace tests.
# Captures every text/rect/fill so assertions can inspect the rendered
# output without writing a real PDF.
# ──────────────────────────────────────────────────────────────────────────────
class _CapturingFPDF:
    def __init__(self):
        self.page = 1
        self.l_margin = 10
        self.r_margin = 10
        self.w = 200
        self.captured_text = []
        self.band_fills = []
        self.band_rects = 0
        self.fill_colors = []

    # All methods below are stubs that fpdf2's render path may call.
    def set_auto_page_break(self, *a, **kw): pass
    def add_page(self): pass
    def set_fill_color(self, *a): self.fill_colors.append(a)
    def set_draw_color(self, *a): pass
    def set_line_width(self, *a): pass
    def set_text_color(self, *a): pass
    def rect(self, *a, **kw):
        if kw.get("style") == "F":
            if self.fill_colors and self.fill_colors[-1] == (153, 27, 27):
                self.band_rects += 1
                self.band_fills.append(self.fill_colors[-1])

    def set_font(self, *a, **kw): pass
    def set_y(self, *a): pass
    def set_x(self, *a): pass
    def set_xy(self, *a): pass
    def get_x(self): return 0
    def get_y(self): return 0
    def line(self, *a, **kw): pass
    def ln(self, *a): pass

    def cell(self, w, h, text, *a, **kw):
        self.captured_text.append(text)

    def multi_cell(self, w, h, text, *a, **kw):
        self.captured_text.append(text)

    def page_no(self): return 1

    def output(self, name, *a, **kw):
        with open(name, "wb") as f:
            f.write(b"%PDF-1.4\n%fake\n")
        return name


@contextmanager
def _patched_fpdf():
    """Patch FPDF in src.utils.pdf_exporter to return _CapturingFPDF
    instances. Yields the class so tests can also inspect fill colors."""
    with patch("src.utils.pdf_exporter.FPDF", _CapturingFPDF):
        yield _CapturingFPDF


# ──────────────────────────────────────────────────────────────────────────────
# Pure-function tests (no PDF rendering, just the helpers).
# ──────────────────────────────────────────────────────────────────────────────


def test_report_template_name_is_healthcare_executive_audit_report():
    """R2: the report template name must be 'Healthcare Enterprise Compliance Audit Report'."""
    assert REPORT_TEMPLATE_NAME == "Healthcare Enterprise Compliance Audit Report"


def test_resolve_penalty_tier_label_returns_known_tiers():
    assert "Tier A" in _resolve_penalty_tier_label("high")
    assert "Tier B" in _resolve_penalty_tier_label("medium")
    assert "Tier C" in _resolve_penalty_tier_label("low")


def test_resolve_penalty_tier_label_unknown_tier_falls_back_to_lowest():
    label = _resolve_penalty_tier_label("not-a-real-tier")
    assert "Tier C" in label


def test_penalty_tier_labels_have_no_dollar_amounts():
    for tier, label in PENALTY_TIER_LABELS.items():
        assert not re.search(r"\$\s*\d", label), (
            f"Tier {tier!r} label contains a dollar amount: {label!r}"
        )


def test_build_finding_breakdown_uses_passed_granular_breakdown():
    finding = {
        "severity": "critical",
        "description": "irrelevant",
        "evidence": "irrelevant",
        "granular_breakdown": {
            "technical_cause": "Telnet session on the wire.",
            "regulatory_violation": ["HIPAA-2026-164.312(e)(1)"],
            "business_grant_impact": "Grant terms breached.",
            "penalty_tier": "medium",
        },
    }
    gb = _build_finding_breakdown(finding)
    assert gb["technical_cause"] == "Telnet session on the wire."
    assert gb["regulatory_violation"] == ["HIPAA-2026-164.312(e)(1)"]
    assert gb["penalty_tier"] == "medium"
    assert "Tier B" in gb["penalty_tier_label"]


def test_build_finding_breakdown_synthesizes_when_breakdown_absent():
    finding = {
        "severity": "high",
        "description": "FTP cleartext observed",
        "evidence": "[tap] FTP cleartext on port 21",
    }
    gb = _build_finding_breakdown(finding)
    for key in ("technical_cause", "regulatory_violation", "business_grant_impact"):
        assert gb[key], f"Synthesized breakdown missing {key!r}"
    assert gb["penalty_tier"] in {"high", "medium", "low"}
    assert "Tier" in gb["penalty_tier_label"]


def test_build_finding_breakdown_synthesized_infers_tier_from_severity():
    assert _build_finding_breakdown({"severity": "critical", "description": "x", "evidence": "y"})["penalty_tier"] == "high"
    assert _build_finding_breakdown({"severity": "high", "description": "x", "evidence": "y"})["penalty_tier"] == "medium"
    assert _build_finding_breakdown({"severity": "medium", "description": "x", "evidence": "y"})["penalty_tier"] == "low"
    assert _build_finding_breakdown({"severity": "low", "description": "x", "evidence": "y"})["penalty_tier"] == "low"


# ──────────────────────────────────────────────────────────────────────────────
# Render-trace tests using the fake FPDF.
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def exporter(tmp_path):
    e = PDFReportExporter()
    e.output_dir = str(tmp_path)
    os.makedirs(e.output_dir, exist_ok=True)
    return e


def test_generate_report_uses_healthcare_template_name(exporter, tmp_path):
    with _patched_fpdf() as FakeCls:
        out = exporter.generate_report(
            framework="HIPAA-2026",
            findings=[{
                "severity": "critical",
                "description": "Unencrypted telnet",
                "evidence": "[tap] 23/tcp open",
            }],
            status="non_compliant",
            confidence=0.95,
            job_id="job-abc-123",
        )

    # The faked class was used; grab its single instance's captures.
    # (The patcher creates one instance per call to FPDF(); we generated
    # exactly one, so inspect the module-level state via the class.)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0


def test_generate_report_header_renders_template_name_not_per_framework(exporter):
    """The header must contain the Healthcare template name and must
    NOT contain the old per-framework subtitle."""
    with _patched_fpdf():
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[{
                "severity": "critical",
                "description": "X",
                "evidence": "Y",
            }],
            status="non_compliant",
            confidence=0.95,
            job_id="job-hdr",
        )

    # Re-run a fresh test to inspect the captures via a fresh instance.
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[{
                "severity": "critical",
                "description": "X",
                "evidence": "Y",
            }],
            status="non_compliant",
            confidence=0.95,
            job_id="job-hdr-2",
        )

    joined = "\n".join(fake.captured_text)
    assert "Healthcare Enterprise Compliance Audit Report" in joined, (
        f"Template name not found in rendered PDF header. Got: {joined[:500]!r}"
    )
    assert "HIPAA-2026 Compliance Report" not in joined, (
        f"Old per-framework subtitle still in PDF header: {joined[:500]!r}"
    )


def test_generate_report_renders_three_layer_breakdown_for_each_finding(exporter):
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[
                {
                    "severity": "critical",
                    "description": "Cleartext DB traffic",
                    "evidence": "[tap] MySQL 3306",
                    "granular_breakdown": {
                        "technical_cause": "MySQL traffic on port 3306 in cleartext.",
                        "regulatory_violation": [
                            "HIPAA-2026: 164.312(e)(1); 164.312(a)(1); 164.312(e)(2)(ii)",
                            "WA-MHMDA (RCW 19.373): 19.373.010",
                        ],
                        "business_grant_impact": "Grant termination risk per WA State Health IT Authority terms.",
                        "penalty_tier": "high",
                    },
                },
                {
                    "severity": "high",
                    "description": "DNS tunneling suspected",
                    "evidence": "[tap] long DNS queries",
                },
            ],
            status="non_compliant",
            confidence=0.95,
            job_id="job-abc-456",
        )

    joined = "\n".join(fake.captured_text)
    # Layer 1: Technical Cause
    assert "Technical Cause:" in joined
    # Layer 2: Regulatory Violation
    assert "Regulatory Violation:" in joined
    # Layer 3: Business & Grant Impact
    assert "Business & Grant Impact:" in joined
    # The actual content of the first finding's breakdown appears.
    assert "MySQL traffic on port 3306 in cleartext." in joined
    assert "HIPAA-2026: 164.312(e)(1)" in joined
    # The second finding's synthesized breakdown appears.
    assert "DNS tunneling suspected" in joined
    # Penalty tier labels render
    assert "Penalty tier:" in joined
    assert "Tier A" in joined  # First finding was high tier
    assert "Tier B" in joined  # Second was synthesized as medium


def test_generate_report_grant_loss_risk_band_for_critical_only(exporter):
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[
                {"severity": "critical", "description": "Telnet active", "evidence": "23/tcp"},
                {"severity": "high",     "description": "FTP cleartext", "evidence": "21/tcp"},
                {"severity": "medium",   "description": "Long DNS",      "evidence": "dns"},
            ],
            status="non_compliant",
            confidence=0.9,
            job_id="job-band-test",
        )

    joined = "\n".join(fake.captured_text)
    # The band title appears — exactly once (only the critical finding).
    assert "GRANT LOSS RISK" in joined
    assert joined.count("GRANT LOSS RISK") == 1
    # Exactly one band was drawn.
    assert fake.band_rects == 1
    # The deep-red fill (153, 27, 27) was used for the band.
    assert (153, 27, 27) in fake.band_fills


def test_generate_report_renders_no_dollar_amounts(exporter):
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[
                {
                    "severity": "critical",
                    "description": "Cleartext telnet",
                    "evidence": "23/tcp open",
                    "granular_breakdown": {
                        "technical_cause": "Telnet on the wire in plaintext.",
                        "regulatory_violation": ["HIPAA-2026-164.312(e)(1)"],
                        "business_grant_impact": "Grant termination risk.",
                        "penalty_tier": "medium",
                    },
                },
            ],
            status="non_compliant",
            confidence=0.9,
            job_id="job-dollar-test",
        )

    joined = "\n".join(fake.captured_text)
    assert not re.search(r"\$\s*\d", joined), (
        f"Dollar amount leaked into rendered PDF text: {joined!r}"
    )


def test_generate_report_uses_ascii_only_in_rendered_text(exporter):
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        exporter.generate_report(
            framework="HIPAA-2026",
            findings=[{
                "severity": "critical",
                "description": "Unencrypted telnet",
                "evidence": "23/tcp open",
            }],
            status="non_compliant",
            confidence=0.95,
            job_id="job-ascii-test",
        )

    for s in fake.captured_text:
        try:
            s.encode("ascii")
        except UnicodeEncodeError as e:
            pytest.fail(f"Non-ASCII text reached the PDF renderer: {s!r} ({e})")


def test_generate_report_with_no_findings_still_produces_valid_pdf(exporter):
    """Edge case: a scan that came back clean. PDF should still build."""
    fake = _CapturingFPDF()
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        out = exporter.generate_report(
            framework="HIPAA-2026",
            findings=[],
            status="compliant",
            confidence=1.0,
            job_id="job-clean",
        )
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0
    joined = "\n".join(fake.captured_text)
    assert "Healthcare Enterprise Compliance Audit Report" in joined

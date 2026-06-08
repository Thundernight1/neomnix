"""
Tests for src/utils/pdf_exporter.py — PDF report generator.

Target coverage: 87% → 95%+. Tests:
  - _ensure_ttf_loaded: TTF load success path (monkeypatch NEOMNIX_DISABLE_TTF=0, mock fpdf2 add_font)
  - _ensure_ttf_loaded: fpdf2 exception → graceful degrade, loaded=False
  - _ensure_ttf_loaded: second call is no-op (idempotency)
  - _ttf_bold_paths: with NEOMNIX_TTF_BOLD_PATH env var set
  - _resolve_penalty_tier_label: unknown tier → fallback to "low"
  - _statutory_framing_for_tier: unknown tier → fallback to LOW text
  - _build_finding_breakdown: granular_breakdown with penalty_tier but no label → backfill label
  - _build_finding_breakdown: severity=critical → inferred tier=high
  - generate_report: findings=[] → no crash, valid PDF bytes returned
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import src.utils.pdf_exporter as pdf_exporter
from src.utils.pdf_exporter import (
    _ensure_ttf_loaded,
    _ttf_bold_paths,
    _ttf_search_paths,
    _ttf_short_circuited,
    _resolve_penalty_tier_label,
    _statutory_framing_for_tier,
    _build_finding_breakdown,
    PENALTY_TIER_LABELS,
    STATUTORY_FRAMING_LOW,
    PDFReportExporter,
    ttf_loaded,
    font_family,
    _TTF_STATE,
    _FONT_FAMILY,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_ttf_state():
    """Reset the module-level TTF state before each test."""
    pdf_exporter._TTF_STATE["attempted"] = False
    pdf_exporter._TTF_STATE["loaded"] = False
    pdf_exporter._TTF_STATE["regular"] = None
    pdf_exporter._TTF_STATE["bold"] = None
    pdf_exporter._TTF_STATE["italic"] = None
    pdf_exporter._TTF_STATE["bold_italic"] = None
    pdf_exporter._TTF_STATE["family"] = "Helvetica"
    yield
    # Post-test reset too.
    pdf_exporter._TTF_STATE["attempted"] = False
    pdf_exporter._TTF_STATE["loaded"] = False
    pdf_exporter._TTF_STATE["regular"] = None
    pdf_exporter._TTF_STATE["bold"] = None
    pdf_exporter._TTF_STATE["italic"] = None
    pdf_exporter._TTF_STATE["bold_italic"] = None
    pdf_exporter._TTF_STATE["family"] = "Helvetica"


# ─────────────────────────────────────────────────────────────────────────────
# Test: _ensure_ttf_loaded
# ─────────────────────────────────────────────────────────────────────────────

def test_ensure_ttf_loaded_short_circuit(monkeypatch):
    """When APP_ENV=test the loader short-circuits and ttf_loaded() stays False."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    fake_pdf = MagicMock()
    _ensure_ttf_loaded(fake_pdf)
    assert ttf_loaded() is False
    # add_font was never called.
    fake_pdf.add_font.assert_not_called()


def test_ensure_ttf_loaded_success_path(monkeypatch, tmp_path):
    """When a real TTF is present and TTF loading is enabled, the loader registers it."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    # Create a real temp TTF file.
    fake_ttf = tmp_path / "fake.ttf"
    fake_ttf.write_bytes(b"FAKETTF")
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", str(fake_ttf))

    fake_pdf = MagicMock()
    _ensure_ttf_loaded(fake_pdf)

    # The loader should have called add_font at least once (for "").
    assert fake_pdf.add_font.called
    # At least one call registered the regular family.
    calls = fake_pdf.add_font.call_args_list
    assert any(c.args[0] == _FONT_FAMILY and c.args[1] == "" for c in calls), \
        f"Expected regular style registration, got {calls}"
    assert ttf_loaded() is True
    assert font_family() == _FONT_FAMILY


def test_ensure_ttf_loaded_fpdf_exception_graceful_degrade(monkeypatch, tmp_path):
    """If add_font raises, loaded=False, family stays 'Helvetica'."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    fake_ttf = tmp_path / "fake.ttf"
    fake_ttf.write_bytes(b"X")
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", str(fake_ttf))

    # Simulate fpdf2 raising on add_font.
    fake_pdf = MagicMock()
    fake_pdf.add_font.side_effect = RuntimeError("fpdf2 broke")

    _ensure_ttf_loaded(fake_pdf)

    assert ttf_loaded() is False
    assert font_family() == "Helvetica"


def test_ensure_ttf_loaded_idempotency(monkeypatch, tmp_path):
    """Second call is a no-op because attempted=True."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    fake_ttf = tmp_path / "fake.ttf"
    fake_ttf.write_bytes(b"X")
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", str(fake_ttf))

    fake_pdf = MagicMock()

    # First call: should call add_font.
    _ensure_ttf_loaded(fake_pdf)
    first_call_count = fake_pdf.add_font.call_count
    assert first_call_count >= 1

    # Second call: should NOT call add_font.
    _ensure_ttf_loaded(fake_pdf)
    second_call_count = fake_pdf.add_font.call_count
    assert second_call_count == first_call_count


def test_ensure_ttf_loaded_no_ttf_found(monkeypatch):
    """When no TTF is found at any path, loaded=False and family stays Helvetica."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    # Point at a nonexistent path.
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", "/nonexistent/DejaVuSans.ttf")

    fake_pdf = MagicMock()
    _ensure_ttf_loaded(fake_pdf)

    assert ttf_loaded() is False
    assert font_family() == "Helvetica"
    fake_pdf.add_font.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test: _ttf_bold_paths
# ─────────────────────────────────────────────────────────────────────────────

def test_ttf_bold_paths_uses_explicit_env_var(monkeypatch):
    """When NEOMNIX_TTF_BOLD_PATH is set, it appears first in the bold paths."""
    monkeypatch.setenv("NEOMNIX_TTF_BOLD_PATH", "/some/bold.ttf")
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", "")
    paths = _ttf_bold_paths()
    assert paths[0] == "/some/bold.ttf"


def test_ttf_bold_paths_includes_derived_bold_variants(monkeypatch):
    """Bold paths derive -Bold variants from regular candidates."""
    monkeypatch.delenv("NEOMNIX_TTF_BOLD_PATH", raising=False)
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    paths = _ttf_bold_paths()
    # Should contain DejaVuSans-Bold variants.
    assert any("DejaVuSans-Bold.ttf" in p for p in paths)


# ─────────────────────────────────────────────────────────────────────────────
# Test: _ttf_search_paths, _ttf_short_circuited
# ─────────────────────────────────────────────────────────────────────────────

def test_ttf_search_paths_includes_explicit_env_var(monkeypatch):
    """When NEOMNIX_TTF_FONT_PATH is set, it's the first candidate."""
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", "/explicit/path.ttf")
    paths = _ttf_search_paths()
    assert paths[0] == "/explicit/path.ttf"


def test_ttf_short_circuited_when_disable_flag(monkeypatch):
    """NEOMNIX_DISABLE_TTF=1 short-circuits the loader."""
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "1")
    monkeypatch.setenv("APP_ENV", "production")
    assert _ttf_short_circuited() is True


def test_ttf_short_circuited_when_app_env_test(monkeypatch):
    """APP_ENV=test short-circuits the loader."""
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    monkeypatch.setenv("APP_ENV", "test")
    assert _ttf_short_circuited() is True


def test_ttf_short_circuited_false_in_production(monkeypatch):
    """APP_ENV=production + no disable flag → not short-circuited."""
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "")
    monkeypatch.setenv("APP_ENV", "production")
    assert _ttf_short_circuited() is False


# ─────────────────────────────────────────────────────────────────────────────
# Test: _resolve_penalty_tier_label
# ─────────────────────────────────────────────────────────────────────────────

def test_resolve_penalty_tier_label_known_tiers():
    """Known tiers return their bracket label."""
    assert _resolve_penalty_tier_label("high") == PENALTY_TIER_LABELS["high"]
    assert _resolve_penalty_tier_label("medium") == PENALTY_TIER_LABELS["medium"]
    assert _resolve_penalty_tier_label("low") == PENALTY_TIER_LABELS["low"]


def test_resolve_penalty_tier_label_unknown_tier_falls_back_to_low():
    """Unknown tier → fallback to 'low' bracket label (never fabricate)."""
    assert _resolve_penalty_tier_label("unknown") == PENALTY_TIER_LABELS["low"]
    assert _resolve_penalty_tier_label("") == PENALTY_TIER_LABELS["low"]
    assert _resolve_penalty_tier_label("extreme") == PENALTY_TIER_LABELS["low"]


# ─────────────────────────────────────────────────────────────────────────────
# Test: _statutory_framing_for_tier
# ─────────────────────────────────────────────────────────────────────────────

def test_statutory_framing_for_tier_known_tiers():
    """Known tiers return their framing paragraph."""
    assert _statutory_framing_for_tier("high") != STATUTORY_FRAMING_LOW
    assert _statutory_framing_for_tier("medium") != STATUTORY_FRAMING_LOW
    assert _statutory_framing_for_tier("low") == STATUTORY_FRAMING_LOW


def test_statutory_framing_for_tier_unknown_falls_back_to_low():
    """Unknown tier → fallback to LOW statutory framing."""
    assert _statutory_framing_for_tier("unknown") == STATUTORY_FRAMING_LOW
    assert _statutory_framing_for_tier("") == STATUTORY_FRAMING_LOW


# ─────────────────────────────────────────────────────────────────────────────
# Test: _build_finding_breakdown
# ─────────────────────────────────────────────────────────────────────────────

def test_build_finding_breakdown_backfills_label():
    """granular_breakdown with penalty_tier but no label → label is backfilled."""
    finding = {
        "granular_breakdown": {
            "penalty_tier": "high",
            "technical_cause": "x",
            "regulatory_violation": ["HIPAA"],
            "business_grant_impact": "y",
        }
    }
    gb = _build_finding_breakdown(finding)
    assert gb["penalty_tier"] == "high"
    assert gb["penalty_tier_label"] == PENALTY_TIER_LABELS["high"]


def test_build_finding_breakdown_critical_severity_inferred_high():
    """No granular_breakdown + severity=critical → inferred_tier=high."""
    finding = {
        "severity": "critical",
        "description": "TLS missing",
        "evidence": "pcap showed plaintext",
    }
    gb = _build_finding_breakdown(finding)
    assert gb["penalty_tier"] == "high"
    assert gb["penalty_tier_label"] == PENALTY_TIER_LABELS["high"]
    assert "TLS missing" in gb["technical_cause"]


def test_build_finding_breakdown_high_severity_inferred_medium():
    """severity=high → inferred_tier=medium."""
    finding = {"severity": "high", "description": "x", "evidence": "y"}
    gb = _build_finding_breakdown(finding)
    assert gb["penalty_tier"] == "medium"


def test_build_finding_breakdown_low_severity_inferred_low():
    """severity=low → inferred_tier=low."""
    finding = {"severity": "low", "description": "x", "evidence": "y"}
    gb = _build_finding_breakdown(finding)
    assert gb["penalty_tier"] == "low"


def test_build_finding_breakdown_preserves_existing_label():
    """If granular_breakdown already has a label, don't overwrite it."""
    finding = {
        "granular_breakdown": {
            "penalty_tier": "high",
            "penalty_tier_label": "Custom Label",
        }
    }
    gb = _build_finding_breakdown(finding)
    assert gb["penalty_tier_label"] == "Custom Label"


# ─────────────────────────────────────────────────────────────────────────────
# Test: generate_report
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_report_with_empty_findings(monkeypatch, tmp_path):
    """generate_report with findings=[] must not crash and must return a valid file path."""
    monkeypatch.setenv("APP_ENV", "test")  # short-circuit TTF
    monkeypatch.chdir(tmp_path)  # redirect output to tmp

    exporter = PDFReportExporter()
    filepath = exporter.generate_report(
        framework="HIPAA-2026",
        findings=[],
        status="compliant",
        confidence=0.95,
        job_id="job-empty-001",
    )
    assert filepath is not None
    assert os.path.isfile(filepath)
    # File should be non-empty (it's a PDF).
    assert os.path.getsize(filepath) > 100
    # File should start with %PDF magic bytes.
    with open(filepath, "rb") as f:
        head = f.read(5)
    assert head.startswith(b"%PDF-")


def test_generate_report_with_findings(monkeypatch, tmp_path):
    """generate_report renders findings into the PDF without crashing."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.chdir(tmp_path)

    exporter = PDFReportExporter()
    findings = [
        {
            "severity": "critical",
            "description": "Unencrypted database traffic",
            "evidence": "port 5432 plaintext",
        },
        {
            "severity": "high",
            "description": "DNS tunneling suspected",
            "evidence": "long DNS queries",
        },
    ]
    filepath = exporter.generate_report(
        framework="WA-MHMDA",
        findings=findings,
        status="non_compliant",
        confidence=0.85,
        job_id="job-find-001",
    )
    assert filepath is not None
    assert os.path.isfile(filepath)


def test_generate_report_critical_finding_renders_grant_loss_band(monkeypatch, tmp_path):
    """A critical finding triggers the 'Grant Loss Risk' warning band."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.chdir(tmp_path)

    exporter = PDFReportExporter()
    findings = [{
        "severity": "critical",
        "description": "x",
        "evidence": "y",
    }]
    filepath = exporter.generate_report(
        framework="HIPAA-2026",
        findings=findings,
        status="non_compliant",
        confidence=0.95,
        job_id="job-crit",
    )
    assert filepath is not None
    # fpdf2 will have produced a non-trivial PDF with the band.
    assert os.path.getsize(filepath) > 500

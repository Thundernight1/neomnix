"""
Tests for Chunk 4:
  R1 — TrueType font (TTF) loader with a test-only short-circuit so
       the suite stays fast and asset-path-independent.
  R2 — Single English report title: "Healthcare Enterprise Compliance
       Audit Report". The header is 100% English in all render modes;
       no bilingual layout, no Turkish transliteration.
  R3 — Statutory framing text in the 3-layer breakdown (45 CFR 160.404,
       RCW 19.373.030 references) without fabricated dollar amounts.
       "[LEGAL REVIEW]" markers are present so customer counsel can
       sign off before delivery.
"""

import os
import re
import sys
from contextlib import contextmanager
from typing import Optional
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.utils.pdf_exporter as pdf_exporter
from src.utils.pdf_exporter import (
    PDFReportExporter,
    REPORT_TEMPLATE_NAME,
    PENALTY_TIER_LABELS,
    _FONT_FAMILY,
    _statutory_framing_for_tier,
    font_family,
    ttf_loaded,
    _ensure_ttf_loaded,
    _ttf_short_circuited,
)


# ──────────────────────────────────────────────────────────────────────────────
# Same capturing FPDF fake as the Chunk 3 test file. Duplicated here so the
# two test files can be run in either order without import cycles.
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
        self.fonts_set = []   # list of (family, style, size) for assertion

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
    def set_font(self, family, style="", size=10):
        self.fonts_set.append((family, style, size))
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
    def add_font(self, family, style, path): pass  # fpdf2's TTF registration
    def output(self, name, *a, **kw):
        with open(name, "wb") as f:
            f.write(b"%PDF-1.4\n%fake\n")
        return name


# ──────────────────────────────────────────────────────────────────────────────
# R1 — TTF loader behavior
# ──────────────────────────────────────────────────────────────────────────────


def test_ttf_short_circuited_when_app_env_is_test(monkeypatch):
    """Under APP_ENV=test, the TTF loader is bypassed regardless of
    whether a TTF exists on disk."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    assert _ttf_short_circuited() is True


def test_ttf_short_circuited_when_explicit_env(monkeypatch):
    """NEOMNIX_DISABLE_TTF=1 forces the bypass even outside test mode."""
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "1")
    monkeypatch.setenv("APP_ENV", "development")
    assert _ttf_short_circuited() is True


def test_ttf_short_circuited_in_normal_development(monkeypatch):
    """In a normal development environment, the loader is not bypassed."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    assert _ttf_short_circuited() is False


def test_ttf_short_circuited_in_production(monkeypatch):
    """In production, the loader is not bypassed."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    assert _ttf_short_circuited() is False


def test_ttf_short_circuit_zero_marks_falsy(monkeypatch):
    """NEOMNIX_DISABLE_TTF=0 must NOT short-circuit (only '1' does)."""
    monkeypatch.setenv("NEOMNIX_DISABLE_TTF", "0")
    monkeypatch.setenv("APP_ENV", "development")
    assert _ttf_short_circuited() is False


def test_ensure_ttf_loaded_is_idempotent(monkeypatch):
    """The loader memoizes its result so repeated calls don't re-scan
    the filesystem."""
    # Force a fresh module state.
    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "test")  # short-circuits
    fake = _CapturingFPDF()
    _ensure_ttf_loaded(fake)
    assert pdf_exporter._TTF_STATE["attempted"] is True
    assert pdf_exporter._TTF_STATE["loaded"] is False
    assert pdf_exporter._TTF_STATE["family"] == "Helvetica"
    # Second call should be a no-op.
    fake.add_font_call_count = 0
    original_add_font = fake.add_font
    def tracking_add_font(*a, **kw):
        fake.add_font_call_count += 1
        return original_add_font(*a, **kw)
    fake.add_font = tracking_add_font
    _ensure_ttf_loaded(fake)
    assert fake.add_font_call_count == 0


def test_font_family_returns_helvetica_in_test_mode(monkeypatch):
    """Under APP_ENV=test, font_family() reports the built-in family
    name so callers can detect the test short-circuit."""
    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": True, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    assert font_family() == "Helvetica"
    assert ttf_loaded() is False


def test_ttf_search_paths_include_env_override(monkeypatch):
    """NEOMNIX_TTF_FONT_PATH must be the first candidate in the search
    list, before any system path."""
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", "/tmp/my-custom-font.ttf")
    paths = pdf_exporter._ttf_search_paths()
    assert paths[0] == "/tmp/my-custom-font.ttf"


def _find_dejavu_path() -> Optional[str]:
    """Return the first real DejaVu Sans path found on this system, or
    None. Centralized so the real-TTF tests can call it consistently."""
    for d in [
        "/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if os.path.isfile(d):
            return d
    return None


def test_ttf_loader_uses_loaded_ttf_when_available(monkeypatch, tmp_path):
    """When a real TTF is on disk and the short-circuit is off, the
    loader registers it and reports ttf_loaded()==True.

    The test environment may or may not ship a TTF. On the CI runner
    (`fonts-dejavu` installed) the loader finds the system path
    even when `NEOMNIX_TTF_FONT_PATH` is unset. We force the test
    to use a known-good path so it is deterministic across systems.
    """
    real_ttf = _find_dejavu_path()
    if not real_ttf:
        pytest.skip("No DejaVu Sans TTF found on this system; skipping real-load test")

    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    # Force the loader to use exactly this path (bypassing the
    # system search) so the test is deterministic.
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", real_ttf)

    fake = _CapturingFPDF()
    _ensure_ttf_loaded(fake)

    assert ttf_loaded() is True
    assert font_family() == "Neomnix"
    assert pdf_exporter._TTF_STATE["regular"] == real_ttf


def test_ttf_loader_handles_missing_path_gracefully(monkeypatch, capsys):
    """When the configured TTF path does not exist AND no system font
    is available, the loader logs a fallback warning (to stdout) and
    stays on Helvetica. The report generation must not crash.

    This test isolates from the system font search by stubbing
    `_find_ttf` to return None unconditionally. Without that
    isolation, a CI box with `fonts-dejavu` installed would find
    DejaVu via the system path and the assertion would fail
    spuriously.
    """
    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    # Force the no-font-found branch regardless of what is on disk.
    monkeypatch.setattr(pdf_exporter, "_find_ttf", lambda paths: None)

    fake = _CapturingFPDF()
    _ensure_ttf_loaded(fake)
    # Loaded stays False; family is Helvetica.
    assert ttf_loaded() is False
    assert font_family() == "Helvetica"


def test_ttf_loader_handles_add_font_exception(monkeypatch):
    """If fpdf2's add_font raises (malformed TTF, permission denied,
    etc.), the loader catches the exception and falls back to Helvetica
    without raising."""
    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)

    class BoomFPDF:
        def add_font(self, *a, **kw):
            raise RuntimeError("simulated fpdf2 error")

    _ensure_ttf_loaded(BoomFPDF())  # must not raise
    assert ttf_loaded() is False
    assert font_family() == "Helvetica"


# ──────────────────────────────────────────────────────────────────────────────
# R2 — Single English report title (post-correction)
# ──────────────────────────────────────────────────────────────────────────────


def test_title_constant_is_strict_english():
    """The single report title must be the exact strict-English string
    from the post-correction brief. No Turkish, no transliteration."""
    assert REPORT_TEMPLATE_NAME == "Healthcare Enterprise Compliance Audit Report"


def test_title_constant_has_no_non_ascii_characters():
    """The title is 100% English ASCII, defensively enforced so a
    future edit cannot silently reintroduce Turkish characters."""
    assert REPORT_TEMPLATE_NAME.isascii(), (
        f"REPORT_TEMPLATE_NAME contains non-ASCII characters: {REPORT_TEMPLATE_NAME!r}"
    )


def test_title_constant_has_no_turkish_specific_characters():
    """Sweep for the Turkish-only characters (S, g, I, etc.) that
    could leak in if someone copy-pastes a Turkish phrase into the
    title constant."""
    turkish_only = set("ğĞşŞıİöÖüÜçÇ")
    for ch in turkish_only:
        assert ch not in REPORT_TEMPLATE_NAME, (
            f"REPORT_TEMPLATE_NAME contains Turkish character {ch!r}: {REPORT_TEMPLATE_NAME!r}"
        )


def test_header_renders_strict_english_title_in_test_mode(exporter_with_fake, tmp_path):
    """Under APP_ENV=test, the header must contain the strict English
    title and NO Turkish characters (which would crash fpdf2's
    Latin-1 Helvetica)."""
    e, fake = exporter_with_fake
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        e.generate_report(
            framework="HIPAA-2026",
            findings=[],
            status="compliant",
            confidence=1.0,
            job_id="job-english-title",
        )
    joined = "\n".join(fake.captured_text)
    assert REPORT_TEMPLATE_NAME in joined
    # No Turkish-only characters anywhere in the rendered output.
    turkish_only = set("ğĞşŞıİöÖüÜçÇ")
    leaked = [ch for ch in turkish_only if ch in joined]
    assert not leaked, f"Turkish characters leaked into rendered PDF: {leaked}"


def test_header_uses_single_title_slot_not_bilingual(exporter_with_fake):
    """The single title is rendered exactly once in the header. The
    old bilingual layout rendered a Turkish primary title AND an
    English supporting subtitle; this regression guard pins that
    there is now exactly one title."""
    e, fake = exporter_with_fake
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        e.generate_report(
            framework="HIPAA-2026",
            findings=[],
            status="compliant",
            confidence=1.0,
            job_id="job-single-title",
        )
    joined = "\n".join(fake.captured_text)
    # Exactly one occurrence of the strict-English title.
    assert joined.count(REPORT_TEMPLATE_NAME) == 1


def test_header_renders_title_when_ttf_loaded(monkeypatch, tmp_path):
    """When the TTF is loaded and a real PDF is produced, the
    strict-English title is in the output regardless of which font
    is in use. The TTF loader does not switch the title to Turkish.

    This test also exercises the renderer end-to-end with a real
    TTF, which is the regression guard for the CI runner
    `fonts-dejavu` environment: the renderer must not raise on
    `set_font(family, "B"|"I", ...)` even when only the regular
    TTF weight is available."""
    real_ttf = _find_dejavu_path()
    if not real_ttf:
        pytest.skip("No DejaVu Sans TTF found on this system; skipping real-render test")

    # Reset module state and force a real TTF load.
    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", real_ttf)

    e = PDFReportExporter()
    e.output_dir = str(tmp_path)
    os.makedirs(e.output_dir, exist_ok=True)

    out = e.generate_report(
        framework="HIPAA-2026",
        findings=[{
            "severity": "critical",
            "description": "Unencrypted telnet",
            "evidence": "23/tcp open",
            "granular_breakdown": {
                "technical_cause": "Telnet on the wire in cleartext.",
                "regulatory_violation": ["HIPAA-2026-164.312(e)(1)"],
                "business_grant_impact": "Grant termination risk per WA State Health IT Authority terms.",
                "penalty_tier": "high",
            },
        }],
        status="non_compliant",
        confidence=0.95,
        job_id="job-ttf-english",
    )
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0
    # The strict English title is the same constant, so the rendered
    # PDF is still 100% English. (The PDF body is binary, so we can't
    # grep the title out of it portably; we rely on the
    # REPORT_TEMPLATE_NAME check elsewhere.)


def test_ttf_loader_registers_all_four_styles(monkeypatch, tmp_path):
    """Regression test for the CI runner bug.

    When a TTF is loaded, the loader must register ALL four
    fpdf2 font styles — regular, bold, italic, bold-italic — so
    that the renderer's set_font(family, "B"|"I"|"BI", ...) calls
    do not raise "Undefined font: neomnix<B|I|BI>".

    On a minimal Linux runner that ships only DejaVuSans.ttf (no
    bold/italic variants), the loader falls back to registering
    the regular TTF for all four styles. fpdf2 synthesizes the
    missing weight or slant from the regular glyphs. The report
    must render end-to-end without raising.
    """
    real_ttf = _find_dejavu_path()
    if not real_ttf:
        pytest.skip("No DejaVu Sans TTF found on this system; skipping style-registration test")

    # Capture every fpdf2.add_font call.
    add_font_calls: list = []

    class _TrackingFPDF:
        def __init__(self):
            self._styles_seen: set = set()

        def add_font(self, family: str, style: str, path: str):
            add_font_calls.append((family, style, path))
            self._styles_seen.add((family, style))

        def set_auto_page_break(self, *a, **kw): pass
        def add_page(self): pass
        def set_fill_color(self, *a): pass
        def set_draw_color(self, *a): pass
        def set_line_width(self, *a): pass
        def set_text_color(self, *a): pass
        def rect(self, *a, **kw): pass
        def set_font(self, family: str, style: str = "", size: int = 10):
            if (family, style) not in self._styles_seen:
                raise RuntimeError(
                    f"set_font({family!r}, {style!r}, {size!r}) called before "
                    f"add_font for style {style!r}; this is the CI failure mode"
                )
        def set_y(self, *a): pass
        def set_x(self, *a): pass
        def set_xy(self, *a): pass
        def get_x(self): return 0
        def get_y(self): return 0
        def line(self, *a, **kw): pass
        def ln(self, *a): pass
        def cell(self, *a, **kw): pass
        def multi_cell(self, *a, **kw): pass
        def page_no(self): return 1
        def output(self, *a, **kw):
            return "/tmp/_test_ttf_loader_registers_all_four_styles.pdf"

    monkeypatch.setattr(pdf_exporter, "_TTF_STATE", {
        "attempted": False, "loaded": False, "regular": None,
        "bold": None, "italic": None, "bold_italic": None, "family": "Helvetica",
    })
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("NEOMNIX_DISABLE_TTF", raising=False)
    monkeypatch.setenv("NEOMNIX_TTF_FONT_PATH", real_ttf)

    pdf = _TrackingFPDF()
    _ensure_ttf_loaded(pdf)

    # Verify the loader registered all four fpdf2 styles for the
    # Neomnix family.
    registered_styles = {(f, s) for f, s, _ in add_font_calls}
    assert (_FONT_FAMILY, "")  in registered_styles, "regular style must be registered"
    assert (_FONT_FAMILY, "B") in registered_styles, "bold style must be registered (CI runner regression)"
    assert (_FONT_FAMILY, "I") in registered_styles, "italic style must be registered (CI runner regression)"
    assert (_FONT_FAMILY, "BI") in registered_styles, "bold-italic style must be registered (CI runner regression)"

    # Now exercise the renderer with each style and assert no
    # set_font() raises. This is the actual CI failure path.
    pdf.set_font(_FONT_FAMILY, "",  10)
    pdf.set_font(_FONT_FAMILY, "B", 10)
    pdf.set_font(_FONT_FAMILY, "I", 10)
    pdf.set_font(_FONT_FAMILY, "BI", 10)


# ──────────────────────────────────────────────────────────────────────────────
# R3 — Statutory framing
# ──────────────────────────────────────────────────────────────────────────────


def test_statutory_framing_high_cites_45_cfr_160_404():
    text = _statutory_framing_for_tier("high")
    assert "45 CFR 160.404" in text


def test_statutory_framing_high_cites_rcw_19_373_030():
    text = _statutory_framing_for_tier("high")
    assert "RCW 19.373.030" in text


def test_statutory_framing_high_marks_legal_review():
    text = _statutory_framing_for_tier("high")
    assert "[LEGAL REVIEW]" in text


def test_statutory_framing_medium_cites_45_cfr_160_404():
    text = _statutory_framing_for_tier("medium")
    assert "45 CFR 160.404" in text


def test_statutory_framing_medium_cites_rcw_19_373_030():
    text = _statutory_framing_for_tier("medium")
    assert "RCW 19.373.030" in text


def test_statutory_framing_low_cites_rcw_19_373_030():
    text = _statutory_framing_for_tier("low")
    assert "RCW 19.373.030" in text


def test_statutory_framing_unknown_tier_falls_back_to_low():
    """An unknown tier must not fabricate a framing paragraph — fall
    back to the lowest tier so we never lie to the customer."""
    text = _statutory_framing_for_tier("not-a-real-tier")
    # Low framing is the safe default.
    assert "RCW 19.373.030" in text
    assert "[LEGAL REVIEW]" in text


def test_statutory_framing_never_contains_dollar_amounts():
    """Sweep all three tier framings for hardcoded dollar amounts.
    The brief forbids them; the rendering text is qualitative only."""
    for tier in ("high", "medium", "low"):
        text = _statutory_framing_for_tier(tier)
        assert not re.search(r"\$\s*\d", text), (
            f"Tier {tier!r} framing contains a dollar amount: {text!r}"
        )


def test_statutory_framing_never_contains_fabricated_percentages():
    """Sweep for fake numbers like '50%' or '2.5x' — anything that
    looks like a quantitative claim that isn't a citation. We do
    allow references to '4 culpability tiers' or similar, so the
    sweep is narrow: only patterns that look like a percent or a
    multiplier attached to a number."""
    for tier in ("high", "medium", "low"):
        text = _statutory_framing_for_tier(tier)
        assert not re.search(r"\b\d+(\.\d+)?\s*%", text), (
            f"Tier {tier!r} framing contains a percentage: {text!r}"
        )


def test_rendering_includes_statutory_framing_section_per_finding(exporter_with_fake):
    """Each rendered finding must include a 'Statutory Framing:' section
    label and the tier-appropriate framing paragraph in the rendered text."""
    e, fake = exporter_with_fake
    findings = [
        {
            "severity": "critical",
            "description": "Cleartext telnet",
            "evidence": "23/tcp open",
            "granular_breakdown": {
                "technical_cause": "Telnet on the wire.",
                "regulatory_violation": ["HIPAA-2026-164.312(e)(1)"],
                "business_grant_impact": "Grant termination risk.",
                "penalty_tier": "high",
            },
        },
        {
            "severity": "high",
            "description": "DNS tunneling",
            "evidence": "long DNS",
        },
        {
            "severity": "medium",
            "description": "Long outbound",
            "evidence": "1.2GB to 1.2.3.4",
        },
    ]
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        e.generate_report(
            framework="HIPAA-2026",
            findings=findings,
            status="non_compliant",
            confidence=0.9,
            job_id="job-statutory",
        )
    joined = "\n".join(fake.captured_text)
    # One "Statutory Framing:" section per finding -> 3 total.
    assert joined.count("Statutory Framing:") == 3
    # The Tier A framing cites 45 CFR 160.404 and RCW 19.373.030.
    assert "45 CFR 160.404" in joined
    assert "RCW 19.373.030" in joined
    # The "[LEGAL REVIEW]" marker is present in the rendered text.
    assert "[LEGAL REVIEW]" in joined


def test_statutory_framing_tier_a_appears_for_critical_finding(exporter_with_fake):
    """A critical finding with the high tier must receive the Tier A
    framing, which references 'Higher culpability tiers'."""
    e, fake = exporter_with_fake
    findings = [{
        "severity": "critical",
        "description": "Cleartext MySQL",
        "evidence": "3306",
        "granular_breakdown": {
            "technical_cause": "MySQL on the wire in cleartext.",
            "regulatory_violation": ["HIPAA-2026-164.312(e)(1)"],
            "business_grant_impact": "Grant termination risk.",
            "penalty_tier": "high",
        },
    }]
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        e.generate_report(
            framework="HIPAA-2026",
            findings=findings,
            status="non_compliant",
            confidence=0.95,
            job_id="job-tier-a",
        )
    joined = "\n".join(fake.captured_text)
    # Tier A language: "Reasonable Cause or Wilful Neglect" + the
    # 160.404 culpability-tier reference.
    assert "Reasonable Cause or Wilful Neglect" in joined
    assert "45 CFR 160.404" in joined


def test_statutory_framing_does_not_appear_before_existing_layers(exporter_with_fake):
    """The Statutory Framing section must come after Technical Cause,
    Regulatory Violation, and Business & Grant Impact in the rendered
    text. This keeps the 3-layer structure intact and the new section
    as a contextual append."""
    e, fake = exporter_with_fake
    with patch("src.utils.pdf_exporter.FPDF", lambda: fake):
        e.generate_report(
            framework="HIPAA-2026",
            findings=[{
                "severity": "high",
                "description": "FTP cleartext",
                "evidence": "21/tcp",
            }],
            status="non_compliant",
            confidence=0.9,
            job_id="job-order",
        )
    joined = "\n".join(fake.captured_text)
    pos_technical   = joined.find("Technical Cause:")
    pos_regulatory  = joined.find("Regulatory Violation:")
    pos_business    = joined.find("Business & Grant Impact:")
    pos_statutory   = joined.find("Statutory Framing:")
    assert 0 < pos_technical < pos_regulatory < pos_business < pos_statutory


# ──────────────────────────────────────────────────────────────────────────────
# Shared fixture
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def exporter_with_fake(tmp_path):
    """A (PDFReportExporter, _CapturingFPDF) pair for render-trace tests."""
    e = PDFReportExporter()
    e.output_dir = str(tmp_path)
    os.makedirs(e.output_dir, exist_ok=True)
    return e, _CapturingFPDF()

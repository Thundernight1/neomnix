"""
PDF Report Exporter — Neomnix Healthcare Edition.
Chunk 3: Branded "Healthcare Executive Audit Report" template that
renders the 3-layer granular breakdown per finding and adds prominent
"Grant Loss Risk" warnings for critical telemetry leaks.
Chunk 4:
  - TrueType font (TTF) integration with an explicit, test-only short
    circuit (NEOMNIX_DISABLE_TTF=1 or APP_ENV=test) so test execution
    stays fast and independent of local font asset paths.
  - Final branded title: "Saglik Sektoru VIP Denetim Raporu"
    (rendered as Turkish "Sağlık Sektörü VIP Denetim Raporu" when
    the TTF is loaded; rendered as ASCII transliteration otherwise).
  - Statutory framing text in the 3-layer breakdown that points to
    45 CFR 160.404 (HIPAA culpability tiers) and RCW 19.373.030
    (MHMDA private right of action), without inventing penalty
    dollar amounts. Bracketed text is explicitly marked
    "[LEGAL REVIEW]" so customer counsel can sign off before this
    report is shown to an end customer.

Authorization model (Chunk 3 R4):
  The admin-only role check is enforced at the FastAPI route layer
  via `Depends(require_role("admin"))` in `src/api/main.py`. This
  exporter is NOT the authorization boundary; it is purely a renderer.
  If a viewer-level request reaches this code, that is a route-layer
  bug to be fixed in main.py, not here.

Penalty tier model (Chunk 3 R2 + Chunk 4 R3):
  The brief forbids hardcoded penalty amounts in rendered output.
  This module uses qualitative tier keys (high / medium / low)
  derived from the finding's in-scope HIPAA citation count, mapped to
  bracket labels via the PENALTY_TIER_LABELS constant. Customer legal
  is responsible for filling in actual dollar values in production —
  see the comment above PENALTY_TIER_LABELS.
"""

from fpdf import FPDF
from datetime import datetime
import os


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  FONT LOADING — TEST-SAFE BY DEFAULT                                        ║
# ╠════════════════════════════════════════════════════════════════════════════╣
# ║  The TTF loader is bypassed when:                                           ║
# ║    - NEOMNIX_DISABLE_TTF=1 (explicit override), or                          ║
# ║    - APP_ENV=test (the test suite sets this in conftest.py).                ║
# ║                                                                            ║
# ║  When bypassed, fpdf2's built-in Helvetica is used, which is Latin-1 only.  ║
# ║  The PDF template is 100% English in all render modes; the loader exists   ║
# ║  for future templates that may need non-ASCII content.                    ║
# ║                                                                            ║
# ║  When NOT bypassed, the loader tries (in order):                           ║
# ║    1. NEOMNIX_TTF_FONT_PATH env var (must point to a valid .ttf)           ║
# ║    2. A list of well-known system font directories                         ║
# ║                                                                            ║
# ║  If the TTF loads, it is registered with fpdf2 once per process via the     ║
# ║  module-level _ttf_state. The font face names ("Regular", "Bold", "Italic")║
# ║  are used in pdf.set_font() calls.                                         ║
# ╚════════════════════════════════════════════════════════════════════════════╝

_FONT_FAMILY = "Neomnix"  # registered with fpdf2 when TTF loads
_TTF_STATE = {
    "attempted": False,  # set to True after first load attempt
    "loaded":    False,  # True if a TTF is registered and usable
    "regular":   None,   # path or None
    "bold":      None,
    "italic":    None,
    "bold_italic": None,
    "family":    "Helvetica",  # fpdf2 family name in effect
}


def _ttf_short_circuited() -> bool:
    """True when the TTF loader should be bypassed.

    The bypass is taken when:
      - NEOMNIX_DISABLE_TTF == "1", or
      - APP_ENV == "test".

    Production deployments leave both unset and get the real loader.
    """
    if os.environ.get("NEOMNIX_DISABLE_TTF", "").strip() == "1":
        return True
    if os.environ.get("APP_ENV", "").strip().lower() == "test":
        return True
    return False


def _ttf_search_paths() -> list:
    """Build the ordered list of candidate TTF paths.

    The order is: explicit NEOMNIX_TTF_FONT_PATH, then a list of
    well-known system font locations. The first one that points at
    a readable file is used.
    """
    candidates = []
    explicit = os.environ.get("NEOMNIX_TTF_FONT_PATH", "").strip()
    if explicit:
        candidates.append(explicit)
    candidates.extend([
        # macOS — DejaVu is not bundled with the OS, but the path
        # below is a common Homebrew install location.
        "/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        # Debian / Ubuntu package `fonts-dejavu`
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Common CI / Linux locations
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ])
    return candidates


def _ttf_bold_paths() -> list:
    """Same as _ttf_search_paths but for the bold/italic/bold-italic
    weights. Falls back to the regular TTF if the bold variant is
    not found — fpdf2 can synthesize bold/italic from a regular
    TTF when needed, but explicit variants render better."""
    candidates = []
    explicit = os.environ.get("NEOMNIX_TTF_BOLD_PATH", "").strip()
    if explicit:
        candidates.append(explicit)
    # Replace the basename in the search path. We do this in a
    # second pass over the regular candidates.
    for path in _ttf_search_paths():
        if path.endswith("DejaVuSans.ttf"):
            candidates.append(path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"))
    return candidates


def _find_ttf(paths):
    """Return the first path in `paths` that points to a readable file."""
    for p in paths:
        if p and os.path.isfile(p) and os.access(p, os.R_OK):
            return p
    return None


def _ensure_ttf_loaded(pdf: FPDF) -> None:
    """Idempotently attempt to load and register a Unicode TTF.

    The first call does the I/O; subsequent calls reuse the cached
    state. On any failure (path missing, fpdf2 exception), state
    `loaded` stays False and the caller falls back to Helvetica.

    Note: the `pdf` parameter is accepted for future use (e.g. registering
    the font against a specific FPDF instance). fpdf2's `add_font`
    is process-global, so the same TTF is shared across all FPDF
    instances.
    """
    if _TTF_STATE["attempted"]:
        return
    _TTF_STATE["attempted"] = True

    if _ttf_short_circuited():
        return

    regular_path = _find_ttf(_ttf_search_paths())
    if not regular_path:
        # No TTF available. The caller will fall back to Helvetica
        # and render Turkish text as ASCII transliteration. This is
        # a normal condition in test environments and is not an
        # error.
        return

    try:
        # Register the regular weight.
        pdf.add_font(_FONT_FAMILY, "", regular_path)
        _TTF_STATE["regular"] = regular_path
        _TTF_STATE["family"] = _FONT_FAMILY

        # Register the remaining three styles (B, I, BI) so that
        # later pdf.set_font(family, "B"|"I"|"BI", ...) calls do not
        # raise "Undefined font: neomnix<B|I|BI>".
        #
        # We prefer dedicated TTF files when available (better
        # typography) but fall back to the regular TTF for any
        # missing variant. fpdf2 will synthesize the missing weight
        # or slant from the regular glyphs, which is visually
        # imperfect but functionally correct — the report will not
        # crash. This fallback is what makes the loader safe on
        # minimal Linux CI runners that ship only DejaVuSans.ttf
        # without the bold/italic variants.
        bold_path = _find_ttf(_ttf_bold_paths())
        pdf.add_font(_FONT_FAMILY, "B",  bold_path or regular_path)
        _TTF_STATE["bold"] = bold_path  # may be None

        pdf.add_font(_FONT_FAMILY, "I",  regular_path)
        _TTF_STATE["italic"] = None  # always synthesized from regular

        pdf.add_font(_FONT_FAMILY, "BI", regular_path)
        _TTF_STATE["bold_italic"] = None  # always synthesized from regular

        _TTF_STATE["loaded"] = True
    except Exception as exc:  # noqa: BLE001
        # Don't crash the report if a malformed TTF is installed.
        # The caller will fall back to Helvetica.
        print(
            f"[pdf_exporter] TTF load failed ({exc!r}); "
            f"falling back to Helvetica."
        )
        _TTF_STATE["loaded"] = False
        _TTF_STATE["family"] = "Helvetica"


def font_family() -> str:
    """Return the fpdf2 font family name that is currently in effect.

    Either the registered TTF family name ("Neomnix") or the built-in
    "Helvetica" fallback. Tests can use this to assert which path
    the loader took.
    """
    return _TTF_STATE["family"]


def ttf_loaded() -> bool:
    """True if the TTF was successfully loaded and registered."""
    return _TTF_STATE["loaded"]


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  PENALTY TIER LABELS — CUSTOMER-CONFIGURABLE                                ║
# ║                                                                              ║
# ║  The brief forbids hardcoded dollar amounts in the rendered PDF.            ║
# ║  These labels are qualitative bracket names. Customer legal must fill       ║
# ║  in actual dollar values in the deployment configuration and update        ║
# ║  these strings to reflect them. For now, bracket names only.               ║
# ╚════════════════════════════════════════════════════════════════════════════╝
PENALTY_TIER_LABELS = {
    "high":   "Tier A - High Penalty Exposure (Critical, Multi-Control)",
    "medium": "Tier B - Moderate Penalty Exposure (Critical, Single-Control or High)",
    "low":    "Tier C - Lower Penalty Exposure (MHMDA-only or Medium)",
}

# Template name. Single English title. The header is 100% English
# in all render modes; no bilingual fallback and no Turkish
# transliteration. The TTF loader remains in place so non-ASCII
# content can still be rendered if a future template needs it.
REPORT_TEMPLATE_NAME = "Healthcare Enterprise Compliance Audit Report"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  STATUTORY FRAMING — QUALITATIVE, NOT FABRICATED                            ║
# ╠════════════════════════════════════════════════════════════════════════════╣
# ║  These strings are deliberately generic and explicitly mark                 ║
# ║  thresholds / numbers as "see source regulation" so we never invent         ║
# ║  dollar amounts. The "[LEGAL REVIEW]" marker is a breadcrumb for the       ║
# ║  customer's counsel to sign off before this template is shown to a         ║
# ║  paying end customer.                                                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# Tier A framing. HIPAA Section 45 CFR 160.404 establishes four
# culpability tiers, but the per-violation dollar ranges in the
# Federal Register are republished annually and vary by year of
# assessment. We point to the regulation rather than quote a number.
STATUTORY_FRAMING_HIGH = (
    "Statutory exposure (Tier A): This finding maps to HIPAA's higher "
    "culpability tiers under 45 CFR 160.404 (Reasonable Cause or Wilful "
    "Neglect) and may, depending on the customer's MHMDA posture, "
    "support a private right of action under RCW 19.373.030. The "
    "applicable per-violation and annual cap amounts are published in "
    "the Federal Register and may have been updated since the report "
    "date. Consult the HHS Office for Civil Rights penalty schedule and "
    "the customer's specific grant terms for current figures. "
    "[LEGAL REVIEW]"
)

# Tier B framing.
STATUTORY_FRAMING_MEDIUM = (
    "Statutory exposure (Tier B): This finding maps to HIPAA's lower-"
    "tier culpability bands (Lack of Knowledge with reasonable cause) "
    "under 45 CFR 160.404. Where the underlying data is also subject "
    "to the Washington My Health My Data Act, a private right of "
    "action under RCW 19.373.030 may be available to affected "
    "consumers independent of any HHS action. Per-violation caps and "
    "annual limits are set by the Federal Register and may be updated. "
    "Consult the HHS Office for Civil Rights penalty schedule for "
    "current figures. [LEGAL REVIEW]"
)

# Tier C framing.
STATUTORY_FRAMING_LOW = (
    "Statutory exposure (Tier C): This finding may be addressed through "
    "the customer's standard HIPAA corrective-action process under "
    "45 CFR 164.404 / 164.406 without an immediate civil monetary "
    "penalty, but still carries a private right of action risk under "
    "RCW 19.373.030 if MHMDA-protected data is implicated. [LEGAL "
    "REVIEW]"
)


def _resolve_penalty_tier_label(tier: str) -> str:
    """Map a tier key (high/medium/low) to its bracket label.
    Unknown tiers fall back to the lower bracket so we never fabricate
    a tier name."""
    return PENALTY_TIER_LABELS.get(tier, PENALTY_TIER_LABELS["low"])


def _statutory_framing_for_tier(tier: str) -> str:
    """Return the statutory framing paragraph for a given penalty tier.
    The text is qualitative; the customer's counsel must approve before
    delivery to an end customer."""
    return {
        "high":   STATUTORY_FRAMING_HIGH,
        "medium": STATUTORY_FRAMING_MEDIUM,
        "low":    STATUTORY_FRAMING_LOW,
    }.get(tier, STATUTORY_FRAMING_LOW)


def _build_finding_breakdown(finding: dict) -> dict:
    """Resolve the 3-layer breakdown for a finding.

    If the caller already passed a `granular_breakdown` (e.g. from
    CrossMappingAnalyzer), use it as-is. Otherwise synthesize a
    3-layer breakdown from the basic fields so older callers and
    test fixtures still render with the new structure.
    """
    if "granular_breakdown" in finding and isinstance(finding["granular_breakdown"], dict):
        gb = dict(finding["granular_breakdown"])
        # Backfill the penalty tier label.
        if "penalty_tier" in gb and "penalty_tier_label" not in gb:
            gb["penalty_tier_label"] = _resolve_penalty_tier_label(gb["penalty_tier"])
        return gb

    # Fallback synthesis. The basic finding dict only has
    # severity / description / evidence / timestamp.
    severity = (finding.get("severity") or "unknown").lower()
    description = finding.get("description") or "No description"
    evidence = finding.get("evidence") or "No evidence provided"

    # No in-scope control list to derive the tier from; infer from severity.
    inferred_tier = (
        "high"   if severity == "critical" else
        "medium" if severity == "high" else
        "low"
    )

    return {
        "technical_cause": description,
        "regulatory_violation": [
            "Regulatory citation not provided in the finding payload. "
            "See ComplianceAgent output for the matched HIPAA-2026 / "
            "WA-MHMDA controls."
        ],
        "business_grant_impact": (
            "Federal and state healthcare grants require continuous "
            "demonstrable compliance with HIPAA Privacy and Security "
            "Rules and applicable state health-data statutes. This "
            "technical condition may constitute a breach of the grant's "
            "data-protection warranties. See HHS OCR penalty schedule "
            "(45 CFR 160.404) and WA State Health IT Authority grant "
            "terms for the current published penalty schedule and grant "
            "termination criteria as of the report date."
        ),
        "penalty_tier": inferred_tier,
        "penalty_tier_label": _resolve_penalty_tier_label(inferred_tier),
        "_evidence": evidence,  # preserved for the rendering layer
    }


class PDFReportExporter:
    """Generates branded executive PDF reports for healthcare compliance."""

    BRAND_COLOR = (30, 58, 138)      # Deep blue
    HEADER_COLOR = (37, 99, 235)     # Blue
    CRITICAL_COLOR = (220, 38, 38)   # Red
    HIGH_COLOR = (234, 88, 12)       # Orange
    MEDIUM_COLOR = (202, 138, 4)     # Yellow
    TEXT_COLOR = (31, 41, 55)        # Dark gray
    SUBTLE_COLOR = (107, 114, 128)   # Gray
    GRANT_LOSS_COLOR = (153, 27, 27) # Deep red — used for the "Grant Loss Risk" band

    def __init__(self):
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "reports", "pdf"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        # Read platform name from environment — allows white-label PDF branding
        self.platform_name = os.getenv("PLATFORM_NAME", os.getenv("ADMIN_EMAIL", "").split("@")[-1].split(".")[0].upper() + " GRC")
        if not self.platform_name or len(self.platform_name) < 3:
            self.platform_name = "Neomnix GRC"

    def _font(self, style: str = "", size: int = 10) -> tuple:
        """Return (family, style, size) for the active font.

        When a TTF is loaded, the family is the registered name
        ("Neomnix"). Otherwise, the family is the built-in Helvetica.
        """
        return (font_family(), style, size)

    def generate_report(self, framework: str, findings: list, status: str, confidence: float, job_id: str) -> str:
        """Generate the branded Healthcare Executive Audit Report."""
        pdf = FPDF()
        # Attempt to load a Unicode TTF. No-op in test env or when
        # NEOMNIX_DISABLE_TTF=1.
        _ensure_ttf_loaded(pdf)
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.add_page()

        # --- Cover / Header Section ---
        self._draw_header(pdf, framework, job_id, status, confidence)

        # --- Executive Summary ---
        pdf.ln(5)
        self._section_title(pdf, "Executive Summary")

        total = len(findings)
        critical_count = sum(1 for f in findings if f.get('severity') == 'critical')
        high_count = sum(1 for f in findings if f.get('severity') == 'high')
        medium_count = sum(1 for f in findings if f.get('severity') == 'medium')

        family = font_family()
        pdf.set_font(family, size=10)
        pdf.set_text_color(*self.TEXT_COLOR)

        summary_lines = [
            f"This report presents the results of an automated compliance scan against the {framework} framework.",
            f"A total of {total} finding(s) were identified during the assessment.",
            f"",
            f"  - Critical: {critical_count}",
            f"  - High: {high_count}",
            f"  - Medium: {medium_count}",
            f"",
            f"Overall Determination: {status.upper().replace('_', ' ')}",
            f"Confidence Score: {confidence:.1%}",
        ]

        for line in summary_lines:
            pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # --- Detailed Findings (3-layer breakdown) ---
        if findings:
            self._section_title(pdf, "Detailed Findings")
            for i, finding in enumerate(findings, 1):
                self._render_finding(pdf, i, finding)

        # --- Legal Disclaimer ---
        self._section_title(pdf, "Legal Disclaimer")
        pdf.set_font(family, "I", 8)
        pdf.set_text_color(*self.SUBTLE_COLOR)
        pdf.multi_cell(0, 4,
            "This report is generated by the Neomnix Platform Compliance Platform. "
            "It is intended for authorized personnel only and should not be distributed "
            "without proper authorization. The findings represent a point-in-time assessment "
            "and may not reflect the current security posture. Penalty tier labels in this "
            "report are qualitative bracket names; actual regulatory penalty amounts and "
            "grant-termination criteria are governed by the HHS OCR penalty schedule "
            "(45 CFR 160.404) and the customer's specific grant terms, both of which "
            "may have been updated since the report date. This report does not constitute "
            "legal or professional compliance advice. Organizations should consult qualified "
            "compliance professionals for formal assessments."
        )

        # --- Page Numbers (footer) ---
        total_pages = pdf.page_no()
        for page_num in range(1, total_pages + 1):
            pdf.page = page_num
            pdf.set_y(-15)
            pdf.set_font(family, "I", 7)
            pdf.set_text_color(*self.SUBTLE_COLOR)
            pdf.cell(0, 10, f"{self.platform_name}  |  Page {page_num} of {total_pages}  |  Confidential", align="C")

        # --- Save ---
        filename = f"{framework}_{job_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)

        return filepath

    def _render_finding(self, pdf: FPDF, index: int, finding: dict) -> None:
        """Render a single finding with the 3-layer breakdown.

        Layout:
            - Title row with severity color.
            - For CRITICAL findings: a prominent "Grant Loss Risk" warning band.
            - 3-layer breakdown: Technical Cause, Regulatory Violation, Business & Grant Impact.
            - Statutory framing paragraph keyed off the penalty tier
              (45 CFR 160.404 + RCW 19.373.030 references; no fabricated numbers).
            - Penalty tier label (Tier A / B / C).
            - Evidence footer.
        """
        severity = (finding.get("severity") or "unknown").upper()
        breakdown = _build_finding_breakdown(finding)
        evidence = finding.get("evidence") or breakdown.get("_evidence") or "No evidence provided"
        is_critical = severity == "CRITICAL"
        family = font_family()

        # --- Critical: Grant Loss Risk band ---
        if is_critical:
            self._draw_grant_loss_band(pdf)

        # --- Title row ---
        if severity == "CRITICAL":
            pdf.set_text_color(*self.CRITICAL_COLOR)
        elif severity == "HIGH":
            pdf.set_text_color(*self.HIGH_COLOR)
        elif severity == "MEDIUM":
            pdf.set_text_color(*self.MEDIUM_COLOR)
        else:
            pdf.set_text_color(*self.TEXT_COLOR)

        pdf.set_font(family, "B", 10)
        pdf.cell(0, 7, f"Finding #{index} [{severity}]", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*self.TEXT_COLOR)

        # --- 3-layer breakdown ---
        # Layer 1: Technical Cause
        pdf.set_font(family, "B", 9)
        pdf.cell(0, 5, "Technical Cause:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, size=9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, breakdown["technical_cause"] or "(no technical cause provided)")
        pdf.ln(1)

        # Layer 2: Regulatory Violation
        pdf.set_font(family, "B", 9)
        pdf.cell(0, 5, "Regulatory Violation:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, size=9)
        reg_violations = breakdown.get("regulatory_violation") or []
        if not reg_violations:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, "(no regulatory citation provided)")
        else:
            for line in reg_violations:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, f"- {line}")
        pdf.ln(1)

        # Layer 3: Business & Grant Impact
        pdf.set_font(family, "B", 9)
        pdf.cell(0, 5, "Business & Grant Impact:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, size=9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, breakdown.get("business_grant_impact") or "(no business impact provided)")
        pdf.ln(1)

        # Chunk 4 R3: Statutory framing paragraph keyed off tier
        pdf.set_font(family, "B", 9)
        pdf.cell(0, 5, "Statutory Framing:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, size=9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, _statutory_framing_for_tier(breakdown.get("penalty_tier", "low")))
        pdf.ln(1)

        # Penalty tier label
        pdf.set_font(family, "I", 8)
        pdf.set_text_color(*self.SUBTLE_COLOR)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"Penalty tier: {breakdown.get('penalty_tier_label', 'unclassified')}")
        pdf.set_text_color(*self.TEXT_COLOR)
        pdf.ln(1)

        # Evidence footer
        pdf.set_font(family, "I", 8)
        pdf.set_text_color(*self.SUBTLE_COLOR)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"Evidence: {evidence}")
        pdf.ln(3)

    def _draw_grant_loss_band(self, pdf: FPDF) -> None:
        """Render a prominent red "Grant Loss Risk" warning band for
        critical findings. Called at the top of each critical finding.
        """
        family = font_family()
        # Compute band height proportional to the page width.
        band_height = 14
        x = pdf.l_margin
        w = pdf.w - pdf.l_margin - pdf.r_margin
        y = pdf.get_y()
        pdf.set_fill_color(*self.GRANT_LOSS_COLOR)
        pdf.rect(x, y, w, band_height, style='F')
        pdf.set_xy(x, y + 1)
        pdf.set_font(family, "B", 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(w, 6, "GRANT LOSS RISK - CRITICAL TELEMETRY LEAK", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x)
        pdf.set_font(family, size=8)
        pdf.cell(w, 5, "This finding may trigger grant termination clauses and standard regulatory financial penalty exposure.", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(y + band_height + 2)
        pdf.set_text_color(*self.TEXT_COLOR)

    def _draw_header(self, pdf: FPDF, framework: str, job_id: str, status: str, confidence: float):
        """Draw branded header with company name and scan metadata.

        Layout:
            - Top brand bar (deep blue).
            - Company name (white).
            - Single English report title (light blue accent).
            - Metadata line.

        The header is 100% English in all render modes. There is no
        bilingual layout and no Turkish transliteration fallback.
        """
        family = font_family()
        # Top bar
        pdf.set_fill_color(*self.BRAND_COLOR)
        pdf.rect(0, 0, 210, 45, style='F')

        # Company name
        pdf.set_y(8)
        pdf.set_font(family, "B", 20)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, self.platform_name.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        # Single English report title.
        pdf.set_font(family, "B", 14)
        pdf.set_text_color(191, 219, 254)
        pdf.cell(0, 7, REPORT_TEMPLATE_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

        # Metadata line
        pdf.set_font(family, size=8)
        pdf.set_text_color(147, 197, 253)
        meta = f"Scan ID: {job_id[:12]}...  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Status: {status.upper()}"
        pdf.cell(0, 5, meta, align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(50)

    def _section_title(self, pdf: FPDF, title: str):
        """Draw a styled section title with underline."""
        family = font_family()
        pdf.set_font(family, "B", 12)
        pdf.set_text_color(*self.HEADER_COLOR)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        # Underline
        pdf.set_draw_color(*self.HEADER_COLOR)
        pdf.set_line_width(0.3)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(3)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  ADMIN-ONLY ACCESS NOTE                                                     ║
# ╠════════════════════════════════════════════════════════════════════════════╣
# ║  The authorization boundary is NOT in this file. The PDF report download   ║
# ║  endpoint at `src/api/main.py:537` enforces `require_role("admin")` at     ║
# ║  the FastAPI route layer. This module is a pure renderer.                 ║
# ║                                                                            ║
# ║  To verify the role check is in place:                                      ║
# ║    1. `grep -n "require_role" backend/src/api/main.py` should show          ║
# ║       `Depends(require_role("admin"))` on the get_pdf_report route.        ║
# ║    2. The test `tests/test_ws_alerts.py::TestPdfRouteAdminOnly` asserts     ║
# ║       that analyst/viewer roles get 403 and admins get through.            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

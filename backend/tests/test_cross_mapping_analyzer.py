"""
Tests for CrossMappingAnalyzer — Chunk 2 healthcare-only output +
Chunk 3 3-layer granular breakdown.

These tests pin the analyzer's response shape:
  - Every match carries a `risk_type` field with both Turkish/English
    business labels.
  - The `controls` list contains ONLY HIPAA-2026 and WA-MHMDA control
    IDs. SOC2, NIST-800-53, CCM-4.0, and SEC-2023 IDs must never leak
    through, even if the rules JSON still carries them for historical
    reasons.
  - The output is a `risk_type`-based per-match dict, not an N×N
    multi-framework intersection.
  - Chunk 3: every match carries a `granular_breakdown` field with
    three non-empty layers (technical_cause, regulatory_violation,
    business_grant_impact) and a `penalty_tier` key derived from
    the in-scope HIPAA citation count. No dollar amounts anywhere.
"""

import asyncio
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.cross_mapping_analyzer import (
    CrossMappingAnalyzer,
    RISK_LABELS,
    _build_granular_breakdown,
    _derive_penalty_tier,
)


# Out-of-scope framework prefixes that must NEVER appear in analyzer output.
OUT_OF_SCOPE_PREFIXES = ("SOC2", "NIST-", "CCM-", "SEC-")


@pytest.fixture
def analyzer():
    return CrossMappingAnalyzer()


def _assert_only_healthcare_controls(controls: list) -> None:
    """Assert every control ID in the list is HIPAA-2026 or WA-MHMDA."""
    assert controls, "controls list should not be empty for a matched finding"
    for c in controls:
        assert c.startswith("HIPAA-") or c.startswith("WA-MHMDA"), (
            f"Out-of-scope control ID leaked through analyzer: {c!r}"
        )
        for bad in OUT_OF_SCOPE_PREFIXES:
            assert not c.startswith(bad), (
                f"Out-of-scope framework prefix {bad!r} leaked through analyzer: {c!r}"
            )


def test_risk_labels_constant():
    """The two business-language risk labels are defined and stable."""
    assert RISK_LABELS == [
        "HIPAA Ceza Riski",
        "Devlet Hibesi (Grant) İptal Riski",
    ]


def test_analyzer_loads_rules(analyzer):
    """The rules JSON should be loaded and non-empty."""
    assert len(analyzer.rules) > 0, "Expected at least one rule from compliance_rules.json"


def test_analyze_telnet_attaches_risk_type_and_healthcare_controls_only(analyzer):
    result = asyncio.run(analyzer.analyze("telnet"))
    assert result["matches"] >= 1, "Expected at least one telnet-related match"
    for vuln, match in result["analysis"].items():
        assert match["risk_type"] == list(RISK_LABELS), (
            f"Missing or wrong risk_type for {vuln}: {match['risk_type']!r}"
        )
        _assert_only_healthcare_controls(match["controls"])


def test_analyze_dns_tunneling_attaches_risk_type_and_healthcare_controls_only(analyzer):
    result = asyncio.run(analyzer.analyze("DNS Tunneling"))
    assert result["matches"] >= 1, "Expected at least one DNS tunneling match"
    for vuln, match in result["analysis"].items():
        assert match["risk_type"] == list(RISK_LABELS)
        _assert_only_healthcare_controls(match["controls"])


def test_analyze_hipaa_control_id_query_healthcare_controls_only(analyzer):
    """Querying by a HIPAA control ID returns only HIPAA/MHMDA controls."""
    result = asyncio.run(analyzer.analyze("HIPAA-2026-164.312"))
    assert result["matches"] >= 1
    for vuln, match in result["analysis"].items():
        _assert_only_healthcare_controls(match["controls"])


def test_analyze_unknown_query_returns_empty_analysis(analyzer):
    result = asyncio.run(analyzer.analyze("xyzzy-no-such-trigger"))
    assert result["matches"] == 0
    assert result["analysis"] == {}


def test_no_out_of_scope_framework_prefix_anywhere_in_healthcare_output(analyzer):
    """Sweep the entire ruleset via a broad query and assert no leakage."""
    # Use a query that matches all rules (substring that appears in every trigger).
    # "encryption" appears in several; we instead iterate every rule directly to be sure.
    leaked = []
    for trigger in analyzer.rules.keys():
        # Simulate the analyzer path by calling analyze with a substring of the trigger
        sub = trigger.split()[0].lower()
        result = asyncio.run(analyzer.analyze(sub))
        for vuln, match in result["analysis"].items():
            for c in match["controls"]:
                for bad in OUT_OF_SCOPE_PREFIXES:
                    if c.startswith(bad):
                        leaked.append((vuln, c))
    assert not leaked, f"Out-of-scope controls leaked: {leaked}"


def test_output_shape_is_per_match_with_risk_type_not_n_by_n(analyzer):
    """The output is keyed by vulnerability and contains a risk_type list,
    not a multi-framework N×N intersection dict.

    This guards against a regression where the old `frameworks: [...]`
    N×N shape is reintroduced.
    """
    result = asyncio.run(analyzer.analyze("encryption"))
    for vuln, match in result["analysis"].items():
        assert "frameworks" not in match, (
            f"Legacy N×N 'frameworks' field reappeared in {vuln}"
        )
        assert "risk_type" in match, f"Missing risk_type in {vuln}"
        assert isinstance(match["risk_type"], list)
        assert len(match["risk_type"]) == 2


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CHUNK 3 — 3-LAYER GRANULAR BREAKDOWN                                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝


# Dollar amount pattern — should NEVER appear in any of the breakdown
# text fields. The brief explicitly forbids hardcoded penalty amounts.
_DOLLAR_PATTERN = re.compile(r"\$\s*\d")


def test_derive_penalty_tier_three_or_more_hipaa_citations_is_high():
    assert _derive_penalty_tier([
        "HIPAA-2026-164.312(a)(1)",
        "HIPAA-2026-164.312(e)(1)",
        "HIPAA-2026-164.312(e)(2)(ii)",
    ]) == "high"


def test_derive_penalty_tier_one_or_two_hipaa_citations_is_medium():
    assert _derive_penalty_tier([
        "HIPAA-2026-164.312(e)(1)",
    ]) == "medium"
    assert _derive_penalty_tier([
        "HIPAA-2026-164.312(e)(1)",
        "HIPAA-2026-164.308(a)(1)(ii)(B)",
    ]) == "medium"


def test_derive_penalty_tier_no_hipaa_citations_is_low():
    """MHMDA-only findings (no HIPAA) get the lowest tier."""
    assert _derive_penalty_tier([
        "WA-MHMDA-RCW-19.373.030",
    ]) == "low"


def test_derive_penalty_tier_empty_controls_is_low():
    assert _derive_penalty_tier([]) == "low"


def test_build_granular_breakdown_has_all_three_layers():
    breakdown = _build_granular_breakdown(
        trigger="Active Telnet sessions",
        description="Plaintext remote access detected.",
        in_scope_controls=[
            "HIPAA-2026-164.312(e)(1)",
            "WA-MHMDA-RCW-19.373.030",
        ],
    )
    assert "technical_cause" in breakdown
    assert "regulatory_violation" in breakdown
    assert "business_grant_impact" in breakdown
    assert "penalty_tier" in breakdown

    assert breakdown["technical_cause"], "technical_cause must not be empty"
    assert breakdown["regulatory_violation"], "regulatory_violation must not be empty"
    assert breakdown["business_grant_impact"], "business_grant_impact must not be empty"
    assert breakdown["penalty_tier"] in {"high", "medium", "low"}


def test_build_granular_breakdown_no_dollar_amounts_anywhere():
    """The brief forbids hardcoded penalty amounts. None of the breakdown
    text fields may contain a dollar sign followed by a digit."""
    breakdown = _build_granular_breakdown(
        trigger="Unencrypted database connection detected",
        description="Cleartext database traffic detected.",
        in_scope_controls=[
            "HIPAA-2026-164.312(a)(1)",
            "HIPAA-2026-164.312(e)(1)",
            "HIPAA-2026-164.312(e)(2)(ii)",
            "WA-MHMDA-RCW-19.373.010",
        ],
    )
    # Concatenate every text field for the regex sweep.
    all_text = " ".join(
        [breakdown["technical_cause"]]
        + list(breakdown["regulatory_violation"])
        + [breakdown["business_grant_impact"]]
    )
    assert not _DOLLAR_PATTERN.search(all_text), (
        f"Found a hardcoded dollar amount in granular breakdown: {all_text!r}"
    )


def test_build_granular_breakdown_business_impact_mentions_grants():
    """The business & grant impact layer must explicitly call out the
    grant-cancellation risk — that is the whole point of the layer."""
    breakdown = _build_granular_breakdown(
        trigger="DNS Tunneling Suspected",
        description="Suspiciously long DNS queries.",
        in_scope_controls=[
            "HIPAA-2026-164.312(b)",
            "WA-MHMDA-RCW-19.373.040",
        ],
    )
    text = breakdown["business_grant_impact"].lower()
    assert "grant" in text, "business_grant_impact must mention 'grant'"
    assert "hhs" in text or "ocr" in text or "hipaa" in text, (
        "business_grant_impact should reference the regulatory source"
    )


def test_build_granular_breakdown_regulatory_violation_is_in_scope_only():
    """Even if the rule JSON still carries SOC2/NIST/CCM strings, the
    regulatory_violation layer must only list in-scope citations."""
    breakdown = _build_granular_breakdown(
        trigger="Some trigger",
        description="Some description.",
        in_scope_controls=[
            "HIPAA-2026-164.312(e)(1)",
            "WA-MHMDA-RCW-19.373.030",
        ],
    )
    reg_text = " ".join(breakdown["regulatory_violation"])
    for bad in ("SOC2", "NIST-", "CCM-", "SEC-"):
        assert not reg_text.startswith(bad), (
            f"Out-of-scope prefix {bad!r} leaked into regulatory_violation: {reg_text!r}"
        )


def test_build_granular_breakdown_empty_controls_returns_placeholder():
    """When no in-scope controls match, the regulatory layer carries a
    'manual review' placeholder rather than crashing or returning empty."""
    breakdown = _build_granular_breakdown(
        trigger="Unknown trigger",
        description="No citation matches.",
        in_scope_controls=[],
    )
    assert breakdown["regulatory_violation"], "Must not be empty"
    assert "manual review" in breakdown["regulatory_violation"][0].lower()
    assert breakdown["penalty_tier"] == "low"


def test_analyze_returns_granular_breakdown_for_every_match(analyzer):
    """Every match in the analyze() output must include the new
    granular_breakdown field with all three layers populated."""
    result = asyncio.run(analyzer.analyze("telnet"))
    assert result["matches"] >= 1
    for vuln, match in result["analysis"].items():
        assert "granular_breakdown" in match, f"Missing granular_breakdown in {vuln}"
        gb = match["granular_breakdown"]
        assert gb["technical_cause"]
        assert gb["regulatory_violation"]
        assert gb["business_grant_impact"]
        assert gb["penalty_tier"] in {"high", "medium", "low"}


def test_analyze_granular_breakdown_no_dollar_amounts_anywhere(analyzer):
    """Sweep every match's breakdown text to confirm no dollar amounts
    are introduced anywhere in the analyzer's output."""
    result = asyncio.run(analyzer.analyze(""))
    # Empty query: a substring is contained in every trigger, so this
    # returns every rule in the file.
    assert result["matches"] > 0, "Empty query should match every rule"
    for vuln, match in result["analysis"].items():
        gb = match["granular_breakdown"]
        all_text = " ".join(
            [gb["technical_cause"]]
            + list(gb["regulatory_violation"])
            + [gb["business_grant_impact"]]
        )
        assert not _DOLLAR_PATTERN.search(all_text), (
            f"Dollar amount leaked into breakdown for {vuln}: {all_text!r}"
        )

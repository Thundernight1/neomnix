"""
CrossMappingAnalyzer — Neomnix healthcare refactor.

Scope (post Chunk 2 / 3):
  - Maps detected network/technical vulnerabilities to HIPAA-2026 and
    WA-MHMDA (RCW 19.373.030) only.
  - N×N multi-framework matching has been removed. SOC2, NIST-800-53,
    CCM-4.0, FedRAMP, PCI-DSS, and SEC-2023 are out of scope.
  - Every finding carries a `risk_type` field with the two business-
    language risk labels that drive the grant-funded healthcare UI:
      * "HIPAA Ceza Riski"                  — HIPAA penalty risk
      * "Devlet Hibesi (Grant) İptal Riski" — grant cancellation risk
  - Every finding carries a `granular_breakdown` field (Chunk 3) with
    a 3-layer structured explanation:
      * technical_cause         — what the network actually showed
      * regulatory_violation    — the exact HIPAA-2026 / WA-MHMDA
                                  citation(s) breached
      * business_grant_impact   — how the technical issue threatens
                                  the customer's federal/state
                                  healthcare grant compliance
                                  posture (no hardcoded penalty
                                  amounts — tiers only)
"""

import json
import os
from typing import Dict, List, Any


# Business-language risk labels attached to every matched finding.
# Turkish and English are both preserved on customer-facing surfaces.
RISK_LABELS: List[str] = [
    "HIPAA Ceza Riski",
    "Devlet Hibesi (Grant) İptal Riski",
]


# Penalty tier key derivation (no dollar amounts in code).
# Tier is computed from severity and the number of distinct in-scope
# HIPAA citations on a finding. The PDF renderer maps tier -> a named
# bracket label (e.g. "Tier A — high penalty exposure"). Customer
# legal is responsible for filling in actual dollar values in
# production deployment.
def _derive_penalty_tier(in_scope_controls: List[str]) -> str:
    """Return a penalty tier key (high / medium / low) derived from the
    finding's in-scope HIPAA citation count. No dollar amounts here.

    Heuristic:
        - 3+ HIPAA citations               -> "high"
        - 1–2 HIPAA citations              -> "medium"
        - 0 HIPAA citations (MHMDA only)   -> "low"
    """
    hipaa_count = sum(1 for c in in_scope_controls if c.startswith("HIPAA-"))
    if hipaa_count >= 3:
        return "high"
    if hipaa_count >= 1:
        return "medium"
    return "low"


def _build_granular_breakdown(
    trigger: str,
    description: str,
    in_scope_controls: List[str],
) -> Dict[str, Any]:
    """Construct the 3-layer structured breakdown for a finding.

    The output is purely qualitative — no dollar amounts, no fabricated
    numbers. The "penalty_tier" key is derived (not invented) and the
    PDF renderer is responsible for mapping the tier to a bracket label
    that the customer's legal team configures in production.

    Layers:
        1. technical_cause      — what the network actually showed.
                                  Sourced from the technical_trigger
                                  and description in compliance_rules.json.
        2. regulatory_violation — the exact HIPAA-2026 and/or WA-MHMDA
                                  citations breached. In-scope only.
        3. business_grant_impact — how this technical issue endangers
                                  the customer's federal/state
                                  healthcare grant compliance posture.
    """
    # Split in-scope controls by framework so the regulatory layer is
    # readable in the rendered PDF / UI.
    hipaa_citations = [c for c in in_scope_controls if c.startswith("HIPAA-")]
    mhmda_citations = [c for c in in_scope_controls if c.startswith("WA-MHMDA")]

    regulatory_lines: List[str] = []
    if hipaa_citations:
        regulatory_lines.append(
            "HIPAA-2026: " + "; ".join(hipaa_citations)
        )
    if mhmda_citations:
        regulatory_lines.append(
            "WA-MHMDA (RCW 19.373): " + "; ".join(mhmda_citations)
        )
    if not regulatory_lines:
        regulatory_lines.append(
            "No in-scope regulatory citation matched. Manual review required."
        )

    business_impact = (
        "Federal and state healthcare grants (e.g. SBIR, HRSA, CDC, "
        "state Health IT) require continuous, demonstrable compliance "
        "with HIPAA Privacy and Security Rules and applicable state "
        "health-data statutes. The technical condition above creates an "
        "active risk that grant sponsors will (a) treat the organization "
        "as out of compliance with the grant's data-protection "
        "warranties, (b) suspend or cancel funding under standard grant "
        "termination clauses, and (c) trigger standard regulatory "
        "financial penalty exposure. See HHS OCR penalty schedule "
        "(45 CFR 160.404) and WA State Health IT Authority grant terms "
        "for the current published penalty schedule and grant "
        "termination criteria as of the report date."
    )

    return {
        "technical_cause": (
            f"{trigger}. {description}".strip()
        ),
        "regulatory_violation": regulatory_lines,
        "business_grant_impact": business_impact,
        "penalty_tier": _derive_penalty_tier(in_scope_controls),
    }


class CrossMappingAnalyzer:
    """
    Healthcare compliance mapper.

    Loads vulnerability -> [regulatory controls] rules from
    compliance_rules.json and, on `analyze(query)`, returns the
    matching findings with their `risk_type` label set and a
    3-layer `granular_breakdown` per finding.
    """

    def __init__(self, rules_path: str = "src/core/compliance_rules.json"):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.rules_path = os.path.join(base_dir, rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load rules keyed by technical_trigger.

        Returns a dict shaped:
            {trigger: {"controls": [...], "description": "..."}}
        """
        if not os.path.exists(self.rules_path):
            return {}
        with open(self.rules_path, "r") as f:
            data = json.load(f)
        rules: Dict[str, Dict[str, Any]] = {}
        for item in data.get("mappings", []):
            trigger = item.get("technical_trigger")
            if not trigger:
                continue
            rules[trigger] = {
                "controls": item.get("controls", []),
                "description": item.get("description", ""),
            }
        return rules

    async def analyze(self, query: str) -> Dict[str, Any]:
        """
        Find rule entries matching the query and return each match
        with its regulatory controls, risk_type labels, and 3-layer
        granular breakdown.

        The query is matched (case-insensitive) against:
          - the technical trigger string
          - the rule description
          - any individual control ID

        Output shape (per match):
            {
                "vulnerability": <technical_trigger>,
                "risk_type":     ["HIPAA Ceza Riski",
                                  "Devlet Hibesi (Grant) İptal Riski"],
                "controls":      ["HIPAA-2026-...", "WA-MHMDA-..."],
                "granular_breakdown": {
                    "technical_cause":      "...",
                    "regulatory_violation": ["HIPAA-2026: ...", ...],
                    "business_grant_impact": "...",
                    "penalty_tier":         "high" | "medium" | "low",
                },
            }

        The top-level return value is:
            {
                "query":     <query string>,
                "matches":   <count>,
                "analysis":  {<vulnerability>: <match dict>, ...},
            }
        """
        query_lower = query.lower()
        matches: List[Dict[str, Any]] = []

        for trigger, details in self.rules.items():
            match_found = False
            if query_lower in trigger.lower():
                match_found = True
            elif query_lower in details.get("description", "").lower():
                match_found = True
            elif any(query_lower in c.lower() for c in details.get("controls", [])):
                match_found = True

            if match_found:
                # Filter the rule's controls to the in-scope healthcare
                # frameworks only. The rules JSON may still contain legacy
                # SOC2/NIST/CCM/SEC control IDs in `controls` for backwards
                # compatibility, but the analyzer output must not surface
                # any out-of-scope framework strings downstream.
                in_scope_controls = [
                    c for c in details["controls"]
                    if c.startswith("HIPAA-") or c.startswith("WA-MHMDA")
                ]
                matches.append({
                    "vulnerability": trigger,
                    "risk_type": list(RISK_LABELS),
                    "controls": in_scope_controls,
                    "granular_breakdown": _build_granular_breakdown(
                        trigger=trigger,
                        description=details.get("description", ""),
                        in_scope_controls=in_scope_controls,
                    ),
                })

        analysis = {m["vulnerability"]: m for m in matches}

        return {
            "query": query,
            "matches": len(matches),
            "analysis": analysis,
        }

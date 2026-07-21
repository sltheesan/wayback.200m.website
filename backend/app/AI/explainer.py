"""
Explainable AI — Risk Narrative Generator
==========================================
Produces human-readable, evidence-backed explanations for why a domain
received its risk score. Uses deterministic template logic (no LLM required),
so it works offline and never blocks.

The output is designed to satisfy "manager-level" readability:

  "This domain historically hosted gambling content between 2014 and 2019.
   Evidence: sports betting, casino bonuses, live roulette detected across
   14 snapshots. Structural analysis flagged 2 hidden element layers and a
   crypto wallet address. Confidence: 94%."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from backend.app.AI.classifier import CATEGORY_META, SAFE_LABEL


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExplainedRisk:
    narrative: str                      # Full English explanation paragraph
    evidence_bullets: List[str]         # Bullet-point evidence list
    primary_category: str               # e.g. "gambling"
    risk_period: str                    # e.g. "2014–2019" or "2022"
    confidence: float                   # 0.0–1.0 (from classifier)
    detector_highlights: List[str]      # High-signal structural findings
    risk_level: str                     # SAFE / MEDIUM / HIGH


# ─────────────────────────────────────────────────────────────────────────────
# Category narrative templates
# ─────────────────────────────────────────────────────────────────────────────

_NARRATIVES: Dict[str, str] = {
    "gambling": (
        "This domain {period_clause} hosted gambling and sports-betting content. "
        "Keyword analysis identified {kw_count} gambling-related signals including "
        "{kw_samples}. {detector_clause} "
        "Historical risk confidence: {confidence:.0%}."
    ),
    "adult": (
        "This domain {period_clause} contained explicit adult entertainment content. "
        "Analysis detected {kw_count} adult-content indicators including {kw_samples}. "
        "{detector_clause} "
        "Confidence: {confidence:.0%}."
    ),
    "phishing_scam": (
        "This domain {period_clause} exhibited phishing and scam-related behaviour. "
        "{kw_count} fraud-related signals were detected including {kw_samples}. "
        "{detector_clause} "
        "Confidence: {confidence:.0%}."
    ),
    "malware_hacking": (
        "This domain {period_clause} was associated with malware distribution or "
        "hacking activity. {kw_count} threat indicators found including {kw_samples}. "
        "{detector_clause} "
        "Confidence: {confidence:.0%}."
    ),
    "illegal_pharmaceuticals": (
        "This domain {period_clause} was linked to illegal pharmaceutical sales. "
        "Detected {kw_count} pharmaceutical-related signals including {kw_samples}. "
        "{detector_clause} "
        "Confidence: {confidence:.0%}."
    ),
    SAFE_LABEL: (
        "No significant threat signals were detected across {snap_count} historical "
        "snapshot{plural}. Content analysis returned safe category signatures "
        "with no flagged keywords or structural anomalies."
    ),
}

_DETECTOR_TEMPLATES: Dict[str, str] = {
    "hidden_elements":        "hidden CSS elements (possible cloaking)",
    "crypto_wallets":         "cryptocurrency wallet addresses",
    "forms":                  "password-collection forms (phishing indicator)",
    "iframe_redirects":       "iframe injections and JavaScript redirects",
    "url_obfuscation":        "heavily obfuscated URLs",
    "external_link_density":  "high external link density",
    "phone_numbers":          "multiple phone number patterns",
    "content_length":         "anomalous page size",
}


# ─────────────────────────────────────────────────────────────────────────────
# Core explainer
# ─────────────────────────────────────────────────────────────────────────────

def build_explanation(
    primary_category: str,
    confidence: float,
    risk_level: str,
    snapshot_results: List[Dict[str, Any]],
) -> ExplainedRisk:
    """
    Build a full risk explanation from the pipeline's snapshot results.

    Parameters
    ----------
    primary_category : str
        Dominant threat category (from classifier).
    confidence : float
        Classification confidence (0.0–1.0).
    risk_level : str
        'SAFE', 'MEDIUM', or 'HIGH'.
    snapshot_results : list
        List of snapshot dicts returned by the pipeline's fetch_and_analyze.

    Returns
    -------
    ExplainedRisk
        Structured explanation object.
    """
    snap_count = len(snapshot_results)

    # ── Collect evidence from all snapshots ───────────────────────────────
    all_keywords: Dict[str, int] = {}   # keyword → total match count
    high_detector_signals: Dict[str, int] = {}  # detector_name → count of highs
    risky_years: List[str] = []

    for snap in snapshot_results:
        year = (snap.get("timestamp") or "")[:4]

        # Keyword evidence
        for flag in snap.get("flags", []):
            kw = flag.get("keyword", "")
            all_keywords[kw] = all_keywords.get(kw, 0) + flag.get("match_count", 1)

        # Structural detector evidence (from extraction_metadata JSON)
        meta_json = snap.get("extraction_metadata")
        if meta_json:
            try:
                meta = json.loads(meta_json)
                for det in meta.get("detectors", []):
                    if det.get("signal") == "high":
                        dname = det.get("detector", "")
                        high_detector_signals[dname] = high_detector_signals.get(dname, 0) + 1
            except Exception:
                pass

        # Track risky years
        if snap.get("risk_score", 0) > 30 and year:
            risky_years.append(year)

    # ── Compute risk period ───────────────────────────────────────────────
    if risky_years:
        min_y, max_y = min(risky_years), max(risky_years)
        risk_period = min_y if min_y == max_y else f"{min_y}–{max_y}"
    else:
        risk_period = "recently"

    # ── Top keywords ──────────────────────────────────────────────────────
    sorted_kws = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)
    top_kws = [k for k, _ in sorted_kws[:5]]
    kw_samples_str = ", ".join(f'"{k}"' for k in top_kws[:3]) if top_kws else "multiple indicators"
    kw_count = len(all_keywords)

    # ── Detector highlights ───────────────────────────────────────────────
    detector_bullets: List[str] = []
    for dname, count in sorted(high_detector_signals.items(), key=lambda x: x[1], reverse=True)[:3]:
        label = _DETECTOR_TEMPLATES.get(dname, dname.replace("_", " "))
        detector_bullets.append(f"Structural analysis detected {label} in {count} snapshot(s).")

    detector_clause = " ".join(detector_bullets) if detector_bullets else ""

    # ── Period clause ─────────────────────────────────────────────────────
    if risky_years:
        period_clause = f"historically ({risk_period})"
    else:
        period_clause = "was found to have"

    # If primary category is safe and confidence is 0, default confidence to 1.0 (100% safe confidence)
    if primary_category == SAFE_LABEL and (confidence == 0.0 or confidence is None):
        confidence = 1.0

    # ── Build narrative ───────────────────────────────────────────────────
    tpl = _NARRATIVES.get(primary_category, _NARRATIVES[SAFE_LABEL])
    try:
        narrative = tpl.format(
            period_clause=period_clause,
            kw_count=kw_count,
            kw_samples=kw_samples_str,
            detector_clause=detector_clause,
            confidence=confidence,
            snap_count=snap_count,
            plural="s" if snap_count != 1 else "",
        )
    except KeyError:
        narrative = f"Risk level: {risk_level}. Category: {primary_category}."

    # ── Evidence bullet list ──────────────────────────────────────────────
    evidence_bullets: List[str] = []
    if top_kws:
        evidence_bullets.append(f"Keywords detected: {', '.join(top_kws)}")
    if kw_count > len(top_kws):
        evidence_bullets.append(f"{kw_count - len(top_kws)} additional unique keyword signals found")
    evidence_bullets.extend(detector_bullets)
    evidence_bullets.append(f"Analysed {snap_count} historical snapshot(s)")
    if risky_years:
        evidence_bullets.append(f"Risk period: {risk_period}")

    # ── Category meta label ───────────────────────────────────────────────
    meta = CATEGORY_META.get(primary_category, {})
    icon = meta.get("icon", "⚠️")
    cat_label = meta.get("label", primary_category.replace("_", " ").title())

    return ExplainedRisk(
        narrative=narrative.strip(),
        evidence_bullets=evidence_bullets,
        primary_category=primary_category,
        risk_period=risk_period,
        confidence=confidence,
        detector_highlights=detector_bullets,
        risk_level=risk_level,
    )

"""
Timeline Service — Year-Level Historical Intelligence Builder
=============================================================
Converts a flat list of snapshot analysis results into a chronological
year-by-year timeline, grouping snapshots by year and computing:
  - Dominant threat category for that year
  - Average and peak risk scores
  - Snapshot count
  - Auto-generated year summary
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from backend.app.AI.classifier import CATEGORY_META, SAFE_LABEL


# ─────────────────────────────────────────────────────────────────────────────
# Year summary templates
# ─────────────────────────────────────────────────────────────────────────────

_YEAR_SUMMARY_TEMPLATES: Dict[str, str] = {
    "gambling":   "{year}: Gambling content detected across {count} snapshot(s). Avg risk: {avg:.0f}.",
    "adult":      "{year}: Adult content present in {count} snapshot(s). Avg risk: {avg:.0f}.",
    "phishing_scam":    "{year}: Phishing/scam indicators found in {count} snapshot(s). Avg risk: {avg:.0f}.",
    "malware_hacking":  "{year}: Malware/hacking signals in {count} snapshot(s). Avg risk: {avg:.0f}.",
    "illegal_pharmaceuticals": "{year}: Illegal pharma signals in {count} snapshot(s). Avg risk: {avg:.0f}.",
    "server_error": "{year}: Server error captures (HTTP 503/500/404) recorded across {count} snapshot(s). Avg risk: {avg:.0f}.",
    "unavailable":  "{year}: Dead domain captures recorded across {count} snapshot(s). Avg risk: {avg:.0f}.",
    SAFE_LABEL:   "{year}: Content appeared safe across {count} snapshot(s). Avg risk: {avg:.0f}.",
}


def build_timeline(snapshot_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a year-level timeline from per-snapshot analysis results.

    Parameters
    ----------
    snapshot_results : list
        Each item is the dict returned by `fetch_and_analyze` in pipeline.py.

    Returns
    -------
    list
        Sorted list of year-level timeline dicts, ready for DB insertion
        or direct API serialisation.
        Each item: {year, category, risk_score (avg), peak_score,
                    snapshot_count, summary}
    """
    # Group snapshots by year
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for snap in snapshot_results:
        ts = snap.get("timestamp", "")
        try:
            year = int(ts[:4])
        except (ValueError, TypeError):
            continue
        by_year.setdefault(year, []).append(snap)

    timeline: List[Dict[str, Any]] = []

    for year in sorted(by_year.keys()):
        snaps = by_year[year]
        scores = [s.get("risk_score", 0) for s in snaps]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        peak_score = max(scores) if scores else 0

        # Dominant category for the year
        categories = [s.get("content_category") or SAFE_LABEL for s in snaps]
        cat_counter = Counter(categories)
        # Prefer non-safe categories if they appear at all
        non_safe = [(c, n) for c, n in cat_counter.items() if c != SAFE_LABEL]
        if non_safe:
            dominant_cat = max(non_safe, key=lambda x: x[1])[0]
        else:
            dominant_cat = SAFE_LABEL

        # Year summary string
        tpl = _YEAR_SUMMARY_TEMPLATES.get(dominant_cat, _YEAR_SUMMARY_TEMPLATES[SAFE_LABEL])
        summary = tpl.format(year=year, count=len(snaps), avg=avg_score)

        meta = CATEGORY_META.get(dominant_cat, {})

        timeline.append({
            "year": year,
            "category": dominant_cat,
            "category_label": meta.get("label", dominant_cat.replace("_", " ").title()),
            "category_icon": meta.get("icon", "❓"),
            "risk_score": round(avg_score, 1),
            "peak_score": peak_score,
            "snapshot_count": len(snaps),
            "summary": summary,
        })

    return timeline


def get_primary_category(timeline: List[Dict[str, Any]]) -> str:
    """Return the most frequently flagged non-safe category across all years."""
    cat_counts: Counter = Counter()
    for entry in timeline:
        cat = entry.get("category", SAFE_LABEL)
        if cat != SAFE_LABEL:
            cat_counts[cat] += entry.get("snapshot_count", 1)
    if cat_counts:
        return cat_counts.most_common(1)[0][0]
    return SAFE_LABEL

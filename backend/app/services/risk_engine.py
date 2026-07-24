import random
from typing import List, Dict, Any, Tuple
from backend.app.utils.logger import logger

# Number of snapshots to sample for analysis
SNAPSHOT_SAMPLE_SIZE = 10


def select_snapshots_to_check(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns all snapshots for analysis, sorted chronologically.
    """
    sorted_snapshots = sorted(snapshots, key=lambda s: s.get("timestamp", ""))
    logger.info(f"Selected all {len(sorted_snapshots)} snapshots for analysis.")
    return sorted_snapshots


def compute_overall_risk(snapshot_results: List[Dict[str, Any]]) -> Tuple[int, str, int, int]:
    """
    Computes the overall risk score and level from a list of snapshot results.
    Aligns with Phase 8 - Domain Decision mapping (Safe / Medium / High).
    """
    if not snapshot_results:
        return 0, "SAFE", 0, 0

    # Filter valid snapshots (including redirects and analyzed captures)
    valid_snaps = []
    for s in snapshot_results:
        if isinstance(s, (int, float)):
            valid_snaps.append({"risk_score": int(s), "content_category": "safe"})
        elif isinstance(s, dict):
            if s.get("is_redirect") or s.get("content_category") not in ["unavailable", "invalid"] or s.get("risk_score", 0) > 0:
                valid_snaps.append(s)
            elif s.get("status_code"):
                valid_snaps.append(s)

    if not valid_snaps:
        valid_snaps = [s for s in snapshot_results if isinstance(s, dict)]

    if not valid_snaps:
        return 0, "SAFE", 0, 0

    scores = [s.get("risk_score", 0) for s in valid_snaps]
    peak_score = max(scores)
    avg_score = sum(scores) / len(scores)

    # Weighted combination: peak heavily influences final score
    final_score = int(round(peak_score * 0.6 + avg_score * 0.4))
    if peak_score >= 80:
        # High-severity threats (gambling/adult redirects, phishing) elevate final score
        final_score = max(final_score, 70)
    final_score = min(final_score, 100)

    avg_score_rounded = int(round(avg_score))

    # Classify risk level based on final score
    if final_score > 60:
        risk_level = "HIGH"
    elif final_score > 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "SAFE"

    return final_score, risk_level, peak_score, avg_score_rounded

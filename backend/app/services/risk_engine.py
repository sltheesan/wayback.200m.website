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
    Aligns with Phase 8 - Domain Decision mapping (Safe / Unsafe / Unknown).
    """
    if not snapshot_results:
        return 0, "UNKNOWN", 0, 0

    # Filter out unavailable or invalid snapshots
    valid_snaps = [s for s in snapshot_results if s.get("content_category") not in ["unavailable", "invalid"]]
    
    if not valid_snaps:
        # Every snapshot was unavailable or invalid
        return 0, "UNKNOWN", 0, 0

    scores = [s["risk_score"] for s in valid_snaps]
    peak_score = max(scores)
    avg_score = sum(scores) / len(scores)

    # Weighted combination: peak heavily influences final score
    final_score = int(round(peak_score * 0.6 + avg_score * 0.4))
    final_score = min(final_score, 100)

    avg_score_rounded = int(round(avg_score))

    # Classify as UNSAFE if one or more snapshots contain confirmed evidence of prohibited content
    has_unsafe = any(s.get("risk_score", 0) > 30 or s.get("content_category", "safe") != "safe" for s in valid_snaps)
    
    if has_unsafe:
        risk_level = "UNSAFE"
    else:
        risk_level = "SAFE"

    return final_score, risk_level, peak_score, avg_score_rounded

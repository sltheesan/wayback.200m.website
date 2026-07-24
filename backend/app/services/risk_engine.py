import random
from typing import List, Dict, Any, Tuple
from backend.app.utils.logger import logger

# Number of snapshots to sample for analysis
SNAPSHOT_SAMPLE_SIZE = 10


def _snap_get(snap: Any, key: str, default: Any = None) -> Any:
    if isinstance(snap, dict):
        return snap.get(key, default)
    return getattr(snap, key, default)


def select_snapshots_to_check(snapshots: List[Any]) -> List[Any]:
    """
    Returns all snapshots for analysis, sorted chronologically.
    Accepts both dict items and Snapshot ORM objects safely.
    """
    sorted_snapshots = sorted(snapshots, key=lambda s: str(_snap_get(s, "timestamp", "") or ""))
    logger.info(f"Selected all {len(sorted_snapshots)} snapshots for analysis.")
    return sorted_snapshots


def compute_overall_risk(snapshot_results: List[Any]) -> Tuple[int, str, int, int]:
    """
    Computes the overall risk score and level from a list of snapshot results.
    Accepts both dict items and Snapshot ORM objects safely.
    """
    if not snapshot_results:
        return 0, "SAFE", 0, 0

    # Filter valid snapshots (including redirects and analyzed captures)
    valid_snaps = []
    for s in snapshot_results:
        if isinstance(s, (int, float)):
            valid_snaps.append({"risk_score": int(s), "content_category": "safe"})
        else:
            is_redir = _snap_get(s, "is_redirect", False)
            cat = _snap_get(s, "content_category")
            r_score = int(_snap_get(s, "risk_score", 0) or 0)
            st_code = _snap_get(s, "status_code")
            if is_redir or cat not in ["unavailable", "invalid"] or r_score > 0 or st_code:
                valid_snaps.append(s)

    if not valid_snaps:
        valid_snaps = list(snapshot_results)

    if not valid_snaps:
        return 0, "SAFE", 0, 0

    scores = [int(_snap_get(s, "risk_score", 0) or 0) for s in valid_snaps]
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

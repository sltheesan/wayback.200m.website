import asyncio
import datetime
import json
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.redis import redis_manager
from backend.app.models.domain import Domain
from backend.app.models.snapshot import Snapshot
from backend.app.models.analysis import AnalysisFlag
from backend.app.models.timeline import DomainTimeline
from backend.app.models.threat_intel import ThreatIntelligence
from backend.app.services.cdx_service import fetch_snapshots_with_proxy_rotation
from backend.app.services.snapshot_fetcher import fetch_snapshot_html, fetch_live_domain_html
from backend.app.services.analyzer import analyze_snapshot_content, get_language
from backend.app.services.risk_engine import select_snapshots_to_check, compute_overall_risk
from backend.app.services.timeline_service import build_timeline, get_primary_category
from backend.app.services.threat_intel import query_all_providers, overall_threat_status
from backend.app.AI.classifier import classify_content, result_to_metadata_json
from backend.app.AI.detectors import run_all_detectors, high_signal_count
from backend.app.AI.explainer import build_explanation
from backend.app.utils.logger import logger

def build_snapshot_evidence_url(timestamp: str, original_url: str, risk_score: int, flags: list, source: str = "archive") -> str | None:
    """Return a visual evidence URL for snapshots that crossed an unsafe threshold."""
    if risk_score < 40 and not flags:
        return None
    if not original_url:
        return None
    if source == "live":
        return original_url
    return f"https://web.archive.org/web/{timestamp}if_/{original_url}"


async def analyze_domain_pipeline(domain: str, force_refresh: bool, db: AsyncSession) -> dict:
    """
    Coordinates the entire domain analysis process.
    1. Checks Redis cache.
    2. Checks PostgreSQL DB (and checks if stale).
    3. Runs CDX search, fetches content, computes risk, and saves.
    """
    domain_clean = domain.strip().lower()
    cache_key = f"domain_analysis:{domain_clean}"

    # 1. Check Redis Cache
    if not force_refresh:
        cached_result = await redis_manager.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT for domain: {domain_clean}")
            return cached_result
        logger.info(f"Cache MISS for domain: {domain_clean}")

    # 2. Check PostgreSQL DB
    query = (
        select(Domain)
        .options(
            selectinload(Domain.snapshots).selectinload(Snapshot.flags),
            selectinload(Domain.timeline),
            selectinload(Domain.threat_intel),
        )
        .where(Domain.name == domain_clean)
    )
    result = await db.execute(query)
    db_domain = result.scalar_one_or_none()

    if db_domain and not force_refresh:
        # Check if the analysis is fresh (within 7 days)
        age = datetime.datetime.utcnow() - db_domain.last_analyzed_at
        if age.days < 7:
            logger.info(f"Database HIT (fresh analysis) for domain: {domain_clean}")
            # Format and return from DB
            response_data = format_domain_response(db_domain)
            # Re-populate cache
            await redis_manager.set(cache_key, response_data)
            return response_data
        logger.info(f"Database analysis for {domain_clean} is STALE ({age.days} days old). Re-analyzing.")

    # 3. Fetch snapshots list from CDX, rotating proxies before failing.
    raw_snapshots, cdx_proxy_used = await fetch_snapshots_with_proxy_rotation(domain_clean, force_refresh=force_refresh)
    if cdx_proxy_used:
        logger.info(f"CDX snapshots for {domain_clean} succeeded via proxy: {cdx_proxy_used}")
    # Also inspect the current homepage. Some repurposed domains have no useful
    # archive captures, and image-heavy adult pages can otherwise be missed.
    live_html, live_url = await fetch_live_domain_html(domain_clean)
    live_timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")

    if raw_snapshots is None:
        if db_domain:
            logger.warning(f"Wayback Machine CDX API is unreachable for {domain_clean}. Falling back to existing database record.")
            return format_domain_response(db_domain)
        if not live_html:
            raise RuntimeError("Wayback Machine CDX API is temporarily unreachable or returned a bad response, and the live domain homepage could not be reached. Please try again.")
        logger.warning(f"Wayback Machine CDX API is unreachable for {domain_clean}. Falling back to live homepage scan.")
        raw_snapshots = []

    if len(raw_snapshots) == 0 and not live_html:
        # Save a default safe/empty record to database to avoid DOSing CDX API on non-existent domains
        logger.warning(f"No archive snapshots or live homepage content found for {domain_clean}")
        db_domain = await save_empty_domain(domain_clean, db)
        empty_response = format_domain_response(db_domain)
        await redis_manager.set(cache_key, empty_response)
        return empty_response

    # 4. Chronologically sort snapshots
    sorted_snapshots = select_snapshots_to_check(raw_snapshots)
    if live_html:
        sorted_snapshots.append({
            "timestamp": live_timestamp,
            "original": live_url or f"https://{domain_clean}/",
            "statuscode": "200",
            "mime": "text/html",
            "digest": f"live:{live_timestamp}",
            "html_content": live_html,
            "source": "live",
        })

    # Group snapshots by digest to de-duplicate fetches.
    # If digest is missing/empty, treat it as a unique snapshot using its timestamp.
    digests_map = {}
    for snap in sorted_snapshots:
        digest_val = snap.get("digest") or snap.get("timestamp")
        digests_map.setdefault(digest_val, []).append(snap)

    # For each unique digest, select the latest snapshot.
    all_unique_snapshots = []
    for digest_val, snaps_group in digests_map.items():
        all_unique_snapshots.append(snaps_group[-1])

    # Sort chronologically to sample accurately
    all_unique_snapshots.sort(key=lambda s: s["timestamp"])

    # Sample up to 6 representative unique snapshots to fetch and analyze HTML for, preventing timeouts
    max_samples = 6
    if len(all_unique_snapshots) <= max_samples:
        unique_snapshots_to_fetch = all_unique_snapshots
    else:
        indices = {0, len(all_unique_snapshots) - 1}
        step = (len(all_unique_snapshots) - 1) / (max_samples - 1)
        for i in range(1, max_samples - 1):
            indices.add(int(round(i * step)))
        unique_snapshots_to_fetch = [all_unique_snapshots[idx] for idx in sorted(indices)]

    # 5. Fetch and analyze snapshot HTML contents sequentially in chronological order
    async def fetch_and_analyze(snap: dict) -> dict:
        timestamp = snap["timestamp"]
        original = snap["original"]
        status = int(snap["statuscode"]) if snap.get("statuscode") else 200
        mime = snap.get("mime", "text/html")

        # Fetch the HTML content. Live captures are already loaded; archive
        # captures are fetched through Wayback's raw snapshot endpoint.
        html_content = snap.get("html_content")
        if html_content is None:
            html_content = await fetch_snapshot_html(timestamp, original, domain_clean)

        # Phase 2 check: If download failed
        if not html_content:
            metadata = {
                "status": "unavailable",
                "reason": "Download failed across all proxy attempts",
                "image_detections": [],
                "classifier": {
                    "primary_category": "safe",
                    "confidence": 0.0,
                    "all_scores": {},
                    "detected_language": "en",
                    "summary": "Snapshot unavailable",
                },
                "detectors": {},
                "detector_boost": 0,
                "evidence_url": None
            }
            return {
                "timestamp": timestamp,
                "original_url": original,
                "status_code": status,
                "mime_type": mime,
                "risk_score": 0,
                "detected_language": "en",
                "category_scores": {},
                "flags": [],
                "content_category": "unavailable",
                "category_confidence": 0.0,
                "content_summary": "Snapshot unavailable or failed to download.",
                "extraction_metadata": json.dumps(metadata, ensure_ascii=False),
                "evidence_url": None,
            }

        # Phase 3 check: Validate HTML content
        from backend.app.services.analyzer import validate_snapshot_html
        is_valid, invalid_reason = validate_snapshot_html(html_content)
        if not is_valid:
            metadata = {
                "status": "invalid",
                "reason": invalid_reason,
                "image_detections": [],
                "classifier": {
                    "primary_category": "safe",
                    "confidence": 0.0,
                    "all_scores": {},
                    "detected_language": "en",
                    "summary": f"Invalid snapshot: {invalid_reason}",
                },
                "detectors": {},
                "detector_boost": 0,
                "evidence_url": None
            }
            return {
                "timestamp": timestamp,
                "original_url": original,
                "status_code": status,
                "mime_type": mime,
                "risk_score": 0,
                "detected_language": "en",
                "category_scores": {},
                "flags": [],
                "content_category": "invalid",
                "category_confidence": 0.0,
                "content_summary": f"Invalid snapshot: {invalid_reason}",
                "extraction_metadata": json.dumps(metadata, ensure_ascii=False),
                "evidence_url": None,
            }

        # Legacy keyword scorer (already enriches flags with match location details)
        risk_score, category_scores, flags = analyze_snapshot_content(html_content, domain_clean)

        # AI Classifier
        from backend.app.utils.text_cleaner import clean_html_content
        cleaned_text = clean_html_content(html_content).lower()
        lang = get_language(cleaned_text)

        clf_result = classify_content(html_content, domain_clean)

        # Phase 5: Image Analysis
        from backend.app.services.analyzer import classify_images_in_html
        image_detections = classify_images_in_html(html_content, domain_clean)
        image_threats = [d for d in image_detections if d["category"] != "safe"]

        # Boost risk score if unsafe images are found
        image_boost = 0
        if image_threats:
            image_boost = 60
        
        # Promote primary classification category to top image threat if text was deemed safe
        primary_cat = clf_result.primary_category
        confidence = clf_result.confidence
        summary = clf_result.summary
        
        if primary_cat == "safe" and image_threats:
            primary_cat = image_threats[0]["category"]
            confidence = max(d["confidence_score"] for d in image_threats)
            summary = f"Threat content identified via historical image checks: {image_threats[0]['evidence_description']}"

        # Structural Detectors
        detector_results = run_all_detectors(html_content, cleaned_text, clf_result)
        high_signals = high_signal_count(detector_results)

        # Boost risk score when structural detectors fire (max +15)
        detector_boost = min(high_signals * 5, 15)
        final_risk_score = min(risk_score + detector_boost + image_boost, 100)

        # Align content classification category and risk score consistency
        if final_risk_score <= 30:
            primary_cat = "safe"
        elif primary_cat == "safe":
            # If risk score is unsafe, assign it to the top matching category from legacy keyword analyzer
            if category_scores:
                max_legacy_cat = max(category_scores, key=category_scores.get)
                if category_scores[max_legacy_cat] > 0:
                    primary_cat = max_legacy_cat
            if primary_cat == "safe" and flags:
                primary_cat = flags[0]["category"]
            # Fallback if no specific categories triggered
            if primary_cat == "safe":
                primary_cat = "phishing_scam"

        if primary_cat != "safe" and final_risk_score < 40:
            final_risk_score = 40

        evidence_url = build_snapshot_evidence_url(
            timestamp, original, final_risk_score, flags, snap.get("source", "archive")
        )

        # Serialise full AI intelligence payload including Phase 5/6/7 details
        metadata = {
            "status": "success",
            "classifier": {
                "primary_category": primary_cat,
                "confidence": confidence,
                "all_scores": clf_result.all_scores,
                "detected_language": clf_result.detected_language,
                "summary": summary,
            },
            "detectors": detector_results,
            "detector_boost": detector_boost,
            "image_boost": image_boost,
            "image_detections": image_detections,
            "evidence_url": evidence_url,
        }
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        return {
            "timestamp": timestamp,
            "original_url": original,
            "status_code": status,
            "mime_type": mime,
            "risk_score": final_risk_score,
            "detected_language": lang,
            "category_scores": category_scores,
            "flags": flags,
            # AI intelligence fields
            "content_category": primary_cat,
            "category_confidence": confidence,
            "content_summary": summary,
            "extraction_metadata": metadata_json,
            "evidence_url": evidence_url,
        }

    # Fetch and analyze sequentially (Phase 2 chronological)
    logger.info(f"Fetching and analyzing {len(unique_snapshots_to_fetch)} unique snapshots sequentially for {domain_clean}...")
    unique_results = []
    for snap in unique_snapshots_to_fetch:
        res = await fetch_and_analyze(snap)
        unique_results.append(res)

    # Build lookup map from digest/timestamp -> analysis result
    analysis_by_digest = {}
    for res, snap_orig in zip(unique_results, unique_snapshots_to_fetch):
        digest_key = snap_orig.get("digest") or snap_orig.get("timestamp")
        analysis_by_digest[digest_key] = res

    # Interpolate results for non-fetched unique snapshots from the closest analyzed snapshot in time
    for snap in all_unique_snapshots:
        digest_key = snap.get("digest") or snap.get("timestamp")
        if digest_key not in analysis_by_digest and unique_snapshots_to_fetch:
            closest_snap = min(
                unique_snapshots_to_fetch,
                key=lambda s: abs(int(s["timestamp"]) - int(snap["timestamp"]))
            )
            closest_digest = closest_snap.get("digest") or closest_snap.get("timestamp")
            closest_res = analysis_by_digest.get(closest_digest)
            if closest_res:
                analysis_by_digest[digest_key] = {
                    **closest_res,
                    "timestamp": snap["timestamp"],
                    "original_url": snap["original"],
                    "status_code": int(snap["statuscode"]) if snap.get("statuscode") else 200,
                    "mime_type": snap.get("mime", "text/html"),
                }

    # Map the unique analysis results back to all snapshots to reconstruct full timeline history
    snapshot_results = []
    for snap in sorted_snapshots:
        digest_key = snap.get("digest") or snap.get("timestamp")
        res = analysis_by_digest.get(digest_key)
        if res:
            snapshot_results.append({
                "timestamp": snap["timestamp"],
                "original_url": snap["original"],
                "status_code": int(snap["statuscode"]) if snap.get("statuscode") else 200,
                "mime_type": snap.get("mime", "text/html"),
                "risk_score": res["risk_score"],
                "detected_language": res["detected_language"],
                "category_scores": res["category_scores"].copy(),
                "flags": [f.copy() for f in res["flags"]],
                "content_category": res.get("content_category"),
                "category_confidence": res.get("category_confidence"),
                "content_summary": res.get("content_summary"),
                "extraction_metadata": res.get("extraction_metadata"),
                "evidence_url": res.get("evidence_url"),
            })

    # 6. Compute overall risk metrics
    overall_score, overall_level, peak_score, avg_score = compute_overall_risk(list(snapshot_results))

    # Build history summary
    history_summary = []
    for snap in snapshot_results:
        year = snap["timestamp"][:4] if snap["timestamp"] else "?"
        categories = list({f["category"] for f in snap["flags"]})
        history_summary.append({
            "timestamp": snap["timestamp"],
            "year": year,
            "risk_score": snap["risk_score"],
            "categories": categories
        })
    history_summary.sort(key=lambda x: x["timestamp"])

    # Aggregate peak category confidences
    category_confidence = {}
    unique_flags = set()
    for snap in snapshot_results:
        for cat, score in snap["category_scores"].items():
            if score > category_confidence.get(cat, 0):
                category_confidence[cat] = score
        for flag in snap["flags"]:
            unique_flags.add(flag["category"])

    # 6b. Build year-level timeline
    timeline_entries = build_timeline(list(snapshot_results))
    primary_category = get_primary_category(timeline_entries)

    # 6c. AI Explanation
    top_confidence = max(
        (s.get("category_confidence") or 0.0 for s in snapshot_results), default=0.0
    )
    explanation = build_explanation(
        primary_category=primary_category,
        confidence=top_confidence,
        risk_level=overall_level,
        snapshot_results=list(snapshot_results),
    )

    # 6d. Threat Intelligence
    threat_intel_results = await query_all_providers(domain_clean)
    threat_overall = overall_threat_status(threat_intel_results)

    # 7. Persist to PostgreSQL database
    if db_domain:
        db_domain.risk_score = overall_score
        db_domain.risk_level = overall_level
        db_domain.last_analyzed_at = datetime.datetime.utcnow()
        db_domain.primary_category = primary_category
        db_domain.risk_narrative = explanation.narrative
        db_domain.last_threat_intel_at = datetime.datetime.utcnow()
        db_domain.snapshots.clear()
        db_domain.timeline.clear()
        db_domain.threat_intel.clear()
    else:
        db_domain = Domain(
            name=domain_clean,
            risk_score=overall_score,
            risk_level=overall_level,
            last_analyzed_at=datetime.datetime.utcnow(),
            primary_category=primary_category,
            risk_narrative=explanation.narrative,
            last_threat_intel_at=datetime.datetime.utcnow(),
        )
        db.add(db_domain)
        db_domain.snapshots = []
        db_domain.timeline = []
        db_domain.threat_intel = []

    await db.flush()

    # Snapshots + flags
    for snap_res in snapshot_results:
        db_snap = Snapshot(
            timestamp=snap_res["timestamp"],
            original_url=snap_res["original_url"],
            status_code=snap_res["status_code"],
            mime_type=snap_res["mime_type"],
            risk_score=snap_res["risk_score"],
            detected_language=snap_res["detected_language"],
            content_category=snap_res.get("content_category"),
            category_confidence=snap_res.get("category_confidence"),
            content_summary=snap_res.get("content_summary"),
            extraction_metadata=snap_res.get("extraction_metadata"),
        )
        db_domain.snapshots.append(db_snap)
        for flag_res in snap_res["flags"]:
            db_snap.flags.append(AnalysisFlag(
                category=flag_res["category"],
                keyword=flag_res["keyword"],
                weight=flag_res["weight"],
                match_count=flag_res["match_count"],
            ))

    # Timeline rows
    for entry in timeline_entries:
        db_domain.timeline.append(DomainTimeline(
            year=entry["year"],
            category=entry["category"],
            risk_score=entry["risk_score"],
            peak_score=entry["peak_score"],
            snapshot_count=entry["snapshot_count"],
            summary=entry["summary"],
        ))

    # Threat intel rows
    for ti in threat_intel_results:
        db_domain.threat_intel.append(ThreatIntelligence(
            provider=ti["provider"],
            status=ti["status"],
            confidence=ti.get("confidence"),
            verdict=ti.get("verdict"),
            raw_response=ti.get("raw_response"),
            fetched_at=datetime.datetime.utcnow(),
        ))

    await db.commit()
    logger.info(f"Saved full intelligence results to DB for {domain_clean}")

    # Re-query Domain object to ensure relationships are loaded properly
    stmt = select(Domain).options(selectinload(Domain.snapshots)).where(Domain.name == domain_clean)
    refreshed_result = await db.execute(stmt)
    refreshed_domain = refreshed_result.scalar_one()

    # 8. Build and cache final response
    final_response = {
        "domain": domain_clean,
        "risk_score": overall_score,
        "risk_level": overall_level,
        "peak_score": peak_score,
        "avg_score": avg_score,
        "category_confidence": category_confidence,
        "flags": sorted(list(unique_flags)),
        "snapshots_checked": len(snapshot_results),
        "history_summary": history_summary,
        "snapshots": list(snapshot_results),
        "last_analyzed_at": db_domain.last_analyzed_at.isoformat(),
        "last_updated": db_domain.last_analyzed_at.isoformat(),
        # Intelligence enrichments
        "primary_category": primary_category,
        "risk_narrative": explanation.narrative,
        "evidence_bullets": explanation.evidence_bullets,
        "risk_period": explanation.risk_period,
        "ai_confidence": explanation.confidence,
        "timeline": timeline_entries,
        "threat_intel": threat_intel_results,
        "threat_overall": threat_overall,
        "cdx_proxy_used": cdx_proxy_used,
    }

    await redis_manager.set(cache_key, final_response)
    return final_response

def format_domain_response(
    domain: Domain,
    peak_score: int = 0,
    avg_score: int = 0,
    history_summary: list = None,
    category_confidence: dict = None
) -> dict:
    """Formats a DB Domain object into the standard API dictionary."""
    snapshots_list = []
    unique_categories = set()
    history = []
    scores = []
    confidence_by_category = dict(category_confidence or {})

    for s in domain.snapshots:
        flags_list = []
        for f in s.flags:
            flags_list.append({
                "category": f.category,
                "keyword": f.keyword,
                "weight": f.weight,
                "match_count": f.match_count
            })
            unique_categories.add(f.category)

        scores.append(s.risk_score)
        history.append({
            "timestamp": s.timestamp,
            "year": s.timestamp[:4] if s.timestamp else "?",
            "risk_score": s.risk_score,
            "categories": sorted({f.category for f in s.flags}),
        })

        raw_meta = getattr(s, "extraction_metadata", None)
        if raw_meta:
            try:
                parsed_meta = json.loads(raw_meta)
                all_scores = parsed_meta.get("classifier", {}).get("all_scores", {}) or {}
                for category, score in all_scores.items():
                    if score > confidence_by_category.get(category, 0):
                        confidence_by_category[category] = score
            except Exception:
                pass

        evidence_url = None
        if raw_meta:
            try:
                evidence_url = json.loads(raw_meta).get("evidence_url")
            except Exception:
                evidence_url = None
        if not evidence_url:
            evidence_url = build_snapshot_evidence_url(s.timestamp, s.original_url, s.risk_score, flags_list)

        snapshots_list.append({
            "timestamp": s.timestamp,
            "original_url": s.original_url,
            "status_code": s.status_code,
            "mime_type": s.mime_type,
            "risk_score": s.risk_score,
            "detected_language": getattr(s, "detected_language", None) or "en",
            # AI classification fields
            "content_category": getattr(s, "content_category", None),
            "category_confidence": getattr(s, "category_confidence", None),
            "content_summary": getattr(s, "content_summary", None),
            "extraction_metadata": getattr(s, "extraction_metadata", None),
            "evidence_url": evidence_url,
            "flags": flags_list
        })

    timeline = [
        {
            "year": entry.year,
            "category": entry.category or "safe",
            "category_label": None,
            "category_icon": None,
            "risk_score": entry.risk_score,
            "peak_score": entry.peak_score,
            "snapshot_count": entry.snapshot_count,
            "summary": entry.summary,
        }
        for entry in sorted(domain.timeline, key=lambda item: item.year)
    ]

    threat_intel = [
        {
            "provider": item.provider,
            "status": item.status,
            "confidence": item.confidence,
            "verdict": item.verdict,
            "raw_response": item.raw_response,
            "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        }
        for item in domain.threat_intel
    ]

    return {
        "domain": domain.name,
        "risk_score": domain.risk_score,
        "risk_level": domain.risk_level,
        "peak_score": peak_score or (max(scores) if scores else 0),
        "avg_score": avg_score or (round(sum(scores) / len(scores)) if scores else 0),
        "category_confidence": confidence_by_category,
        "flags": sorted(list(unique_categories)),
        "snapshots_checked": len(domain.snapshots),
        "history_summary": history_summary or sorted(history, key=lambda x: x["timestamp"]),
        "snapshots": sorted(snapshots_list, key=lambda x: x["timestamp"]),
        "last_analyzed_at": domain.last_analyzed_at.isoformat(),
        "last_updated": domain.last_analyzed_at.isoformat(),
        "primary_category": domain.primary_category,
        "risk_narrative": domain.risk_narrative,
        "evidence_bullets": None,
        "risk_period": None,
        "ai_confidence": max(confidence_by_category.values(), default=None),
        "timeline": timeline,
        "threat_intel": threat_intel,
        "threat_overall": overall_threat_status(threat_intel) if threat_intel else None,
    }

async def save_empty_domain(domain_name: str, db: AsyncSession) -> Domain:
    """Saves a domain with 0 risk and no snapshots if none exist on CDX."""
    query = (
        select(Domain)
        .options(
            selectinload(Domain.snapshots),
            selectinload(Domain.timeline),
            selectinload(Domain.threat_intel)
        )
        .where(Domain.name == domain_name)
    )
    result = await db.execute(query)
    db_domain = result.scalar_one_or_none()

    if db_domain:
        db_domain.risk_score = 0
        db_domain.risk_level = "UNKNOWN"
        db_domain.last_analyzed_at = datetime.datetime.utcnow()
        db_domain.snapshots.clear()
        db_domain.timeline.clear()
        db_domain.threat_intel.clear()
    else:
        db_domain = Domain(
            name=domain_name,
            risk_score=0,
            risk_level="UNKNOWN",
            last_analyzed_at=datetime.datetime.utcnow(),
            snapshots=[],
            timeline=[],
            threat_intel=[]
        )
        db.add(db_domain)

    await db.commit()
    return db_domain





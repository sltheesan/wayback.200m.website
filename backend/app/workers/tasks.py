import asyncio
import nest_asyncio
import time
import json
from datetime import datetime, timedelta
from sqlalchemy import delete
from backend.app.workers.celery_worker import celery_app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.login_history import LoginHistory
from backend.app.models.activity_log import ActivityLog
from backend.app.models.notification import Notification
from backend.app.models.scan_record import ScanRecord, ScanSource
from backend.app.models.domain import Domain
from backend.app.models.snapshot import Snapshot
from backend.app.models.analysis import AnalysisFlag
from backend.app.models.timeline import DomainTimeline
from backend.app.models.threat_intel import ThreatIntelligence
from backend.app.models.system_settings import SystemSettings
from backend.app.services.pipeline import analyze_domain_pipeline
from backend.app.services.cdx_service import fetch_snapshots_with_proxy_rotation
from backend.app.utils.logger import logger

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        nest_asyncio.apply()

    return loop.run_until_complete(coro)

def _pick_evidence_snapshot(result: dict) -> dict | None:
    snapshots = result.get("snapshots") or []
    unsafe = [
        snap for snap in snapshots
        if snap.get("evidence_url") and (snap.get("risk_score", 0) >= 40 or snap.get("flags"))
    ]
    if not unsafe:
        return None

    snap = max(unsafe, key=lambda item: item.get("risk_score", 0))
    return {
        "timestamp": snap.get("timestamp"),
        "original_url": snap.get("original_url"),
        "risk_score": snap.get("risk_score"),
        "evidence_url": snap.get("evidence_url"),
        "flags": snap.get("flags", []),
    }

def _enrich_snapshots_with_ai(result: dict) -> dict:
    snapshots = result.get("snapshots", [])
    for snap in snapshots:
        raw_meta = snap.get("extraction_metadata")
        if raw_meta and isinstance(raw_meta, str):
            try:
                parsed = json.loads(raw_meta)
                clf = parsed.get("classifier", {})
                snap["ai_intelligence"] = {
                    "primary_category": clf.get("primary_category"),
                    "confidence": clf.get("confidence"),
                    "all_scores": clf.get("all_scores"),
                    "detected_language": clf.get("detected_language"),
                    "summary": clf.get("summary"),
                    "detectors": parsed.get("detectors"),
                    "detector_boost": parsed.get("detector_boost"),
                }
            except Exception:
                snap["ai_intelligence"] = None
        elif not snap.get("ai_intelligence"):
            snap["ai_intelligence"] = None
    return result

@celery_app.task(name="tasks.analyze_domain")
def analyze_domain_task(domain: str, force_refresh: bool = False, user_id: int | None = None) -> dict:
    """
    Celery task that analyzes a single domain in the background.
    Additionally records admin scan history when completed.
    """
    logger.info(f"[Celery Task] Initiating background analysis for {domain} (User ID: {user_id})")
    start_time = time.monotonic()

    async def run_analysis():
        async with AsyncSessionLocal() as db:
            result = await analyze_domain_pipeline(domain, force_refresh, db)
            enriched = _enrich_snapshots_with_ai(result)

            # Record the scan for admin history
            duration_ms = int((time.monotonic() - start_time) * 1000)
            try:
                scan_rec = ScanRecord(
                    domain_name=domain,
                    user_id=user_id,
                    status="completed",
                    risk_score=enriched.get("risk_score"),
                    risk_level=enriched.get("risk_level"),
                    duration_ms=duration_ms,
                    source=ScanSource.manual if user_id else ScanSource.anonymous,
                    wayback_status="fetched" if enriched.get("snapshots") else "no_data",
                )
                db.add(scan_rec)
                await db.commit()
            except Exception as scan_err:
                logger.warning(f"Failed to record scan history in background task: {scan_err}")
                await db.rollback()

            return enriched

    return _run_async(run_analysis())

@celery_app.task(name="tasks.analyze_multiple_domains")
def analyze_multiple_domains_task(domains: list[str], force_refresh: bool = False) -> list[dict]:
    """
    Celery task to run batch analysis on multiple domains in the background.
    On CDX failure for a domain, automatically retries through the full proxy
    rotation list (HTTP_PROXY_LIST in .env) to bypass regional blocks.
    """
    logger.info(f"[Celery Task] Initiating background bulk analysis for {len(domains)} domains")

    async def run_bulk():
        results = []
        for d in domains:
            try:
                async with AsyncSessionLocal() as db:
                    res = await analyze_domain_pipeline(d, force_refresh, db)
                    results.append({
                        "domain": res["domain"],
                        "risk_score": res["risk_score"],
                        "risk_level": res["risk_level"],
                        # Content intelligence — what was found inside the domain
                        "flags": res.get("flags", []),                          # List of threat category names e.g. ["Gambling", "Phishing"]
                        "primary_category": res.get("primary_category", ""),   # Top AI-classified category
                        "category_confidence": res.get("category_confidence", {}),  # Per-category keyword hit counts
                        "snapshots_checked": res.get("snapshots_checked", 0),  # How many Wayback snapshots were inspected
                        "risk_narrative": res.get("risk_narrative", ""),       # AI explanation sentence
                        "evidence_snapshot": _pick_evidence_snapshot(res),
                        "proxy_used": res.get("cdx_proxy_used"),
                    })
            except Exception as first_err:
                logger.warning(
                    f"[Batch] First attempt failed for {d}: {first_err}. "
                    f"Retrying with proxy rotation..."
                )
                # ── Proxy rotation retry ──────────────────────────────────────
                # Re-run the full pipeline but pre-fetch CDX using each proxy in turn.
                # We inject the working snapshots into a patched pipeline call by
                # temporarily monkey-patching fetch_snapshots inside the pipeline module.
                from backend.app.services import cdx_service as _cdx_mod
                from backend.app.services import pipeline as _pipe_mod

                _original_fetch = _cdx_mod.fetch_snapshots

                rotated_result = None
                proxy_succeeded = None

                try:
                    snapshots_found, proxy_used = await fetch_snapshots_with_proxy_rotation(d)
                    if snapshots_found is not None:
                        # Patch fetch_snapshots temporarily so the pipeline uses
                        # the already-fetched snapshots from the working proxy
                        async def _patched_fetch(domain, proxy=None):
                            return snapshots_found

                        _cdx_mod.fetch_snapshots = _patched_fetch
                        _pipe_mod.fetch_snapshots = _patched_fetch

                        try:
                            async with AsyncSessionLocal() as db2:
                                rotated_result = await analyze_domain_pipeline(d, force_refresh, db2)
                                proxy_succeeded = proxy_used
                        finally:
                            # Always restore original function
                            _cdx_mod.fetch_snapshots = _original_fetch
                            _pipe_mod.fetch_snapshots = _original_fetch
                    else:
                        logger.error(f"[Batch] All proxy rotation attempts failed for {d}. Skipping.")
                except Exception as rotation_err:
                    _cdx_mod.fetch_snapshots = _original_fetch
                    _pipe_mod.fetch_snapshots = _original_fetch
                    logger.error(f"[Batch] Proxy rotation error for {d}: {rotation_err}")

                if rotated_result:
                    results.append({
                        "domain": rotated_result["domain"],
                        "risk_score": rotated_result["risk_score"],
                        "risk_level": rotated_result["risk_level"],
                        "flags": rotated_result.get("flags", []),
                        "primary_category": rotated_result.get("primary_category", ""),
                        "category_confidence": rotated_result.get("category_confidence", {}),
                        "snapshots_checked": rotated_result.get("snapshots_checked", 0),
                        "risk_narrative": rotated_result.get("risk_narrative", ""),
                        "evidence_snapshot": _pick_evidence_snapshot(rotated_result),
                        "proxy_used": rotated_result.get("cdx_proxy_used", proxy_succeeded),
                    })
                # If still failed, domain is simply omitted from results → shows as "Failed" in UI

        return results

    return _run_async(run_bulk())

@celery_app.task(name="tasks.cleanup_old_domains")
def cleanup_old_domains_task() -> int:
    """
    Celery task that deletes domains and all cascaded metrics/snapshots older than 30 days.
    """
    logger.info("[Celery Task] Initiating background database cleanup for records older than 30 days")

    async def run_cleanup():
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        async with AsyncSessionLocal() as db:
            stmt = delete(Domain).where(Domain.last_analyzed_at < cutoff_date)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    deleted_count = _run_async(run_cleanup())
    logger.info(f"[Celery Task] Database cleanup complete. Deleted {deleted_count} domain records.")
    return deleted_count

@celery_app.task(name="tasks.update_working_proxies")
def update_working_proxies_task() -> list[str]:
    """
    Celery task that scrapes and tests free proxies, storing the verified working
    ones in Redis so that actual analysis pipelines can fetch them instantly.
    """
    logger.info("[Celery Task] Scraped proxy auto-refresh and validation task started...")

    async def run_update():
        from backend.app.core.proxy_utils import find_working_proxies
        from backend.app.core.redis import redis_manager

        working = await find_working_proxies()
        await redis_manager.set("scraped_working_proxies", working, expire_seconds=86400)  # cache for 1 day
        logger.info(f"[Celery Task] Scraped working proxy pool updated: {len(working)} verified proxies cached in Redis.")
        return working

    return _run_async(run_update())



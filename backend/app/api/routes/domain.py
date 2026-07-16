import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_optional_user
from backend.app.schemas.domain_schema import DomainRequest, DomainAnalysisResponse
from backend.app.schemas.response_schema import BulkAnalysisRequest, BulkAnalysisResponse
from backend.app.services.pipeline import analyze_domain_pipeline
from backend.app.models.domain import Domain
from backend.app.models.scan_record import ScanRecord, ScanSource
from backend.app.models.user import User
from backend.app.workers.tasks import analyze_multiple_domains_task, analyze_domain_task
from backend.app.utils.logger import logger

router = APIRouter()


def _enrich_snapshots_with_ai(result: dict) -> dict:
    """
    Parse each snapshot's `extraction_metadata` JSON string into the
    structured `ai_intelligence` field expected by the API schema.
    """
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


from fastapi.responses import HTMLResponse, Response

@router.get("/proxy-snapshot", response_class=HTMLResponse)
async def proxy_snapshot(timestamp: str, url: str):
    """
    Proxies Wayback Machine snapshot HTML content through the backend so that users 
    blocked from direct archive.org access can view snapshot iframe previews.
    Injects a <base href> tag so relative resources (CSS, JS, images) resolve correctly.
    """
    from backend.app.services.wayback import wayback_service
    try:
        html_content = await wayback_service.get_snapshot_content(timestamp=timestamp, url=url)

        # Build the Wayback base URL for this snapshot so relative links resolve correctly
        wayback_base = f"https://web.archive.org/web/{timestamp}id_/{url}"

        # Inject <base href> right after <head> (or at the start of <html>) so all
        # relative CSS/JS/image paths are resolved against the archived snapshot origin.
        base_tag = f'<base href="{wayback_base}" target="_blank">'

        if "<head>" in html_content.lower():
            # Insert after first <head> tag (case-insensitive)
            idx = html_content.lower().find("<head>")
            insert_pos = idx + len("<head>")
            html_content = html_content[:insert_pos] + base_tag + html_content[insert_pos:]
        elif "<html" in html_content.lower():
            # Fallback: insert right before </html>
            html_content = base_tag + html_content
        else:
            html_content = base_tag + html_content

        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;",
        }
        return HTMLResponse(content=html_content, headers=headers)
    except Exception as e:
        logger.error(f"Error proxying snapshot for {url} at {timestamp}: {e}")
        # Return a styled error page instead of a 500 that breaks the iframe
        error_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Snapshot Unavailable</title>
<style>
  body {{ font-family: sans-serif; background: #0f172a; color: #94a3b8;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
  .box {{ text-align: center; padding: 2rem; border: 1px solid #1e293b; border-radius: 12px; max-width: 400px; }}
  h2 {{ color: #e2e8f0; margin-bottom: .5rem; }}
  a {{ color: #818cf8; }}
</style></head>
<body><div class="box">
  <h2>📷 Snapshot Unavailable</h2>
  <p>Could not retrieve this snapshot through the proxy.</p>
  <p><a href="https://web.archive.org/web/{timestamp}/{url}" target="_blank">Open directly on Wayback Machine ↗</a></p>
  <p style="font-size:11px;margin-top:1rem;color:#475569">{str(e)[:120]}</p>
</div></body></html>"""
        return HTMLResponse(content=error_html, status_code=200)


@router.post("/analyze", response_model=DomainAnalysisResponse)
async def analyze_domain(
    request: DomainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Analyzes a domain by fetching historical snapshots, scoring content, 
    and persisting results to cache and database.
    Optionally links the scan to an authenticated user for admin history tracking.
    """
    start_time = time.monotonic()
    try:
        logger.info(f"Received analysis request for: {request.domain}")
        result = await analyze_domain_pipeline(
            domain=request.domain, 
            force_refresh=request.force_refresh, 
            db=db
        )
        enriched = _enrich_snapshots_with_ai(result)

        # Record the scan for admin history
        duration_ms = int((time.monotonic() - start_time) * 1000)
        try:
            scan_rec = ScanRecord(
                domain_name=request.domain,
                user_id=current_user.id if current_user else None,
                status="completed",
                risk_score=enriched.get("risk_score"),
                risk_level=enriched.get("risk_level"),
                duration_ms=duration_ms,
                source=ScanSource.manual if current_user else ScanSource.anonymous,
                wayback_status="fetched" if enriched.get("snapshots") else "no_data",
            )
            db.add(scan_rec)
            await db.flush()
        except Exception as scan_err:
            logger.warning(f"Failed to record scan history: {scan_err}")

        return enriched
    except Exception as e:
        logger.error(f"Error during domain analysis for {request.domain}: {e}", exc_info=True)
        err_msg = str(e)
        status_code = 500
        if "Wayback Machine" in err_msg or "CDX API" in err_msg or "unreachable" in err_msg:
            status_code = 503
        raise HTTPException(
            status_code=status_code, 
            detail=f"An error occurred while analyzing domain: {err_msg}"
        )


@router.post("/bulk-analyze", response_model=BulkAnalysisResponse)
async def bulk_analyze_domains(request: BulkAnalysisRequest):
    """
    Submits a list of domains for background processing via Celery.
    Returns a Celery task ID immediately.
    """
    if not request.domains:
        raise HTTPException(status_code=400, detail="Domain list cannot be empty")
        
    try:
        # Trigger Celery task in the background
        task = analyze_multiple_domains_task.delay(request.domains)
        logger.info(f"Triggered bulk analysis task {task.id} for domains: {request.domains}")
        return BulkAnalysisResponse(
            task_id=task.id,
            message="Bulk analysis successfully queued in the background."
        )
    except Exception as e:
        logger.error(f"Failed to queue bulk analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue background job: {str(e)}"
        )

@router.get("/stats")
async def get_domain_stats(db: AsyncSession = Depends(get_db)):
    """
    Fetches aggregate statistics regarding analyzed domains, risk levels, and recent records.
    """
    try:
        # Query total count and risk level counts
        total_stmt = select(func.count(Domain.id))
        total_res = await db.execute(total_stmt)
        total_count = total_res.scalar() or 0

        # Query counts grouped by risk level
        group_stmt = select(Domain.risk_level, func.count(Domain.id)).group_by(Domain.risk_level)
        group_res = await db.execute(group_stmt)
        breakdown = {row[0]: row[1] for row in group_res.all()}

        # Ensure all risk categories are present in breakdown
        for level in ["SAFE", "MEDIUM", "HIGH", "UNSAFE", "UNKNOWN"]:
            if level not in breakdown:
                breakdown[level] = 0

        # Fetch every analyzed domain so dashboard widgets reflect the full DB catalog.
        recent_stmt = select(Domain).order_by(Domain.last_analyzed_at.desc())
        recent_res = await db.execute(recent_stmt)
        recent_domains = [
            {
                "domain": d.name,
                "risk_score": d.risk_score,
                "risk_level": d.risk_level,
                "last_analyzed_at": d.last_analyzed_at.isoformat()
            }
            for d in recent_res.scalars().all()
        ]

        return {
            "total_analyzed": total_count,
            "risk_breakdown": breakdown,
            "recent_domains": recent_domains
        }
    except Exception as e:
        logger.error(f"Error querying statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to query database statistics"
        )

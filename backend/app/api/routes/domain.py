import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_optional_user
from backend.app.schemas.domain_schema import DomainRequest, DomainAnalysisResponse, DomainAnalysisSubmitResponse
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
<head><meta charset="UTF-8"><title>Captured HTTP Error / Snapshot Preview</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #94a3b8;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
  .box {{ text-align: center; padding: 2.5rem; border: 1px solid #1e293b; border-radius: 16px; max-width: 460px; background: #0f172a; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }}
  .icon {{ font-size: 2.5rem; margin-bottom: 1rem; }}
  h2 {{ color: #f8fafc; font-size: 1.25rem; font-weight: 600; margin: 0 0 0.5rem 0; }}
  p {{ font-size: 0.9rem; line-height: 1.5; color: #94a3b8; margin: 0 0 1.25rem 0; }}
  .badge {{ display: inline-block; padding: 0.25rem 0.75rem; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; margin-bottom: 1rem; }}
  a {{ display: inline-block; padding: 0.6rem 1.2rem; background: #3b82f6; color: #ffffff; font-weight: 500; font-size: 0.85rem; border-radius: 8px; text-decoration: none; transition: all 0.2s; }}
  a:hover {{ background: #2563eb; }}
  .err-detail {{ font-size: 11px; margin-top: 1.25rem; color: #64748b; word-break: break-all; }}
</style></head>
<body><div class="box">
  <div class="badge">SERVER CAPTURE NOTICE</div>
  <div class="icon">⚠️</div>
  <h2>Captured Server Error / Dead Snapshot</h2>
  <p>This historical capture was recorded while the domain returned an HTTP error (e.g. 503 Service Unavailable / 404) or was unreachable.</p>
  <a href="https://web.archive.org/web/{timestamp}/{url}" target="_blank">Open on Wayback Machine ↗</a>
  <div class="err-detail">{str(e)[:150]}</div>
</div></body></html>"""
        return HTMLResponse(content=error_html, status_code=200)


from backend.app.services.task_dispatcher import (
    dispatch_single_domain_analysis,
    dispatch_bulk_domain_analysis,
)

@router.post("/analyze", response_model=DomainAnalysisSubmitResponse)
async def analyze_domain(
    request: DomainRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Submits a domain scan job for background analysis.
    Uses Celery when active, or falls back seamlessly to background async task runner.
    Returns the task ID immediately.
    """
    try:
        logger.info(f"Received analysis request for: {request.domain}")
        task_id = await dispatch_single_domain_analysis(
            request.domain, 
            request.force_refresh, 
            current_user.id if current_user else None
        )
        return DomainAnalysisSubmitResponse(
            task_id=task_id,
            message="Analysis successfully queued in the background."
        )
    except Exception as e:
        logger.error(f"Failed to queue domain analysis for {request.domain}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue background job: {str(e)}"
        )


@router.post("/bulk-analyze", response_model=BulkAnalysisResponse)
async def bulk_analyze_domains(request: BulkAnalysisRequest):
    """
    Submits a list of domains for background processing.
    Uses Celery when active, or falls back seamlessly to background async task runner.
    Returns a task ID immediately.
    """
    if not request.domains:
        raise HTTPException(status_code=400, detail="Domain list cannot be empty")
        
    try:
        task_id = await dispatch_bulk_domain_analysis(request.domains)
        logger.info(f"Triggered bulk analysis task {task_id} for domains: {request.domains}")
        return BulkAnalysisResponse(
            task_id=task_id,
            message="Bulk analysis successfully queued in the background."
        )
    except Exception as e:
        logger.error(f"Failed to queue bulk analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue background job: {str(e)}"
        )

@router.get("/stats")
async def get_domain_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Fetches aggregate statistics regarding analyzed domains, risk levels, and recent records.
    Enriches each domain with user details (or fallback to active inspector).
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

        # Determine default fallback user info if scan record user is null
        fallback_user_data = None
        if current_user:
            fallback_user_data = {
                "user_id": current_user.id,
                "username": current_user.username,
                "full_name": current_user.full_name,
            }
        else:
            first_user_res = await db.execute(select(User).order_by(User.id.asc()).limit(1))
            first_user = first_user_res.scalar_one_or_none()
            if first_user:
                fallback_user_data = {
                    "user_id": first_user.id,
                    "username": first_user.username,
                    "full_name": first_user.full_name,
                }

        # Fetch every analyzed domain so dashboard widgets reflect the full DB catalog.
        recent_stmt = select(Domain).order_by(Domain.last_analyzed_at.desc())
        recent_res = await db.execute(recent_stmt)
        domain_objs = recent_res.scalars().all()

        domain_names = [d.name for d in domain_objs]
        user_map: dict[str, dict[str, Any]] = {}
        
        if domain_names:
            scan_stmt = (
                select(ScanRecord.domain_name, User.id, User.username, User.full_name)
                .join(User, ScanRecord.user_id == User.id)
                .where(ScanRecord.domain_name.in_(domain_names))
                .order_by(ScanRecord.checked_at.desc())
            )
            scan_res = await db.execute(scan_stmt)
            for d_name, u_id, username, full_name in scan_res.all():
                if d_name not in user_map:  # First record is the latest user check
                    user_map[d_name] = {
                        "user_id": u_id,
                        "username": username,
                        "full_name": full_name,
                    }

        recent_domains = [
            {
                "domain": d.name,
                "risk_score": d.risk_score,
                "risk_level": d.risk_level,
                "last_analyzed_at": d.last_analyzed_at.isoformat(),
                "checked_by": user_map.get(d.name, fallback_user_data)
            }
            for d in domain_objs
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

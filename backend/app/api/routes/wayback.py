from fastapi import APIRouter, Query, HTTPException, Response
from typing import List
from backend.app.services.wayback import wayback_service, SSRFValidationError, WaybackServiceError
from backend.app.schemas.wayback_schema import WaybackSearchResponse, WaybackAvailabilityResponse
from backend.app.utils.logger import logger

router = APIRouter()

@router.get("/search", response_model=List[WaybackSearchResponse])
async def search_snapshots(
    domain: str = Query(..., description="The target domain to search index entries for"),
    force_refresh: bool = Query(False, description="Force fetching fresh data, bypassing cache")
):
    """
    Search historical snapshot indexes for a domain.
    """
    try:
        results = await wayback_service.search_snapshots(domain, force_refresh)
        return results
    except SSRFValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WaybackServiceError as e:
        logger.error(f"API Error in search_snapshots: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/snapshot")
async def get_snapshot(
    timestamp: str = Query(..., description="Snapshot timestamp"),
    url: str = Query(..., description="Original URL of the snapshot"),
    force_refresh: bool = Query(False, description="Bypass cache and force fetch snapshot content")
):
    """
    Retrieve raw HTML content of a specific snapshot.
    """
    try:
        html = await wayback_service.get_snapshot_content(timestamp, url, force_refresh)
        return Response(content=html, media_type="text/html")
    except SSRFValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WaybackServiceError as e:
        logger.error(f"API Error in get_snapshot: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/availability", response_model=WaybackAvailabilityResponse)
async def check_availability(
    url: str = Query(..., description="The target URL to check availability"),
    force_refresh: bool = Query(False, description="Bypass cache and check fresh availability")
):
    """
    Check if Wayback has archived snapshots of a target URL.
    """
    try:
        raw_res = await wayback_service.check_availability(url, force_refresh)
        closest = raw_res.get("archived_snapshots", {}).get("closest", {})
        return WaybackAvailabilityResponse(
            url=url,
            available=closest.get("available", False),
            snapshot_url=closest.get("url"),
            timestamp=closest.get("timestamp")
        )
    except SSRFValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WaybackServiceError as e:
        logger.error(f"API Error in check_availability: {e}")
        raise HTTPException(status_code=502, detail=str(e))

from typing import List, Dict, Any, Optional
from backend.app.services.wayback import wayback_service
from backend.app.utils.logger import logger
from urllib.parse import urlparse

_USE_DEFAULT_PROXY = object()

def filter_homepage_snapshots(raw_snapshots: List[Dict[str, Any]], domain_clean: str) -> List[Dict[str, Any]]:
    snapshots = []
    for snap in raw_snapshots:
        status = snap.get("statuscode", "")
        mime = snap.get("mime", "")
        original_url = snap.get("original", "")

        if status != "200" or not mime or "text/html" not in mime:
            continue

        try:
            parsed = urlparse(original_url)
            path = parsed.path.rstrip("/")
            if path and path not in ["", "/"]:
                continue
        except Exception:
            pass

        snapshots.append(snap)

    if not snapshots:
        logger.info(f"Homepage-only filter returned 0 results for {domain_clean}. Falling back to all HTML snapshots.")
        for snap in raw_snapshots:
            status = snap.get("statuscode", "")
            mime = snap.get("mime", "")
            if status == "200" and mime and "text/html" in mime:
                snapshots.append(snap)
    return snapshots

async def fetch_snapshots(domain: str, proxy: str | None | object = _USE_DEFAULT_PROXY, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
    """
    Backward-compatible wrapper to fetch snapshot metadata, now routed through the new WaybackAccessService.
    """
    domain_clean = domain.strip().lower()
    try:
        raw_snapshots = await wayback_service.search_snapshots(domain_clean, force_refresh=force_refresh)
        return filter_homepage_snapshots(raw_snapshots, domain_clean)
    except Exception as e:
        logger.error(f"cdx_service.fetch_snapshots: Error fetching snapshots for {domain_clean}: {e}")
        return None

async def fetch_snapshots_with_proxy_rotation(domain: str, force_refresh: bool = False) -> tuple[Optional[List[Dict[str, Any]]], str | None]:
    """
    Backward-compatible wrapper. Calls the WaybackAccessService (which already performs internal proxy rotation).
    """
    domain_clean = domain.strip().lower()
    try:
        raw_snapshots = await wayback_service.search_snapshots(domain_clean, force_refresh=force_refresh)
        filtered = filter_homepage_snapshots(raw_snapshots, domain_clean)
        # Proxy rotation is now abstracted inside the client, so we return "WaybackAccessService" as the used proxy name.
        return filtered, "WaybackAccessService"
    except Exception as e:
        logger.error(f"cdx_service.fetch_snapshots_with_proxy_rotation: Error for {domain_clean}: {e}")
        return None, None

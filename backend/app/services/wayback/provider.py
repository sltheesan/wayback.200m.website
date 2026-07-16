import json
from typing import Protocol, List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.utils.logger import logger
from backend.app.services.wayback.client import WaybackHTTPClient

class ArchiveProvider(Protocol):
    async def search(self, domain: str) -> Optional[List[Dict[str, Any]]]:
        """Query snapshot index/metadata for the domain."""
        ...

    async def get_snapshot(self, timestamp: str, url: str) -> str:
        """Fetch raw HTML content of a snapshot."""
        ...

    async def get_availability(self, url: str) -> Dict[str, Any]:
        """Check if an archive snapshot is available for a URL."""
        ...

class WaybackProvider(ArchiveProvider):
    def __init__(self, client: WaybackHTTPClient):
        self.client = client

    async def _query_cdx_raw(self, target_url: str) -> List[List[str]]:
        query_url = f"{settings.WAYBACK_CDX_URL}?url={target_url}&output=json&limit=500"
        res_text = await self.client.get(query_url)
        if not res_text.strip():
            return []
        try:
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error parsing CDX JSON response for {target_url}: {e}")
            from backend.app.services.wayback.exceptions import WaybackServiceError
            raise WaybackServiceError(f"Failed to parse Wayback CDX response: {e}")

    async def search(self, domain: str) -> List[Dict[str, Any]]:
        domain_clean = domain.strip().lower()
        if getattr(settings, "MOCK_WAYBACK", False):
            logger.info(f"WaybackProvider [MOCK]: Generating mock snapshots list for {domain_clean}")
            return [
                {
                    "timestamp": "20190412120000",
                    "original": f"http://{domain_clean}/",
                    "statuscode": "200",
                    "mime": "text/html",
                    "digest": f"mockdigest2019_{domain_clean}"
                },
                {
                    "timestamp": "20210618153000",
                    "original": f"http://{domain_clean}/",
                    "statuscode": "200",
                    "mime": "text/html",
                    "digest": f"mockdigest2021_{domain_clean}"
                },
                {
                    "timestamp": "20230824091500",
                    "original": f"http://{domain_clean}/",
                    "statuscode": "200",
                    "mime": "text/html",
                    "digest": f"mockdigest2023_{domain_clean}"
                }
            ]

        logger.info(f"WaybackProvider: Querying CDX wildcard for: {domain_clean}/*")
        raw_data = await self._query_cdx_raw(f"{domain_clean}/*")
        if not raw_data or len(raw_data) <= 1:
            logger.info(f"WaybackProvider: CDX wildcard returned no data. Trying root query for: {domain_clean}")
            root_data = await self._query_cdx_raw(domain_clean)
            if root_data:
                raw_data = root_data

        if not raw_data or len(raw_data) <= 1:
            return []

        headers_list = [h.lower() for h in raw_data[0]]
        snapshots = []
        for row in raw_data[1:]:
            snapshot_dict = dict(zip(headers_list, row))
            snapshots.append({
                "timestamp": snapshot_dict.get("timestamp", ""),
                "original": snapshot_dict.get("original", ""),
                "statuscode": snapshot_dict.get("statuscode", ""),
                "mime": snapshot_dict.get("mimetype", snapshot_dict.get("mime", "")),
                "digest": snapshot_dict.get("digest", "")
            })
        return snapshots

    async def get_snapshot(self, timestamp: str, url: str) -> str:
        if getattr(settings, "MOCK_WAYBACK", False):
            url_lower = url.lower()
            logger.info(f"WaybackProvider [MOCK]: Returning mock HTML content for {url} at {timestamp}")
            if "redhat-gitops-patterns" in url_lower:
                return """
                <html>
                  <head>
                    <title>Best Online Casino slots and Roulette</title>
                    <meta name="description" content="online casino live casino welcome bonus slots slots slots casino casino roulette roulette">
                  </head>
                  <body>
                    <h1>Welcome to the Ultimate Casino experience!</h1>
                    <p>Place your bet now on roulette, blackjack, or video slots. Win big cash payouts online casino games!</p>
                  </body>
                </html>
                """
            elif "geld-lenen" in url_lower:
                return """
                <html>
                  <head>
                    <title>Geld Lenen Zonder BKR Toetsing</title>
                    <meta name="description" content="geld lenen bkr toetsing snel lenen lening">
                  </head>
                  <body>
                    <h1>Snel en eenvoudig geld lenen</h1>
                    <p>Wilt u geld lenen zonder BKR toetsing? Vraag vandaag nog een lening aan voor extra financiele ruimte.</p>
                  </body>
                </html>
                """
            elif "shopsocielle" in url_lower:
                return """
                <html>
                  <head>
                    <title>Shop Socielle - Online Fashion Store</title>
                    <meta name="description" content="fashion store shopping cart checkout shopping">
                  </head>
                  <body>
                    <h1>Welcome to Shop Socielle</h1>
                    <p>Add items to your cart, check out the new arrivals, and shop our latest collection.</p>
                  </body>
                </html>
                """
            elif "wikipedia.org" in url_lower:
                return "<html><head><meta name=\"description\" content=\"wikipedia safe clean educational content\"></head><body><h1>Wikipedia The Free Encyclopedia</h1><p>Clean educational content.</p></body></html>"
            else:
                return f"<html><head><meta name=\"description\" content=\"mock clean safe educational site\"></head><body><h1>Mock Homepage for {url}</h1><p>This is a safe and clean educational site.</p></body></html>"

        raw_url = f"https://web.archive.org/web/{timestamp}id_/{url}"
        logger.info(f"WaybackProvider: Fetching snapshot content for {url} at {timestamp}")
        return await self.client.get(raw_url)

    async def get_availability(self, url: str) -> Dict[str, Any]:
        if getattr(settings, "MOCK_WAYBACK", False):
            logger.info(f"WaybackProvider [MOCK]: Checking availability for {url}")
            return {
                "archived_snapshots": {
                    "closest": {
                        "available": True,
                        "url": f"https://web.archive.org/web/20230824091500/{url}",
                        "timestamp": "20230824091500"
                    }
                }
            }

        avail_url = f"https://archive.org/wayback/available?url={url}"
        logger.info(f"WaybackProvider: Checking availability for {url}")
        res_text = await self.client.get(avail_url)
        try:
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"WaybackProvider: Failed to parse availability JSON: {e}")
            return {"archived_snapshots": {}}

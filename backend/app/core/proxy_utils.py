from __future__ import annotations

import asyncio
import time
import random
from typing import Optional
import aiohttp
from bs4 import BeautifulSoup

from backend.app.core.config import settings
from backend.app.utils.logger import logger

SUPPORTED_PROXY_PREFIXES = (
    "http://",
    "https://",
    "socks4://",
    "socks5://"
)

# Cache for free public proxies
_free_proxies: list[str] = []
_last_fetched: float = 0.0
_fetch_lock = asyncio.Lock()

# Verified working proxies cache
_working_proxies: list[str] = []


def proxy_label(proxy: Optional[str]) -> str:
    return proxy or "direct (no proxy)"


def is_supported_proxy(proxy: Optional[str]) -> bool:
    if proxy is None:
        return True
    return proxy.lower().startswith(SUPPORTED_PROXY_PREFIXES)


def is_socks_proxy(proxy: Optional[str]) -> bool:
    if not proxy:
        return False
    return proxy.lower().startswith(("socks4://", "socks5://"))


def is_free_proxy(proxy: Optional[str]) -> bool:
    """Checks if the proxy is part of the dynamically scraped free proxy pool."""
    if not proxy:
        return False
    return proxy in _free_proxies


# ---------------------------------------------------------------------------
# Proxy Sources
# ---------------------------------------------------------------------------

PROXY_SOURCES = [
    # ProxyScrape — HTTP anonymous SSL proxies
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=anonymous",
    # ProxyScrape — SOCKS5 proxies
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all",
    # Proxy-list.download
    "https://www.proxy-list.download/api/v1/get?type=http&anon=elite",
]


async def _fetch_from_source(session: aiohttp.ClientSession, url: str) -> list[str]:
    """Fetch and parse a single proxy list source. Returns list of http:// proxy strings."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    results = []
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as response:
            if response.status == 200:
                text = await response.text()
                for line in text.splitlines():
                    line = line.strip()
                    if line and ":" in line and not line.startswith("#"):
                        # Determine scheme: proxyscrape SOCKS5 source → socks5://, else http://
                        if "socks5" in url:
                            results.append(f"socks5://{line}")
                        elif "socks4" in url:
                            results.append(f"socks4://{line}")
                        else:
                            results.append(f"http://{line}")
    except Exception as e:
        logger.debug(f"[Proxy] Source {url} failed: {e}")
    return results


async def refresh_free_proxies() -> None:
    """Scrapes fresh proxies from multiple sources concurrently."""
    global _free_proxies, _last_fetched

    logger.info("[Proxy] Fetching fresh proxies from multiple sources...")
    new_proxies: list[str] = []

    try:
        async with aiohttp.ClientSession() as session:
            tasks = [_fetch_from_source(session, src) for src in PROXY_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    new_proxies.extend(result)

        # Deduplicate
        seen: set[str] = set()
        deduped: list[str] = []
        for p in new_proxies:
            if p not in seen:
                seen.add(p)
                deduped.append(p)

        if deduped:
            _free_proxies = deduped
            _last_fetched = time.time()
            logger.info(f"[Proxy] Collected {len(_free_proxies)} candidate proxies from all sources.")
        else:
            logger.warning("[Proxy] All sources returned 0 proxies.")
    except Exception as e:
        logger.error(f"[Proxy] Error refreshing proxy pool: {e}")


# ---------------------------------------------------------------------------
# Proxy Testing
# ---------------------------------------------------------------------------

async def test_single_proxy(proxy: str, target: str = "https://web.archive.org/") -> Optional[str]:
    """Tests if a single proxy can reach archive.org within 6 seconds."""
    try:
        connector = None
        if proxy.lower().startswith(("socks4://", "socks5://")):
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy)
            except ImportError:
                return None

        async with aiohttp.ClientSession(connector=connector) as session:
            request_kwargs: dict = {"timeout": aiohttp.ClientTimeout(total=6)}
            if not proxy.lower().startswith(("socks4://", "socks5://")):
                request_kwargs["proxy"] = proxy

            async with session.get(target, **request_kwargs) as response:
                if response.status < 400:
                    return proxy
    except Exception:
        pass
    return None


async def find_working_proxies() -> list[str]:
    """
    Validates cached working proxies, then scrapes and batch-tests fresh ones.
    Returns up to 15 verified working proxies.
    """
    global _working_proxies

    # 1. Re-validate existing cached working proxies (fast, parallel)
    if _working_proxies:
        tasks = [test_single_proxy(p) for p in _working_proxies]
        results = await asyncio.gather(*tasks)
        still_working = [r for r in results if r]
        if len(still_working) >= 3:
            _working_proxies = still_working
            logger.info(f"[Proxy] {len(still_working)} cached proxies still working.")
            return _working_proxies

    # 2. Fetch fresh proxy lists (refresh every 10 minutes)
    async with _fetch_lock:
        if not _free_proxies or (time.time() - _last_fetched > 600):
            await refresh_free_proxies()

    if not _free_proxies:
        logger.warning("[Proxy] No candidate proxies available to test.")
        return _working_proxies

    # 3. Test proxies in parallel batches of 60 at a time
    # Shuffle so we don't always hammer the same proxies first
    candidates = _free_proxies[:]
    random.shuffle(candidates)

    new_working: list[str] = []
    batch_size = 60

    for i in range(0, min(len(candidates), 180), batch_size):
        batch = candidates[i: i + batch_size]
        tasks = [test_single_proxy(p) for p in batch]
        results = await asyncio.gather(*tasks)
        new_working.extend(r for r in results if r)

        if len(new_working) >= 15:
            break  # We have enough working proxies

    # Merge with previously working, deduplicate, keep top 15
    combined = list(dict.fromkeys(new_working + _working_proxies))
    _working_proxies = combined[:15]

    logger.info(f"[Proxy] Working proxy pool updated: {len(_working_proxies)} proxies available.")
    return _working_proxies


def report_proxy_failure(proxy: str) -> None:
    global _working_proxies
    if proxy in _working_proxies:
        logger.warning(f"[Proxy] Proxy {proxy} failed. Removing from working pool.")
        try:
            _working_proxies.remove(proxy)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_proxy_rotation_list() -> list[str | None]:
    """
    Build the full rotation list in priority order:
      1. HTTP_PROXY  (single primary configured proxy)
      2. HTTP_PROXY_LIST  (comma-separated configured proxies)
      3. Verified free proxies (if ENABLE_PROXY_SCRAPER=True)
      4. Direct connection  (always last)
    """
    proxies: list[str | None] = []

    # --- Tier 1: Explicitly configured proxies (highest priority) ---
    configured = settings.get_proxy_rotation_list()
    # get_proxy_rotation_list() already appends None at the end — remove it for now
    tier1 = [p for p in configured if p is not None]
    if tier1:
        proxies.extend(tier1)
        logger.debug(f"[Proxy] Tier-1 configured proxies: {tier1}")

    # --- Tier 2: Verified free proxies (if scraper enabled) ---
    if getattr(settings, "ENABLE_PROXY_SCRAPER", False):
        working = await find_working_proxies()
        for p in working:
            if p not in proxies:
                proxies.append(p)

    # --- Tier 3: Direct connection (always present as final fallback) ---
    proxies.append(None)

    return proxies

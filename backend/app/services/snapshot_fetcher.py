import asyncio
from backend.app.core.config import settings
from backend.app.utils.logger import logger
from backend.app.core.http_client import HttpClient
from backend.app.core.proxy_utils import get_proxy_rotation_list, proxy_label
from backend.app.services.wayback import wayback_service


def build_snapshot_url(timestamp: str, url: str) -> str:
    """Constructs the Wayback Machine archive URL for a snapshot."""
    clean_url = url
    if "web.archive.org/web/" in url:
        parts = url.split("/web/")
        if len(parts) > 1:
            subparts = parts[1].split("/", 1)
            if len(subparts) > 1:
                clean_url = subparts[1]

    return f"{settings.WAYBACK_SNAPSHOT_URL}/{timestamp}/{clean_url}"


import re

_RE_EXTRACT_JS_REDIRECT = re.compile(
    r'(?:window\.location|document\.location|location\.href|location\.replace)\s*=\s*["\'](https?://[^"\'>\s]+)["\']',
    re.IGNORECASE
)
_RE_EXTRACT_META_REDIRECT = re.compile(
    r'<meta\s+http-equiv=["\']?refresh["\']?\s+content=["\']?\d+;\s*url=(https?://[^"\'>\s]+)["\']?',
    re.IGNORECASE
)


async def follow_redirect_if_needed(html: str, current_url: str) -> str:
    """Extracts JS or Meta-refresh redirect target URLs and appends target HTML content for deep analysis."""
    if not html:
        return html

    target_match = _RE_EXTRACT_JS_REDIRECT.search(html) or _RE_EXTRACT_META_REDIRECT.search(html)
    if not target_match:
        return html

    redirect_target = target_match.group(1)
    if redirect_target and redirect_target.lower() != current_url.lower():
        logger.info(f"Detected client-side redirect in snapshot/live page to: {redirect_target}")
        from backend.app.core.http_client import http_client
        session = http_client.get_session_for_proxy(None)
        try:
            async with session.get(redirect_target, timeout=8, headers={"User-Agent": "Mozilla/5.0"}) as res:
                if res.status < 400:
                    target_html = await res.text(errors="ignore")
                    logger.info(f"Fetched redirect target HTML ({len(target_html)} bytes) from {redirect_target}")
                    return (
                        f"{html}\n"
                        f"<!-- REDIRECT TARGET URL: {redirect_target} -->\n"
                        f"<!-- REDIRECT TARGET CONTENT BEGIN -->\n"
                        f"{target_html}\n"
                        f"<!-- REDIRECT TARGET CONTENT END -->"
                    )
        except Exception as e:
            logger.warning(f"Could not fetch redirect target content from {redirect_target}: {e}")

        # Always append target URL to HTML comment so text cleaners & threat analyzers see the target domain!
        return f"{html}\n<!-- REDIRECT TARGET URL: {redirect_target} -->"

    return html


async def fetch_snapshot_html(timestamp: str, original_url: str, domain: str) -> str:
    """
    Fetches the raw HTML content of a snapshot from the Wayback Machine.
    Now routed through the centralized, validated, and cached WaybackAccessService,
    with client-side redirect target inspection.
    """
    try:
        raw_html = await wayback_service.get_snapshot_content(timestamp, original_url)
        return await follow_redirect_if_needed(raw_html, original_url)
    except Exception as e:
        logger.error(f"snapshot_fetcher.fetch_snapshot_html: Failed to fetch snapshot {timestamp} for {original_url}: {e}")
        return ""


async def fetch_live_domain_html(domain: str) -> tuple[str, str | None]:
    """
    Fetches the current homepage HTML for a domain.
    Includes client-side and HTTP redirect target inspection.
    """
    domain_clean = domain.strip().lower().removeprefix("http://").removeprefix("https://").strip("/")
    if not domain_clean:
        return "", None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    from backend.app.core.http_client import http_client
    from backend.app.core.proxy_utils import is_socks_proxy

    proxy_list = settings.get_proxy_rotation_list()
    for proxy in proxy_list:
        label = proxy_label(proxy)
        session = http_client.get_session_for_proxy(proxy)
        for url in (f"https://{domain_clean}/", f"http://{domain_clean}/"):
            try:
                request_kwargs = {
                    "headers": headers,
                    "timeout": 12,
                    "allow_redirects": True
                }
                if proxy and not is_socks_proxy(proxy):
                    request_kwargs["proxy"] = proxy

                async with session.get(url, **request_kwargs) as res:
                    content_type = res.headers.get("content-type", "")
                    if res.status < 400 and ("html" in content_type or not content_type):
                        logger.debug(f"Fetched live homepage for {domain_clean} via {label}")
                        raw_text = await res.text(errors="ignore")
                        final_url = str(res.url)
                        enhanced_html = await follow_redirect_if_needed(raw_text, final_url)
                        if final_url and final_url.lower() != url.lower():
                            enhanced_html += f"\n<!-- HTTP REDIRECT FINAL URL: {final_url} -->"
                        return enhanced_html, final_url
                    logger.warning(
                        f"Live homepage returned status {res.status} ({content_type}) for {url} via {label}"
                    )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching live homepage for {url} via {label}")
            except Exception as e:
                logger.warning(f"Error fetching live homepage for {url} via {label}: {e}")

        logger.warning(f"Live homepage fetch failed via {label}; trying next proxy for {domain_clean}")

    return "", None

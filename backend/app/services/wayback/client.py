import asyncio
import random
import aiohttp
from typing import Optional, Dict, Any
from backend.app.utils.logger import logger
from backend.app.core.http_client import http_client
from backend.app.core.proxy_utils import get_proxy_rotation_list, proxy_label, is_socks_proxy, is_free_proxy
from backend.app.services.wayback.exceptions import ProviderError
from backend.app.core.config import settings

class WaybackHTTPClient:
    """
    Production-grade HTTP client for querying Wayback Machine or archive providers.
    Handles timeout, retries, user-agent rotation, and proxy rotation.
    """

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        timeout: int = 35,
        max_retries: int = 2
    ) -> str:
        """
        Executes HTTP requests with proxy rotation, user-agent rotation, and retries per proxy.
        """
        proxy_list = await get_proxy_rotation_list()
        user_agents = settings.get_user_agents()

        for proxy in proxy_list:
            label = proxy_label(proxy)
            session = http_client.get_session_for_proxy(proxy)

            # Dynamic timeout and retry config based on proxy type
            if is_free_proxy(proxy):
                # Fast-fail for scraped free proxies — move on quickly if no response
                current_timeout = 4
                current_retries = 1
            elif proxy is None:
                # Direct connection: give it more time but only attempt once
                current_timeout = 25
                current_retries = 1
            else:
                # Explicitly configured trusted proxy: use full timeout
                current_timeout = timeout
                current_retries = max_retries

            for attempt in range(current_retries):
                # 1. Rotate User-Agent
                random_ua = random.choice(user_agents)
                req_headers = {
                    "User-Agent": random_ua,
                    **(headers or {})
                }

                # 2. Build request kwargs
                request_kwargs = {
                    "params": params,
                    "headers": req_headers,
                    "timeout": aiohttp.ClientTimeout(total=current_timeout),
                    "allow_redirects": True
                }

                # HTTP proxies require the proxy arg; SOCKS proxy connector handles it internally
                if proxy and not is_socks_proxy(proxy):
                    request_kwargs["proxy"] = proxy

                try:
                    logger.info(f"Querying {url} via {label} (attempt {attempt + 1}/{current_retries})...")
                    async with session.request(
                        method,
                        url,
                        **request_kwargs
                    ) as response:
                        if response.status < 400:
                            logger.info(f"Request to {url} succeeded via {label}")
                            return await response.text(errors="ignore")
                        
                        if response.status == 429:
                            logger.warning(
                                f"Rate limited (429) on {url} via {label}. "
                                f"Attempt {attempt + 1}/{current_retries}"
                            )
                        else:
                            logger.warning(
                                f"Provider returned status {response.status} for {url} "
                                f"via {label}. Attempt {attempt + 1}/{current_retries}"
                            )
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Timeout querying {url} via {label}. "
                        f"Attempt {attempt + 1}/{current_retries}"
                    )
                    if proxy:
                        from backend.app.core.proxy_utils import report_proxy_failure
                        report_proxy_failure(proxy)
                except Exception as e:
                    logger.error(
                        f"Error querying {url} via {label} on attempt {attempt + 1}: {e}"
                    )
                    if proxy:
                        from backend.app.core.proxy_utils import report_proxy_failure
                        report_proxy_failure(proxy)

                # Wait slightly before retry on the same proxy (skip for free proxies — move on fast)
                if attempt < current_retries - 1 and not is_free_proxy(proxy):
                    await asyncio.sleep(1.0)

            logger.warning(f"Request failed via {label}; trying next proxy/mechanism")

        raise ProviderError(f"All proxy and direct access attempts failed for URL: {url}")

    async def get(self, url: str, **kwargs) -> str:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> str:
        return await self.request("POST", url, **kwargs)

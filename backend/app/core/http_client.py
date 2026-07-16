import aiohttp
from typing import Optional
from backend.app.utils.logger import logger

class HttpClient:
    session: Optional[aiohttp.ClientSession] = None
    # Map of proxy_key -> ClientSession
    proxy_sessions: dict[str, aiohttp.ClientSession] = {}

    @classmethod
    def get_session(cls) -> aiohttp.ClientSession:
        """Standard backwards-compatible direct connection session."""
        if cls.session is None or cls.session.closed:
            connector = aiohttp.TCPConnector(limit=100)
            cls.session = aiohttp.ClientSession(connector=connector)
        return cls.session

    @classmethod
    def get_session_for_proxy(cls, proxy: Optional[str]) -> aiohttp.ClientSession:
        """Returns or creates a reusable ClientSession configured for the given proxy."""
        from backend.app.core.proxy_utils import is_socks_proxy
        
        proxy_key = proxy or "direct"
        if proxy_key not in cls.proxy_sessions or cls.proxy_sessions[proxy_key].closed:
            if proxy and is_socks_proxy(proxy):
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy)
                    cls.proxy_sessions[proxy_key] = aiohttp.ClientSession(connector=connector)
                    logger.info(f"[HTTP] Created new SOCKS session for proxy: {proxy}")
                except ImportError:
                    logger.error("[HTTP] aiohttp-socks is not installed. SOCKS proxy is disabled, falling back to direct connection.")
                    cls.proxy_sessions[proxy_key] = aiohttp.ClientSession()
            else:
                # Direct or HTTP/HTTPS proxy session
                cls.proxy_sessions[proxy_key] = aiohttp.ClientSession()
                logger.info(f"[HTTP] Created new standard session for proxy key: {proxy_key}")
                
        return cls.proxy_sessions[proxy_key]

    @classmethod
    async def close_session(cls):
        """Closes all active sessions and connections."""
        # 1. Close standard session
        if cls.session:
            await cls.session.close()
            cls.session = None
            
        # 2. Close all proxy sessions
        for proxy_key, session in list(cls.proxy_sessions.items()):
            if not session.closed:
                await session.close()
        cls.proxy_sessions.clear()
        logger.info("[HTTP] All HTTP client sessions closed successfully.")

http_client = HttpClient()

"""
Audit helper — writes immutable ActivityLog rows for every admin action.
Import and call `log_action` at the end of any mutating admin endpoint.
"""
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activity_log import ActivityLog
from backend.app.utils.logger import logger


def _parse_user_agent(ua_string: Optional[str]) -> tuple[str, str, str]:
    """
    Parse a User-Agent string into (browser, os, device).
    Returns ('Unknown', 'Unknown', 'Unknown') on failure.
    """
    if not ua_string:
        return "Unknown", "Unknown", "Unknown"
    try:
        import user_agents  # type: ignore
        ua = user_agents.parse(ua_string)
        browser = ua.browser.family or "Unknown"
        os_name = ua.os.family or "Unknown"
        device = ua.device.family or "Other"
        return browser, os_name, device
    except Exception:
        return "Unknown", "Unknown", "Unknown"


async def log_action(
    db: AsyncSession,
    *,
    user_id: Optional[int],
    username: Optional[str],
    user_role: Optional[str],
    action: str,
    object_type: Optional[str] = None,
    object_id: Optional[Any] = None,
    object_label: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent_string: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> None:
    """
    Write an immutable audit log entry.
    This function is fire-and-forget — errors are logged but never raised.
    """
    try:
        browser, os_name, device = _parse_user_agent(user_agent_string)

        log_entry = ActivityLog(
            user_id=user_id,
            username_snapshot=username,
            user_role_snapshot=user_role,
            action=action,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else None,
            object_label=object_label,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent_string,
            browser=browser,
            os=os_name,
            device=device,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        await db.flush()  # push to transaction without committing
    except Exception as exc:
        logger.error(f"[Audit] Failed to write activity log: {exc}")

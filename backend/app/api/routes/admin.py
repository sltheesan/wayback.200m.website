"""
Admin routes: dashboard stats, activity logs, login history, scan records,
notifications, system settings, and export.
"""
import csv
import io
from datetime import datetime, date, timedelta, timezone
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.dependencies import require_admin, require_super_admin, get_current_user, get_client_ip
from backend.app.core.audit import log_action
from backend.app.models.user import User, UserRole
from backend.app.models.activity_log import ActivityLog
from backend.app.models.login_history import LoginHistory
from backend.app.models.scan_record import ScanRecord
from backend.app.models.notification import Notification
from backend.app.models.system_settings import SystemSettings
from backend.app.models.domain import Domain
from backend.app.schemas.admin_schema import (
    DashboardStatsResponse,
    ScanRecordListResponse, ScanRecordResponse,
    ActivityLogListResponse, ActivityLogResponse,
    LoginHistoryListResponse, LoginHistoryResponse,
    NotificationResponse,
    SystemSettingResponse, BulkSystemSettingsUpdate,
)
from backend.app.utils.logger import logger

router = APIRouter()
_UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(_UTC).replace(tzinfo=None)


def _today_range() -> tuple[datetime, datetime]:
    today = date.today()
    start = datetime(today.year, today.month, today.day)
    return start, start + timedelta(days=1)


# ---------------------------------------------------------------------------
# GET /admin/stats — dashboard statistics
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    # User counts
    total_users = (await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False, User.role == UserRole.user)
    )).scalar() or 0
    total_admins = (await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False, User.role == UserRole.admin)
    )).scalar() or 0
    total_super_admins = (await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False, User.role == UserRole.super_admin)
    )).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False, User.status == "active")
    )).scalar() or 0
    suspended_users = (await db.execute(
        select(func.count(User.id)).where(User.is_deleted == False, User.status == "suspended")
    )).scalar() or 0

    # Domain scan counts
    total_scans = (await db.execute(select(func.count(ScanRecord.id)))).scalar() or 0
    today_start, today_end = _today_range()
    todays_checks = (await db.execute(
        select(func.count(ScanRecord.id)).where(
            ScanRecord.checked_at >= today_start,
            ScanRecord.checked_at < today_end,
        )
    )).scalar() or 0
    unsafe_domains = (await db.execute(
        select(func.count(Domain.id)).where(Domain.risk_level.in_(["HIGH", "MEDIUM"]))
    )).scalar() or 0
    safe_domains = (await db.execute(
        select(func.count(Domain.id)).where(Domain.risk_level == "SAFE")
    )).scalar() or 0

    # Checks per day (last 30 days)
    thirty_days_ago = _utcnow() - timedelta(days=30)
    daily_rows = await db.execute(
        select(
            func.date(ScanRecord.checked_at).label("day"),
            func.count(ScanRecord.id).label("count"),
        )
        .where(ScanRecord.checked_at >= thirty_days_ago)
        .group_by(func.date(ScanRecord.checked_at))
        .order_by(func.date(ScanRecord.checked_at))
    )
    checks_per_day = [{"date": str(row.day), "count": row.count} for row in daily_rows]

    # Safe vs Unsafe breakdown
    risk_rows = await db.execute(
        select(Domain.risk_level, func.count(Domain.id)).group_by(Domain.risk_level)
    )
    safe_vs_unsafe = {row[0]: row[1] for row in risk_rows}

    # Most checked domains (top 10)
    top_domains_rows = await db.execute(
        select(ScanRecord.domain_name, func.count(ScanRecord.id).label("count"))
        .group_by(ScanRecord.domain_name)
        .order_by(func.count(ScanRecord.id).desc())
        .limit(10)
    )
    most_checked_domains = [{"domain": row[0], "count": row[1]} for row in top_domains_rows]

    # Users activity (logins per day, last 30 days)
    login_rows = await db.execute(
        select(
            func.date(LoginHistory.login_at).label("day"),
            func.count(LoginHistory.id).label("logins"),
        )
        .where(LoginHistory.login_at >= thirty_days_ago, LoginHistory.success == True)
        .group_by(func.date(LoginHistory.login_at))
        .order_by(func.date(LoginHistory.login_at))
    )
    users_activity = [{"date": str(row.day), "logins": row.logins} for row in login_rows]

    return DashboardStatsResponse(
        total_users=total_users,
        total_admins=total_admins,
        total_super_admins=total_super_admins,
        active_users=active_users,
        suspended_users=suspended_users,
        total_domains_checked=total_scans,
        todays_checks=todays_checks,
        unsafe_domains=unsafe_domains,
        safe_domains=safe_domains,
        checks_per_day=checks_per_day,
        safe_vs_unsafe=safe_vs_unsafe,
        most_checked_domains=most_checked_domains,
        users_activity=users_activity,
    )


# ---------------------------------------------------------------------------
# GET /admin/scan-records
# ---------------------------------------------------------------------------
@router.get("/scan-records", response_model=ScanRecordListResponse)
async def get_scan_records(
    domain: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    risk_level: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(ScanRecord)
    if domain:
        stmt = stmt.where(ScanRecord.domain_name.ilike(f"%{domain}%"))
    if user_id:
        stmt = stmt.where(ScanRecord.user_id == user_id)
    if risk_level:
        stmt = stmt.where(ScanRecord.risk_level == risk_level)
    if date_from:
        stmt = stmt.where(ScanRecord.checked_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(ScanRecord.checked_at <= datetime.fromisoformat(date_to))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(ScanRecord.checked_at.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(stmt)).scalars().all()

    # Enrich with usernames
    enriched = []
    for rec in records:
        username = None
        if rec.user_id:
            u = (await db.execute(select(User.username).where(User.id == rec.user_id))).scalar_one_or_none()
            username = u
        enriched.append(ScanRecordResponse(
            id=rec.id,
            domain_name=rec.domain_name,
            user_id=rec.user_id,
            username=username,
            status=rec.status,
            risk_score=rec.risk_score,
            risk_level=rec.risk_level,
            duration_ms=rec.duration_ms,
            source=rec.source,
            wayback_status=rec.wayback_status,
            checked_at=rec.checked_at,
        ))

    return ScanRecordListResponse(
        records=enriched,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


# ---------------------------------------------------------------------------
# GET /admin/activity-logs
# ---------------------------------------------------------------------------
@router.get("/activity-logs", response_model=ActivityLogListResponse)
async def get_activity_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(ActivityLog)
    if user_id:
        stmt = stmt.where(ActivityLog.user_id == user_id)
    if action:
        stmt = stmt.where(ActivityLog.action.ilike(f"%{action}%"))
    if date_from:
        stmt = stmt.where(ActivityLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(ActivityLog.created_at <= datetime.fromisoformat(date_to))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(ActivityLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    logs = (await db.execute(stmt)).scalars().all()

    return ActivityLogListResponse(
        logs=[ActivityLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


# ---------------------------------------------------------------------------
# GET /admin/login-history
# ---------------------------------------------------------------------------
@router.get("/login-history", response_model=LoginHistoryListResponse)
async def get_login_history(
    user_id: Optional[int] = Query(None),
    success: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(LoginHistory)
    if user_id:
        stmt = stmt.where(LoginHistory.user_id == user_id)
    if success is not None:
        stmt = stmt.where(LoginHistory.success == success)
    if role:
        stmt = stmt.where(LoginHistory.user_role_snapshot == role)
    if date_from:
        stmt = stmt.where(LoginHistory.login_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(LoginHistory.login_at <= datetime.fromisoformat(date_to))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(LoginHistory.login_at.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(stmt)).scalars().all()

    return LoginHistoryListResponse(
        records=[LoginHistoryResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


# ---------------------------------------------------------------------------
# GET /admin/notifications
# ---------------------------------------------------------------------------
@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(Notification)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    notifications = (await db.execute(stmt)).scalars().all()

    unread_count = (await db.execute(
        select(func.count(Notification.id)).where(Notification.is_read == False)
    )).scalar() or 0

    return {
        "notifications": [NotificationResponse.model_validate(n) for n in notifications],
        "unread_count": unread_count,
    }


# ---------------------------------------------------------------------------
# PATCH /admin/notifications/{id}/read
# ---------------------------------------------------------------------------
@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notif: Notification | None = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notif.is_read = True


# ---------------------------------------------------------------------------
# PATCH /admin/notifications/mark-all-read
# ---------------------------------------------------------------------------
@router.patch("/notifications/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    from sqlalchemy import update
    await db.execute(
        update(Notification).where(Notification.is_read == False).values(is_read=True)
    )


# ---------------------------------------------------------------------------
# GET /admin/settings (Super Admin only)
# ---------------------------------------------------------------------------
@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    settings_rows = (await db.execute(select(SystemSettings).order_by(SystemSettings.category, SystemSettings.key))).scalars().all()
    return [SystemSettingResponse.model_validate(s) for s in settings_rows]


# ---------------------------------------------------------------------------
# PUT /admin/settings (Super Admin only)
# ---------------------------------------------------------------------------
@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
async def update_settings(
    request: Request,
    body: BulkSystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    for key, value in body.settings.items():
        result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
        setting: SystemSettings | None = result.scalar_one_or_none()
        if setting:
            old_val = setting.value
            setting.value = value
            setting.updated_by = current_user.id
            setting.updated_at = _utcnow()
            await log_action(
                db,
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role,
                action="UPDATE_SETTING",
                object_type="SystemSettings",
                object_id=setting.id,
                object_label=key,
                old_value={"value": old_val},
                new_value={"value": value},
                ip_address=get_client_ip(request),
                user_agent_string=request.headers.get("User-Agent"),
            )
        else:
            new_setting = SystemSettings(key=key, value=value, updated_by=current_user.id, updated_at=_utcnow())
            db.add(new_setting)


# ---------------------------------------------------------------------------
# GET /admin/export/csv
# ---------------------------------------------------------------------------
@router.get("/export/csv")
async def export_csv(
    report_type: str = Query(..., description="activity_logs | login_history | scan_records | users"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    output = io.StringIO()

    if report_type == "users":
        writer = csv.writer(output)
        writer.writerow(["ID", "Full Name", "Username", "Email", "Role", "Status", "Department", "Created At", "Last Login"])
        rows = (await db.execute(select(User).where(User.is_deleted == False))).scalars().all()
        for u in rows:
            writer.writerow([u.id, u.full_name, u.username, u.email, u.role, u.status, u.department or "", u.created_at, u.last_login_at or ""])

    elif report_type == "login_history":
        writer = csv.writer(output)
        writer.writerow(["ID", "Username", "Role", "IP", "Browser", "Country", "Login At", "Logout At", "Success", "Failure Reason"])
        stmt = select(LoginHistory).order_by(LoginHistory.login_at.desc())
        if date_from:
            stmt = stmt.where(LoginHistory.login_at >= datetime.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(LoginHistory.login_at <= datetime.fromisoformat(date_to))
        rows = (await db.execute(stmt)).scalars().all()
        for r in rows:
            writer.writerow([r.id, r.username_attempted, r.user_role_snapshot or "", r.ip_address or "", r.browser or "", r.country or "", r.login_at, r.logout_at or "", r.success, r.failure_reason or ""])

    elif report_type == "activity_logs":
        writer = csv.writer(output)
        writer.writerow(["ID", "User", "Role", "Action", "Object Type", "Object", "IP", "Browser", "Status", "Time"])
        stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc())
        if date_from:
            stmt = stmt.where(ActivityLog.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(ActivityLog.created_at <= datetime.fromisoformat(date_to))
        rows = (await db.execute(stmt)).scalars().all()
        for r in rows:
            writer.writerow([r.id, r.username_snapshot or "", r.user_role_snapshot or "", r.action, r.object_type or "", r.object_label or "", r.ip_address or "", r.browser or "", r.status, r.created_at])

    elif report_type == "scan_records":
        writer = csv.writer(output)
        writer.writerow(["ID", "Domain", "User ID", "Status", "Risk Score", "Risk Level", "Duration(ms)", "Source", "Wayback Status", "Checked At"])
        stmt = select(ScanRecord).order_by(ScanRecord.checked_at.desc())
        if date_from:
            stmt = stmt.where(ScanRecord.checked_at >= datetime.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(ScanRecord.checked_at <= datetime.fromisoformat(date_to))
        rows = (await db.execute(stmt)).scalars().all()
        for r in rows:
            writer.writerow([r.id, r.domain_name, r.user_id or "", r.status, r.risk_score or "", r.risk_level or "", r.duration_ms or "", r.source, r.wayback_status or "", r.checked_at])
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {report_type}")

    output.seek(0)
    filename = f"{report_type}_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

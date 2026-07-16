"""
User management routes (Admin and Super Admin only).
"""
from datetime import datetime, timezone
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_admin, require_super_admin, get_client_ip
from backend.app.core.security import hash_password, validate_password_strength, generate_temp_password
from backend.app.core.audit import log_action
from backend.app.models.user import User, UserRole, UserStatus
from backend.app.models.notification import Notification
from backend.app.schemas.user_schema import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserSuspendRequest,
)
from backend.app.schemas.auth_schema import ResetPasswordRequest
from backend.app.utils.logger import logger

router = APIRouter()
_UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(_UTC).replace(tzinfo=None)


def _can_manage_target(actor: User, target: User) -> bool:
    """
    RBAC permission check: can 'actor' manage 'target'?
    - Super Admin can manage anyone.
    - Admin can only manage regular users.
    """
    if actor.role == UserRole.super_admin:
        return True
    if actor.role == UserRole.admin:
        return target.role == UserRole.user
    return False


# ---------------------------------------------------------------------------
# GET /users — list with search + filter + pagination
# ---------------------------------------------------------------------------
@router.get("", response_model=UserListResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Search by name/username/email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User).where(User.is_deleted == False)

    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(term),
                User.username.ilike(term),
                User.email.ilike(term),
            )
        )
    if role:
        stmt = stmt.where(User.role == role)
    if status_filter:
        stmt = stmt.where(User.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


# ---------------------------------------------------------------------------
# POST /users — create user
# ---------------------------------------------------------------------------
@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Admins cannot create admins or super_admins
    if current_user.role == UserRole.admin and body.role in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only create regular users.")

    # Check uniqueness
    existing = await db.execute(
        select(User).where(
            (User.username == body.username) | (User.email == body.email),
            User.is_deleted == False,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already in use.")

    if not body.password or not body.password.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password cannot be empty.")

    new_user = User(
        full_name=body.full_name,
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        department=body.department,
        status=body.status,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(new_user)
    await db.flush()

    # Notify all admins
    notif = Notification(
        notification_type="new_user",
        title="New User Created",
        message=f"{current_user.username} created user '{body.username}' ({body.role}).",
    )
    db.add(notif)

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="CREATE_USER",
        object_type="User",
        object_id=new_user.id,
        object_label=new_user.username,
        new_value={"role": body.role, "email": body.email},
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )

    return UserResponse.model_validate(new_user)


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse.model_validate(target)


# ---------------------------------------------------------------------------
# PUT /users/{user_id}
# ---------------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not _can_manage_target(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to modify this user.")

    # Admins cannot promote to admin/super_admin
    if current_user.role == UserRole.admin and body.role in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins cannot assign admin roles.")

    old = {"full_name": target.full_name, "role": target.role, "status": target.status, "email": target.email}

    if body.full_name is not None:
        target.full_name = body.full_name
    if body.username is not None:
        target.username = body.username
    if body.email is not None:
        target.email = body.email
    if body.role is not None:
        target.role = body.role
    if body.status is not None:
        target.status = body.status
    if body.department is not None:
        target.department = body.department
    target.updated_at = _utcnow()

    new = {"full_name": target.full_name, "role": target.role, "status": target.status, "email": target.email}

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="UPDATE_USER",
        object_type="User",
        object_id=target.id,
        object_label=target.username,
        old_value=old,
        new_value=new,
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )
    return UserResponse.model_validate(target)


# ---------------------------------------------------------------------------
# DELETE /users/{user_id} — soft delete
# ---------------------------------------------------------------------------
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not _can_manage_target(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to delete this user.")

    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account.")

    target.is_deleted = True
    target.deleted_at = _utcnow()
    target.status = UserStatus.suspended

    notif = Notification(
        notification_type="user_deleted",
        title="User Deleted",
        message=f"{current_user.username} deleted user '{target.username}'.",
    )
    db.add(notif)

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="DELETE_USER",
        object_type="User",
        object_id=target.id,
        object_label=target.username,
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )


# ---------------------------------------------------------------------------
# POST /users/{user_id}/suspend
# ---------------------------------------------------------------------------
@router.post("/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user_id: int,
    request: Request,
    body: UserSuspendRequest = UserSuspendRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not _can_manage_target(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

    target.status = UserStatus.suspended
    target.updated_at = _utcnow()

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="SUSPEND_USER",
        object_type="User",
        object_id=target.id,
        object_label=target.username,
        new_value={"reason": body.reason},
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )
    return UserResponse.model_validate(target)


# ---------------------------------------------------------------------------
# POST /users/{user_id}/activate
# ---------------------------------------------------------------------------
@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not _can_manage_target(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

    target.status = UserStatus.active
    target.failed_login_count = 0
    target.locked_until = None
    target.updated_at = _utcnow()

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="ACTIVATE_USER",
        object_type="User",
        object_id=target.id,
        object_label=target.username,
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )
    return UserResponse.model_validate(target)


# ---------------------------------------------------------------------------
# POST /users/{user_id}/reset-password
# ---------------------------------------------------------------------------
@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    target: User | None = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not _can_manage_target(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

    temp_password: str | None = None
    if body.new_password:
        if not body.new_password or not body.new_password.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password cannot be empty.")
        target.hashed_password = hash_password(body.new_password)
    else:
        temp_password = generate_temp_password()
        target.hashed_password = hash_password(temp_password)

    target.must_change_password = True
    target.password_changed_at = _utcnow()
    target.updated_at = _utcnow()

    # TODO: send email if body.send_email and SMTP configured

    await log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="RESET_PASSWORD",
        object_type="User",
        object_id=target.id,
        object_label=target.username,
        old_value={"password": "hidden"},
        new_value={"password": "hidden"},
        ip_address=get_client_ip(request),
        user_agent_string=request.headers.get("User-Agent"),
    )

    response: dict = {"message": "Password reset successfully.", "must_change_password": True}
    if temp_password:
        response["temp_password"] = temp_password  # Only returned once — admin must copy it
    return response

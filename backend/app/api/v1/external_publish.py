"""外部平台发布任务 API。

端点：
- POST   /api/v1/publish/tasks            创建发布任务
- GET    /api/v1/publish/tasks             任务列表
- GET    /api/v1/publish/tasks/{id}        任务详情
- POST   /api/v1/publish/tasks/{id}/retry  重试
- GET    /api/v1/publish/tasks/{id}/logs   执行日志
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ROLE_ADMIN, ROLE_OPERATOR, require_roles
from app.models import Content, PublishArtifact, SocialAccount, SocialPublicationTask, SocialPublishLog
from app.models.user import User
from app.schemas.external import (
    PublishArtifactItem,
    PublishArtifactListResponse,
    PublishLogItem,
    PublishLogListResponse,
    PublishTaskCreate,
    PublishTaskItem,
    PublishTaskListResponse,
)
from app.integrations.synapse_engine.platform_capabilities import (
    ALL_PLATFORM_NAMES,
    is_publishable,
)
from app.services.external_publish_service import (
    PLACEHOLDER_PLATFORMS,
    SUPPORTED_PLATFORMS,
    dispatch_task,
)

router = APIRouter()

_KNOWN_PLATFORMS = ALL_PLATFORM_NAMES


@router.post("/publish/tasks", response_model=PublishTaskItem, tags=["external-publish"], status_code=201)
def create_publish_task(
    payload: PublishTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """创建外部发布任务并派发到 worker（立即）或登记为定时任务。"""
    content = db.query(Content).filter(Content.id == payload.content_id).first()
    if not content:
        raise HTTPException(404, "内容不存在")
    account = db.query(SocialAccount).filter(SocialAccount.id == payload.account_id).first()
    if not account:
        raise HTTPException(404, "账号不存在")
    if payload.platform not in _KNOWN_PLATFORMS:
        raise HTTPException(400, f"不支持的平台: {payload.platform}")
    if not is_publishable(payload.platform):
        raise HTTPException(400, f"平台 {payload.platform} 待接入，暂不支持创建发布任务")
    from app.integrations.synapse_engine.utils.playwright_provider import runtime_available
    if not runtime_available():
        raise HTTPException(503, "发布运行时未安装，当前环境不能创建发布任务")
    if account.platform != payload.platform:
        raise HTTPException(400, "账号平台与发布平台不一致")

    is_schedule = payload.publish_mode == "schedule"
    if is_schedule and not payload.scheduled_at:
        raise HTTPException(400, "定时发布必须提供 scheduled_at")
    # 立即发布前置校验 cookie（定时发布到期时再校验，允许先排期）
    if not is_schedule and account.cookie_status != "active":
        raise HTTPException(400, f"账号 cookie 状态为 {account.cookie_status}，请先扫码登录")
    # 立即发布还要求账号已写回 internal_account_id（扫码登录成功后才有）
    if not is_schedule and not account.internal_account_id:
        raise HTTPException(400, "账号未完成扫码登录（缺少 internal_account_id），请先扫码登录")

    scheduled_dt = None
    if is_schedule:
        scheduled_dt = datetime.fromisoformat(payload.scheduled_at.replace("Z", "+00:00"))

    title = payload.title or content.title or content.markdown[:60]
    task = SocialPublicationTask(
        content_id=content.id,
        platform=payload.platform,
        platform_code=account.platform_code,
        social_account_id=account.id,
        title=title,
        description=payload.description or content.summary,
        topics=payload.topics,
        cover_path=payload.cover_path or content.cover_image,
        status="scheduled" if is_schedule else "pending",
        scheduled_at=scheduled_dt,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    if is_schedule:
        # 定时任务由后台扫描线程到点派发
        db.add(SocialPublishLog(
            task_id=task.id,
            level="info",
            message=f"已登记定时发布，计划时间 {payload.scheduled_at}",
        ))
        db.commit()
        db.refresh(task)
    else:
        dispatch_task(db, task, account)
        db.refresh(task)

    return PublishTaskItem.model_validate(task)


@router.get("/publish/tasks", response_model=PublishTaskListResponse, tags=["external-publish"])
def list_publish_tasks(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
    platform: Annotated[str | None, Query()] = None,
    task_status: Annotated[str | None, Query(alias="status")] = None,
    content_id: Annotated[int | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    q = db.query(SocialPublicationTask)
    if platform:
        q = q.filter(SocialPublicationTask.platform == platform)
    if task_status:
        q = q.filter(SocialPublicationTask.status == task_status)
    if content_id:
        q = q.filter(SocialPublicationTask.content_id == content_id)
    total = q.count()
    items = q.order_by(desc(SocialPublicationTask.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return PublishTaskListResponse(total=total, items=[PublishTaskItem.model_validate(t) for t in items])


@router.get("/publish/tasks/{task_id}", response_model=PublishTaskItem, tags=["external-publish"])
def get_publish_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    task = db.query(SocialPublicationTask).filter(SocialPublicationTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return PublishTaskItem.model_validate(task)


@router.post("/publish/tasks/{task_id}/retry", response_model=PublishTaskItem, tags=["external-publish"])
def retry_publish_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    task = db.query(SocialPublicationTask).filter(SocialPublicationTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(400, f"当前状态 {task.status} 不可重试")

    account = db.query(SocialAccount).filter(SocialAccount.id == task.social_account_id).first()
    if not account:
        raise HTTPException(400, "关联账号不存在")

    task.started_at = None
    task.finished_at = None
    task.error_message = None
    db.commit()

    dispatch_task(db, task, account)
    db.refresh(task)
    return PublishTaskItem.model_validate(task)


@router.get("/publish/tasks/{task_id}/logs", response_model=PublishLogListResponse, tags=["external-publish"])
def list_publish_logs(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    logs = db.query(SocialPublishLog).filter(SocialPublishLog.task_id == task_id).order_by(SocialPublishLog.created_at).all()
    return PublishLogListResponse(total=len(logs), items=[PublishLogItem.model_validate(l) for l in logs])


@router.get("/publish/tasks/{task_id}/artifacts", response_model=PublishArtifactListResponse, tags=["external-publish"])
def list_publish_artifacts(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """任务的截图/HTML 留痕列表。"""
    items = (
        db.query(PublishArtifact)
        .filter(PublishArtifact.task_id == task_id)
        .order_by(PublishArtifact.created_at)
        .all()
    )
    return PublishArtifactListResponse(
        total=len(items),
        items=[PublishArtifactItem.model_validate(a) for a in items],
    )

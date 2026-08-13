"""外部平台发布派发与定时执行服务。

集中封装：
- 已真实接入网页自动化发布的平台集合
- 把发布任务构造为 worker task_spec（解析媒体、准备截图留痕目录）
- 派发任务到线程池 worker（create / retry / 定时 共用）
- 扫描到期的定时外部发布任务并派发

不直接做 Playwright 操作；真实浏览器自动化在 synapse_engine worker 中执行。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Content, SocialAccount, SocialPublicationTask, SocialPublishLog
from app.services.media_resolver import (
    get_upload_dir,
    resolve_content_media,
    resolve_content_video,
)

logger = logging.getLogger(__name__)

# 平台能力来自单一源（platform_capabilities.py）
from app.integrations.synapse_engine.platform_capabilities import (
    IMAGE_TEXT_PLATFORMS as IMAGE_TEXT_SUPPORTED,
    PUBLISHABLE_PLATFORMS,
    VIDEO_PLATFORMS as VIDEO_SUPPORTED,
)

# 允许创建发布任务的平台（verified + beta）
SUPPORTED_PLATFORMS = PUBLISHABLE_PLATFORMS

# 仍待接入的平台：保留数据结构与 UI 位置，但不真实执行
PLACEHOLDER_PLATFORMS: set[str] = {"channels", "douyin", "kuaishou", "bilibili"}

_ARTIFACT_SUBDIR = "publish_artifacts"


def get_artifact_dir(task_id: int) -> str:
    """某任务的截图/HTML 留痕目录（uploads/publish_artifacts/<task_id>）。"""
    d = os.path.join(get_upload_dir(), _ARTIFACT_SUBDIR, str(task_id))
    os.makedirs(d, exist_ok=True)
    return d


def build_task_spec(db: Session, task: SocialPublicationTask, account: SocialAccount) -> dict:
    """把 SocialPublicationTask 构造为 worker 可执行的 task_spec。

    图文平台：media_paths = 内容封面 + 素材图（插入正文富文本）。
    短视频平台：media_paths = [视频文件]，cover_path = 视频封面（上传后设置）。
    """
    content = db.query(Content).filter(Content.id == task.content_id).first()
    spec: dict = {
        "task_id": task.id,
        "platform": task.platform,
        "account_id": account.internal_account_id or "",
        "title": task.title,
        "description": task.description or "",
        "tags": task.topics or [],
        "publish_mode": "direct",
        "artifact_dir": get_artifact_dir(task.id),
    }
    if task.platform in VIDEO_SUPPORTED:
        video = resolve_content_video(db, content, material_id=task.social_material_id)
        spec["media_paths"] = [video["video_path"]] if video["video_path"] else []
        spec["cover_path"] = video["cover_path"] or (task.cover_path or "")
        spec["is_video"] = True
    else:
        spec["media_paths"] = resolve_content_media(db, content, task.cover_path)
        spec["cover_path"] = task.cover_path or ""
        spec["is_video"] = False
    return spec


def dispatch_task(db: Session, task: SocialPublicationTask, account: SocialAccount) -> SocialPublicationTask:
    """派发发布任务到 worker。仅支持已接入平台；未接入平台标记失败。

    调用方负责事务其余部分；本函数内部 commit 自身状态变更。
    """
    if task.platform not in SUPPORTED_PLATFORMS:
        task.status = "failed"
        task.error_message = f"平台 {task.platform} 暂未接入网页自动化发布，请等待后续版本"
        task.finished_at = datetime.now(timezone.utc)
        db.add(SocialPublishLog(task_id=task.id, level="warn", message=task.error_message))
        db.commit()
        return task

    if not account.internal_account_id or account.cookie_status != "active":
        task.status = "failed"
        task.error_message = "账号未登录或 cookie 失效，请先扫码登录后重试"
        task.finished_at = datetime.now(timezone.utc)
        db.add(SocialPublishLog(task_id=task.id, level="error", message=task.error_message))
        db.commit()
        return task

    try:
        from app.integrations.synapse_engine.workers.threadpool_worker import submit_publish_task

        spec = build_task_spec(db, task, account)
        # 短视频平台必须有视频文件，否则无法发布
        if spec.get("is_video") and not spec.get("media_paths"):
            task.status = "failed"
            task.error_message = "未找到可发布的视频文件，请先为内容绑定视频素材（本地文件）"
            task.finished_at = datetime.now(timezone.utc)
            db.add(SocialPublishLog(task_id=task.id, level="error", message=task.error_message))
            db.commit()
            return task

        submit_publish_task(task.id, spec)
        task.status = "queued"
        task.error_message = None
        media_count = len(spec["media_paths"])
        media_desc = f"{media_count} 个视频" if spec.get("is_video") else f"{media_count} 张图片"
        db.add(SocialPublishLog(
            task_id=task.id,
            level="info",
            message=f"已派发到发布引擎（{media_desc}）",
        ))
        db.commit()
    except ImportError:
        task.status = "failed"
        task.error_message = "发布引擎未安装（缺少 playwright 依赖）"
        task.finished_at = datetime.now(timezone.utc)
        db.add(SocialPublishLog(task_id=task.id, level="error", message=task.error_message))
        db.commit()
    except Exception as e:  # noqa: BLE001
        task.status = "failed"
        task.error_message = f"派发任务失败: {e}"
        task.finished_at = datetime.now(timezone.utc)
        db.add(SocialPublishLog(task_id=task.id, level="error", message=task.error_message))
        db.commit()
    return task


def run_scheduled_external_publish(db: Session) -> int:
    """扫描到期的定时外部发布任务并派发，返回派发数量。"""
    now = datetime.now(timezone.utc)
    due = (
        db.query(SocialPublicationTask)
        .filter(
            SocialPublicationTask.status == "scheduled",
            SocialPublicationTask.scheduled_at.isnot(None),
            SocialPublicationTask.scheduled_at <= now,
        )
        .all()
    )
    count = 0
    for task in due:
        account = db.query(SocialAccount).filter(SocialAccount.id == task.social_account_id).first()
        if not account:
            task.status = "failed"
            task.error_message = "关联账号不存在，定时发布取消"
            task.finished_at = now
            db.add(SocialPublishLog(task_id=task.id, level="error", message=task.error_message))
            db.commit()
            continue
        dispatch_task(db, task, account)
        count += 1
    return count


__all__ = [
    "SUPPORTED_PLATFORMS",
    "IMAGE_TEXT_SUPPORTED",
    "VIDEO_SUPPORTED",
    "PLACEHOLDER_PLATFORMS",
    "get_artifact_dir",
    "build_task_spec",
    "dispatch_task",
    "run_scheduled_external_publish",
]

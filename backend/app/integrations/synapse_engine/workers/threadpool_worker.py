"""Synapse 线程池 worker（替代 Celery）。

用 ThreadPoolExecutor + asyncio.run 执行发布任务，不引入 Celery/Redis。
- submit_publish_task(task_id, task_spec): 提交发布任务到线程池
- submit_cookie_validate(account_id, platform): 提交 cookie 校验
- _run_publish_in_thread(task_id, task_spec): 线程内执行，用 asyncio.run 跑 Playwright
- _writeback_result(task_id, result): 同步写库（用 SessionLocal）

设计原则：
1. 线程池任务为同步函数，内部用 asyncio.run() 启动 event loop 执行协程
2. 任务执行后直接通过 SessionLocal 写回 social_publication_task 表
3. 单任务单线程单浏览器，避免 Playwright 资源竞争
"""
from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import PublishArtifact, SocialPublicationTask, SocialPublishLog

logger = logging.getLogger(__name__)

# Playwright 资源较重，限制并发数
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="synapse-worker")


def submit_publish_task(task_id: str, task_spec: dict) -> None:
    """提交发布任务到线程池（立即返回，不阻塞）。"""
    _executor.submit(_run_publish_in_thread, task_id, task_spec)


def submit_cookie_validate(account_id: str, platform: str) -> None:
    """提交 cookie 校验任务到线程池（立即返回，不阻塞）。"""
    _executor.submit(_run_cookie_validate_in_thread, account_id, platform)


def _run_publish_in_thread(task_id: str, task_spec: dict) -> None:
    """线程内执行发布任务，用 asyncio.run 跑 Playwright，完成后同步写库。"""
    logger.info("[SynapseWorker] 开始执行发布任务 task_id=%s", task_id)

    # 标记任务进入 running（仅对整数形态的 task_id 生效）
    try:
        _mark_publish_running(task_id)
    except Exception as mark_err:
        logger.warning("[SynapseWorker] 标记 running 失败 task_id=%s: %s", task_id, mark_err)

    try:
        # 延迟导入避免循环依赖
        from app.integrations.synapse_engine.publish import Publisher
        from app.integrations.synapse_engine.utils.playwright_provider import (
            configure_windows_event_loop,
        )

        configure_windows_event_loop()

        async def _run():
            publisher = Publisher()
            return await publisher.run(task_spec)

        result = asyncio.run(_run())
        logger.info(
            "[SynapseWorker] 发布任务完成 task_id=%s success=%s status=%s",
            task_id, result.get("success"), result.get("status"),
        )
    except Exception as e:
        logger.exception("[SynapseWorker] 发布任务异常 task_id=%s", task_id)
        result = {
            "task_id": task_id,
            "success": False,
            "status": "worker_error",
            "error": str(e),
            "platform": task_spec.get("platform", ""),
        }

    # 同步写回 DB（不依赖 /result API）
    try:
        _writeback_result(task_id, result)
    except Exception as wb_err:
        logger.exception(
            "[SynapseWorker] 写回 DB 失败 task_id=%s: %s", task_id, wb_err
        )


def _run_cookie_validate_in_thread(account_id: str, platform: str) -> None:
    """线程内执行 cookie 校验。"""
    logger.info("[SynapseWorker] 校验 cookie platform=%s account_id=%s", platform, account_id)
    try:
        from app.integrations.synapse_engine.service import EmbeddedSynapseService
        from app.integrations.synapse_engine.utils.playwright_provider import (
            configure_windows_event_loop,
        )

        configure_windows_event_loop()

        async def _run():
            service = EmbeddedSynapseService()
            return await service.validate_cookie_async(platform, account_id)

        result = asyncio.run(_run())
        logger.info(
            "[SynapseWorker] cookie 校验完成 platform=%s valid=%s",
            platform, result.get("valid"),
        )
    except Exception as e:
        logger.exception("[SynapseWorker] cookie 校验异常 platform=%s", platform)


def _mark_publish_running(task_id: str) -> None:
    """任务开始时把状态从 pending 改为 running（找不到任务则跳过）。"""
    pub_id = _parse_task_id(task_id)
    if pub_id is None:
        return
    with SessionLocal() as db:
        task = db.execute(
            select(SocialPublicationTask).where(SocialPublicationTask.id == pub_id)
        ).scalar_one_or_none()
        if task is not None and task.status == "pending":
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            db.commit()


def _writeback_result(task_id: str, result: dict[str, Any]) -> None:
    """把发布结果同步写回 social_publication_task 表。

    Args:
        task_id: 任务 ID（SocialPublicationTask.id 整数）
        result: Publisher.run 返回的结果 dict，字段：
            - success: bool
            - status: published|filled|cookie_missing|publish_error|...
            - external_post_id: str | None
            - publish_url: str | None
            - error: str | None
            - message: str | None
    """
    pub_id = _parse_task_id(task_id)
    if pub_id is None:
        logger.warning(
            "_writeback_result: task_id=%s 不是合法整数，跳过 DB 写回",
            task_id,
        )
        return

    success_flag = bool(result.get("success"))
    status = result.get("status", "unknown")
    # filled / publish_unknown 视为发布未完成（只填表没点击发布）→ 不算成功
    if status in ("filled", "publish_unknown"):
        success_flag = False
        status = "failed"

    # 映射到 SocialPublicationTask.status 枚举：success | failed
    task_status = "success" if success_flag else "failed"

    with SessionLocal() as db:
        task = db.execute(
            select(SocialPublicationTask).where(SocialPublicationTask.id == pub_id)
        ).scalar_one_or_none()
        if task is None:
            logger.warning(
                "_writeback_result: SocialPublicationTask %s 不存在，跳过写回",
                pub_id,
            )
            return

        # 任务已被取消则不覆盖状态
        if task.status == "cancelled":
            logger.info(
                "_writeback_result: 任务 %s 已取消，不覆盖状态",
                pub_id,
            )
            return

        # 更新任务状态
        task.status = task_status
        task.error_message = result.get("error") or result.get("message") or task.error_message
        task.finished_at = datetime.now(timezone.utc)
        # 保存原始响应（截图路径较大，raw_response 不落 artifacts 明细）
        task.raw_response = {k: v for k, v in result.items() if k != "artifacts"}
        if result.get("publish_url"):
            task.error_message = None

        # 写日志
        log_level = "info" if success_flag else "error"
        log_message = (
            result.get("message")
            or result.get("error")
            or f"任务执行完成，状态: {status}"
        )
        db.add(SocialPublishLog(
            task_id=task.id,
            level=log_level,
            message=log_message,
        ))

        # 截图/HTML 留痕落库
        _save_artifacts(db, task.id, result.get("artifacts") or [])

        db.commit()
        logger.info(
            "_writeback_result: 任务 %s 写回成功 status=%s success=%s",
            pub_id, task_status, success_flag,
        )


def _save_artifacts(db, task_id: int, artifacts: list[dict]) -> None:
    """把 adapter 返回的截图/HTML 制品写入 publish_artifact 表。"""
    if not artifacts:
        return
    from app.services.media_resolver import to_served_url

    for art in artifacts:
        path = art.get("path") or ""
        filename = art.get("filename") or (path.rsplit("/", 1)[-1] if path else "artifact")
        url = to_served_url(path) if path else None
        if not url and path:
            url = f"/uploads/publish_artifacts/{task_id}/{filename}"
        db.add(PublishArtifact(
            task_id=task_id,
            artifact_type=art.get("type") or "screenshot",
            filename=filename,
            file_path=path,
            url=url,
            note=art.get("note"),
        ))


def _parse_task_id(task_id: str) -> int | None:
    """把 task_id 解析为整数（SocialPublicationTask.id）。解析失败返回 None。"""
    try:
        return int(str(task_id))
    except (ValueError, TypeError):
        return None


__all__ = [
    "submit_publish_task",
    "submit_cookie_validate",
    "_run_publish_in_thread",
    "_writeback_result",
]

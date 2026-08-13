"""Publisher - 高级发布编排器。

由 ThreadPoolExecutor worker 调用。接收一个发布任务规格（task spec），
调用 EmbeddedSynapseService 执行发布，并返回结果给 worker 用于回写
social_publication_task 表。

不直接访问 DB（避免与 repository 层循环依赖）。
"""
from __future__ import annotations

import logging
from typing import Any

from app.integrations.synapse_engine.service import EmbeddedSynapseService

logger = logging.getLogger(__name__)


class Publisher:
    """高级发布编排器（worker 内部使用）。"""

    def __init__(self, service: EmbeddedSynapseService | None = None):
        self.service = service or EmbeddedSynapseService()

    async def run(self, task_spec: dict) -> dict:
        """执行发布任务（async，由 worker 用 asyncio.run 包装）。

        直接 await service.publish_content_async，在 worker 的事件循环中
        运行 Playwright，避免与 service 后台循环交叉。

        Args:
            task_spec: 发布任务规格，包含字段：
                - task_id: 任务 ID
                - platform: 平台
                - account_id: 账号 ID
                - title: 标题
                - description: 正文
                - tags: 标签列表
                - media_paths: 媒体文件本地路径列表
                - cover_path: 封面图本地路径
                - publish_mode: direct|schedule
                - scheduled_at: 定时发布时间（ISO）

        Returns:
            {
                "task_id": "...",
                "success": True/False,
                "status": "published|filled|cookie_missing|publish_error|...",
                "platform": "...",
                "external_post_id": "...",  # 可能没有
                "publish_url": "...",       # 可能没有
                "error": "...",             # 失败时
            }
        """
        task_id = task_spec.get("task_id")
        platform = task_spec.get("platform", "")
        account_id = task_spec.get("account_id", "")
        title = task_spec.get("title", "")
        description = task_spec.get("description", "")
        tags = task_spec.get("tags") or []
        media_paths = task_spec.get("media_paths") or []
        cover_path = task_spec.get("cover_path")
        publish_mode = task_spec.get("publish_mode", "direct")
        scheduled_at = task_spec.get("scheduled_at")
        artifact_dir = task_spec.get("artifact_dir")

        logger.info(
            "Publisher.run task_id=%s platform=%s account_id=%s media_count=%d",
            task_id, platform, account_id, len(media_paths),
        )

        try:
            result = await self.service.publish_content_async(
                platform=platform,
                account_id=account_id,
                title=title,
                description=description,
                tags=tags,
                media_paths=media_paths,
                cover_path=cover_path,
                publish_mode=publish_mode,
                scheduled_at=scheduled_at,
                artifact_dir=artifact_dir,
            )
        except Exception as e:
            logger.exception("Publisher 执行异常 task_id=%s", task_id)
            return {
                "task_id": task_id,
                "success": False,
                "status": "publish_error",
                "error": str(e),
                "platform": platform,
                "artifacts": [],
            }

        # 统一返回字段
        success = bool(result.get("success"))
        status = result.get("status", "unknown")
        return {
            "task_id": task_id,
            "success": success,
            "status": status,
            "platform": platform,
            "external_post_id": result.get("external_post_id"),
            "publish_url": result.get("publish_url"),
            "message": result.get("message"),
            "error": result.get("error"),
            "artifacts": result.get("artifacts") or [],
        }


__all__ = ["Publisher"]

"""EmbeddedSynapseService - Synapse 内嵌发布引擎对外服务（同步版本）。

统一封装：
1. 扫码登录：start_login / poll_login_status / cancel_login
2. Cookie 校验：validate_account_cookie
3. 内容发布：publish_content（由 ThreadPoolExecutor worker 调用）
4. 平台适配器加载：通过 platforms.get_platform_adapter

所有公共方法均为同步（普通 def），内部通过后台守护线程中的持久事件循环
执行 Playwright 异步操作。不引入 Celery/Redis，Playwright 操作保留 async。
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from app.core.config import get_settings
from app.integrations.synapse_engine.cookie import CookieManager
from app.integrations.synapse_engine.platforms import get_platform_adapter
from app.integrations.synapse_engine.platforms.base import (
    LoginResult,
    LoginStatus,
    QRCodeData,
    PlatformAdapter,
)
from app.integrations.synapse_engine.platforms.codes import (
    CODE_TO_PLATFORM,
    PLATFORM_CODES,
    PLATFORM_NAMES,
    normalize_platform,
    resolve_platform_code,
)
from app.integrations.synapse_engine.utils.playwright_provider import (
    configure_windows_event_loop,
)

logger = logging.getLogger(__name__)


class EmbeddedSynapseService:
    """Synapse 内嵌引擎服务（单例，同步版本）。

    同步方法内部通过后台守护线程中的持久事件循环执行 Playwright 协程。

    为什么用持久事件循环而非 asyncio.run()：
    扫码登录流程跨多次调用（start_login -> poll_login_status），
    Playwright 浏览器会话必须在调用间保持存活；asyncio.run() 每次
    创建并关闭事件循环，会导致浏览器连接丢失。因此本服务在后台守护
    线程中运行一个持久事件循环，通过 run_coroutine_threadsafe 提交协程，
    既保证同步调用语义，又保留浏览器状态。

    线程安全：_login_sessions 由 threading.Lock 保护。
    """

    _instance: "EmbeddedSynapseService | None" = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "EmbeddedSynapseService":
        with cls._init_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.settings = get_settings()
        self.cookie_manager = CookieManager()
        # 进行中的扫码会话：<session_id, {adapter, platform, account_id, started_at}>
        self._login_sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        # 后台持久事件循环（懒启动）
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready = threading.Event()

    # ===== 后台事件循环 =====

    def _ensure_loop(self) -> None:
        """启动后台事件循环（守护线程），仅启动一次。"""
        if self._loop is not None and self._loop.is_running():
            return
        with self._init_lock:
            if self._loop is not None and self._loop.is_running():
                return
            configure_windows_event_loop()
            self._loop = asyncio.new_event_loop()

            def _run_loop() -> None:
                asyncio.set_event_loop(self._loop)
                self._loop_ready.set()
                self._loop.run_forever()

            t = threading.Thread(target=_run_loop, name="synapse-async-loop", daemon=True)
            t.start()
            self._loop_ready.wait(timeout=5)

    def _run_async(self, coro):
        """把协程提交到后台事件循环执行，同步等待结果。"""
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    # ===== 扫码登录 =====

    def start_login(self, platform: str, account_id: str | None = None) -> dict:
        """启动扫码登录流程，返回二维码信息。

        Args:
            platform: 平台代码（xiaohongshu/douyin/...）
            account_id: 可选，账号 ID（用于关联 cookie 文件）

        Returns:
            {
                "session_id": "...",
                "platform": "...",
                "qr_image": "data:image/png;base64,...",
                "qr_url": "...",
                "expires_in": 300,
            }

        Notes:
            session_id 由 adapter.get_qrcode() 内部生成并返回（qr.session_id），
            service 直接复用该 ID 作为会话标识，确保 poll_login_status 能找到
            adapter 内部的浏览器会话。
        """
        return self._run_async(self._start_login_async(platform, account_id))

    async def _start_login_async(self, platform: str, account_id: str | None = None) -> dict:
        platform = normalize_platform(platform)
        if not platform:
            raise ValueError("platform 不能为空")

        adapter = get_platform_adapter(platform, config={"headless": True})
        qr: QRCodeData = await adapter.get_qrcode()

        # 统一使用 qr.session_id，确保 poll_status 能找到 adapter 内部会话
        session_id = qr.session_id
        account_id = account_id or f"temp_{session_id[:8]}"

        with self._lock:
            self._login_sessions[session_id] = {
                "adapter": adapter,
                "platform": platform,
                "account_id": account_id,
                "qr_data": qr,
                "started_at": time.time(),
                "last_result": None,
            }

        logger.info(
            "start_login platform=%s session_id=%s account_id=%s",
            platform, session_id, account_id,
        )

        return {
            "session_id": session_id,
            "platform": platform,
            "platform_name": PLATFORM_NAMES.get(platform, platform),
            "account_id": account_id,
            "qr_image": qr.qr_image,
            "qr_url": qr.qr_url,
            "expires_in": qr.expires_in,
        }

    def poll_login_status(self, session_id: str) -> dict:
        """轮询扫码登录状态。

        Args:
            session_id: start_login 返回的 session_id（与 adapter 内部会话 ID 一致）

        Returns:
            {
                "status": "waiting|scanned|confirmed|failed|expired",
                "message": "...",
                "platform": "...",
                "account_id": "...",
                "user_info": {...} | None,
                "saved": bool,
            }
        """
        return self._run_async(self._poll_login_status_async(session_id))

    async def _poll_login_status_async(self, session_id: str) -> dict:
        with self._lock:
            sess = self._login_sessions.get(session_id)
        if not sess:
            return {
                "status": LoginStatus.EXPIRED.value,
                "message": "session 不存在或已过期",
            }

        # 超时
        if time.time() - sess["started_at"] > 300:
            await self._cleanup_session_async(session_id)
            return {
                "status": LoginStatus.EXPIRED.value,
                "message": "二维码已过期，请重新获取",
            }

        adapter: PlatformAdapter = sess["adapter"]
        # session_id 与 adapter 内部会话 ID 一致，poll_status 能找到会话
        result: LoginResult = await adapter.poll_status(session_id)
        sess["last_result"] = result

        if result.status == LoginStatus.CONFIRMED:
            # 登录成功，保存 storage_state
            platform = sess["platform"]
            account_id = sess["account_id"]
            if result.full_state:
                self.cookie_manager.save(platform, account_id, result.full_state)
            # 清理会话（关闭浏览器）
            await self._cleanup_session_async(session_id)

            return {
                "status": LoginStatus.CONFIRMED.value,
                "message": result.message or "登录成功",
                "platform": platform,
                "account_id": account_id,
                "user_info": _user_info_to_dict(result.user_info),
                "saved": True,
            }

        return {
            "status": result.status.value,
            "message": result.message or "",
            "platform": sess["platform"],
            "account_id": sess["account_id"],
        }

    def cancel_login(self, session_id: str) -> dict:
        """取消扫码登录会话。"""
        return self._run_async(self._cancel_login_async(session_id))

    async def _cancel_login_async(self, session_id: str) -> dict:
        await self._cleanup_session_async(session_id)
        return {"session_id": session_id, "status": "cancelled"}

    async def _cleanup_session_async(self, session_id: str) -> None:
        with self._lock:
            sess = self._login_sessions.pop(session_id, None)
        if not sess:
            return
        adapter: PlatformAdapter = sess["adapter"]
        try:
            await adapter.cleanup_session(session_id)
        except Exception as e:
            logger.warning("清理 session %s 失败: %s", session_id, e)

    # ===== Cookie 校验 =====

    def validate_account_cookie(self, platform: str, account_id: str) -> dict:
        """校验账号 cookie 是否仍有效。"""
        return self._run_async(self.validate_cookie_async(platform, account_id))

    async def validate_cookie_async(self, platform: str, account_id: str) -> dict:
        """校验 storage_state 是否有效（async 实现，可供 worker 直接 await）。"""
        platform = normalize_platform(platform)
        storage_state = self.cookie_manager.load(platform, account_id)
        if not storage_state:
            return {"valid": False, "reason": "未找到本地 cookie，请先扫码登录"}

        adapter = get_platform_adapter(platform)
        result = await adapter.validate_cookie(storage_state)
        if not result.get("valid"):
            # 校验失败时删除失效 cookie
            self.cookie_manager.delete(platform, account_id)
        return result

    # ===== 内容发布 =====

    def publish_content(
        self,
        platform: str,
        account_id: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        media_paths: list[str] | None = None,
        cover_path: str | None = None,
        publish_mode: str = "direct",
        scheduled_at: str | None = None,
        artifact_dir: str | None = None,
    ) -> dict:
        """发布内容到指定平台（同步）。

        Playwright 操作在后台事件循环中执行，不阻塞调用线程的事件循环。
        """
        return self._run_async(self.publish_content_async(
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
        ))

    async def publish_content_async(
        self,
        platform: str,
        account_id: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        media_paths: list[str] | None = None,
        cover_path: str | None = None,
        publish_mode: str = "direct",
        scheduled_at: str | None = None,
        artifact_dir: str | None = None,
    ) -> dict:
        """发布内容到指定平台（async 实现，可供 Publisher 直接 await）。"""
        platform = normalize_platform(platform)
        storage_state = self.cookie_manager.load(platform, account_id)
        if not storage_state:
            return {
                "success": False,
                "status": "cookie_missing",
                "error": f"未找到 {platform} 账号 {account_id} 的 cookie，请先扫码登录",
                "artifacts": [],
            }

        adapter = get_platform_adapter(platform)
        try:
            result = await adapter.publish_content(
                storage_state=storage_state,
                title=title,
                description=description,
                tags=tags or [],
                media_paths=media_paths or [],
                cover_path=cover_path,
                publish_mode=publish_mode,
                scheduled_at=scheduled_at,
                artifact_dir=artifact_dir,
            )
            # 发布成功后 cookie 可能已更新（页面刷新 cookie），尝试重新保存
            # 这里不强制更新，因为多数情况下 storage_state 不变
            return result
        except Exception as e:
            logger.exception("发布到 %s 失败", platform)
            return {
                "success": False,
                "status": "publish_error",
                "error": str(e),
                "artifacts": [],
            }

    # ===== 账号管理 =====

    def list_saved_accounts(self, platform: str | None = None) -> list[dict]:
        """列出已保存 cookie 的账号。"""
        return self.cookie_manager.list_accounts(platform)

    def get_account_cookie_path(self, platform: str, account_id: str) -> str | None:
        """获取账号 cookie 文件路径。"""
        from pathlib import Path
        p = self.cookie_manager._path(platform, account_id)
        return str(p) if p.exists() else None

    def delete_account_cookie(self, platform: str, account_id: str) -> bool:
        """删除账号 cookie 文件。"""
        return self.cookie_manager.delete(platform, account_id)

    # ===== 平台元数据 =====

    @staticmethod
    def list_platforms() -> list[dict]:
        """返回支持的平台列表。"""
        return [
            {
                "code": code,
                "platform": plat,
                "name": PLATFORM_NAMES.get(plat, plat),
            }
            for plat, code in PLATFORM_CODES.items()
        ]

    @staticmethod
    def resolve_platform(code_or_name: str) -> str | None:
        """把平台 code（数字或名字）规范化为 platform 字符串。"""
        return normalize_platform(code_or_name)


def _user_info_to_dict(user_info) -> dict | None:
    if user_info is None:
        return None
    return {
        "user_id": user_info.user_id,
        "name": user_info.name,
        "username": user_info.username,
        "avatar": user_info.avatar,
        "extra": user_info.extra or {},
    }


__all__ = ["EmbeddedSynapseService"]

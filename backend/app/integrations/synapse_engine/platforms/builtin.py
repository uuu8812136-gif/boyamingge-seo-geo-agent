"""内置平台适配器（不依赖外部 D:\\social-auto-stack 源码）。

通过 Playwright 直接驱动浏览器完成扫码登录和真实发布：
- 扫码登录：打开登录页 -> 截屏作为二维码 -> 轮询登录态
- 发布内容：加载 storage_state -> 打开发布页 -> 填表 -> 上传素材 -> 点击发布按钮 -> 等待发布成功

各平台发布按钮选择器和成功判定已内置（不再依赖 SYNAPSE_SRC_DIR）。
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
import uuid
from typing import Any

from app.integrations.synapse_engine.platforms.base import (
    LoginResult,
    LoginStatus,
    PlatformAdapter,
    QRCodeData,
    UserInfo,
)
from app.integrations.synapse_engine.platforms.codes import (
    PLATFORM_LOGIN_URLS,
    PLATFORM_NAMES,
    PLATFORM_PUBLISH_URLS,
)

logger = logging.getLogger(__name__)


# 各平台发布按钮选择器（按优先级排列，第一个命中的就用）
# 这些选择器来自原 SynapseAutomation 项目 platforms/<platform>/upload.py 的真实实现
_PLATFORM_PUBLISH_BUTTON_SELECTORS: dict[str, list[str]] = {
    "douyin": [
        'button:has-text("发布")',
        'div.publish-btn',
        '.publish-content-btn [class*="publish"]',
    ],
    "xiaohongshu": [
        'button:has-text("发布")',
        'div.publishBtn',
        '.publish-content .btn',
    ],
    "kuaishou": [
        'button:has-text("发布")',
        '.publish-btn',
        'div[class*="publish"] button',
    ],
    "bilibili": [
        'button:has-text("立即投稿")',
        'button:has-text("发布")',
        '.submit-btn [class*="publish"]',
    ],
    "channels": [
        'button:has-text("发表")',
        'button:has-text("发布")',
        '.publish-btn',
    ],
    # ── 图文平台：百家号图文 / 知乎文章（选择器待真实账号联调验证）──
    "baijiahao": [
        'button:has-text("发布")',
        '.op-btn-publish',
        'button.publish-btn',
    ],
    "zhihu": [
        'button:has-text("发布")',
        '.PublishPanel-triggerButton',
        'button.Button--primary:has-text("发布")',
    ],
}

# 各平台发布成功后的 URL 片段（用于判断发布是否成功）
_PLATFORM_SUCCESS_URL_PATTERNS: dict[str, list[str]] = {
    "douyin": [r"creator-micro/content/manage", r"creator.douyin.com/creator-micro"],
    "xiaohongshu": [r"publish/success", r"creator\.xiaohongshu\.com/publish/publish\?done"],
    "kuaishou": [r"cp\.kuaishou\.com/article/publish/success", r"article/manage"],
    "bilibili": [r"member\.bilibili\.com/platform/upload-manager"],
    "channels": [r"channels\.weixin\.qq\.com/platform/post/list"],
    # ── 图文平台发布成功 URL 模式（待真实账号联调验证）──
    "baijiahao": [r"baijiahao\.baidu\.com/builder/rc/(home|content|contentlist)", r"baijiahao\.baidu\.com/builder/rc/clue"],
    "zhihu": [r"zhuanlan\.zhihu\.com/p/\d+", r"zhihu\.com/people/"],
}

# 各平台标题输入框选择器（按优先级排列）
_PLATFORM_TITLE_SELECTORS: dict[str, list[str]] = {
    "douyin": [
        'div[contenteditable="true"].ace-editor',
        'textarea[placeholder*="标题"]',
        'input[placeholder*="标题"]',
    ],
    "xiaohongshu": [
        'div[contenteditable="true"][placeholder*="标题"]',
        'input[placeholder*="标题"]',
        '.title input',
    ],
    "kuaishou": [
        'input[placeholder*="标题"]',
        'textarea[placeholder*="标题"]',
        '.title-input input',
    ],
    "bilibili": [
        '.input-title textarea',
        'textarea[placeholder*="标题"]',
        'input[placeholder*="标题"]',
    ],
    "channels": [
        'textarea[placeholder*="标题"]',
        'input[placeholder*="标题"]',
        '.title-input input',
    ],
    # ── 图文平台标题输入框选择器（待真实账号联调验证）──
    "baijiahao": [
        'textarea[placeholder*="请输入标题"]',
        'input[placeholder*="标题"]',
        'textarea[placeholder*="标题"]',
        '.cheetah-input',
    ],
    "zhihu": [
        'textarea[placeholder*="标题"]',
        '.WriteIndex-titleInput textarea',
        '.Editable-title textarea',
        'input[placeholder*="标题"]',
    ],
}

# 各平台正文/描述选择器
_PLATFORM_BODY_SELECTORS: dict[str, list[str]] = {
    "douyin": [
        'div[contenteditable="true"].ace-editor:not([class*="title"])',
        'textarea[placeholder*="描述"]',
        '.desc-input [contenteditable]',
    ],
    "xiaohongshu": [
        'div[contenteditable="true"][placeholder*="正文"]',
        'div[contenteditable="true"][placeholder*="描述"]',
        '.desc-input [contenteditable]',
    ],
    "kuaishou": [
        'textarea[placeholder*="描述"]',
        'div[contenteditable="true"]',
    ],
    "bilibili": [
        '.ql-editor[contenteditable="true"]',
        'textarea[placeholder*="简介"]',
        'div[contenteditable="true"]',
    ],
    "channels": [
        'textarea[placeholder*="描述"]',
        'div[contenteditable="true"]',
    ],
    # ── 图文平台正文（富文本编辑器）选择器（待真实账号联调验证）──
    "baijiahao": [
        '.ProseMirror[contenteditable="true"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="正文"]',
    ],
    "zhihu": [
        '.public-DraftEditor-content[contenteditable="true"]',
        '.Editable-content[contenteditable="true"]',
        'div[contenteditable="true"]',
    ],
}

# 各平台文件上传 input 选择器
_PLATFORM_FILE_INPUT_SELECTORS: dict[str, list[str]] = {
    "douyin": ['input[type="file"][accept*="video"]', 'input[type="file"]'],
    "xiaohongshu": ['input[type="file"][accept*="image"]', 'input[type="file"][accept*="video"]', 'input[type="file"]'],
    "kuaishou": ['input[type="file"][accept*="video"]', 'input[type="file"]'],
    "bilibili": ['input[type="file"][accept*="video"]', 'input[type="file"]'],
    "channels": ['input[type="file"][accept*="video"]', 'input[type="file"]'],
    # ── 图文平台正文插图 input 选择器（待真实账号联调验证）──
    "baijiahao": ['input[type="file"][accept*="image"]', 'input[type="file"]'],
    "zhihu": ['input[type="file"][accept*="image"]', 'input[type="file"]'],
}

# 图文平台正文插图工具按钮（点击后弹出隐藏的 file input）
_PLATFORM_IMAGE_BUTTON_SELECTORS: dict[str, list[str]] = {
    "baijiahao": [
        'button:has-text("图片")',
        '[title="图片"]',
        '.edui-for-insertimage',
    ],
    "zhihu": [
        'button[aria-label="图片"]',
        'button:has-text("图片")',
        '.Editable-toolbarMenu button[aria-label*="图片"]',
    ],
}


class BuiltinPlatformAdapter(PlatformAdapter):
    """通用内置平台适配器。

    使用 Playwright 驱动浏览器：
    - 扫码登录：打开登录页 -> 截屏作为二维码 -> 轮询登录态
    - 发布内容：加载 storage_state -> 打开发布页 -> 填表 -> 上传素材 -> 点击发布按钮 -> 等待发布成功
    """

    def __init__(self, platform: str, config: dict | None = None):
        self.platform = (platform or "").strip().lower()
        self.config = config or {}
        self.login_url = PLATFORM_LOGIN_URLS.get(self.platform, "")
        self.publish_url = PLATFORM_PUBLISH_URLS.get(self.platform, "")
        self.platform_name = PLATFORM_NAMES.get(self.platform, self.platform)
        # session_id -> {page, context, browser, created_at, last_status}
        self._sessions: dict[str, dict[str, Any]] = {}

    async def _launch_browser(self, headless: bool | None = None, storage_state: dict | None = None):
        """启动浏览器并返回 (browser, context)。"""
        from app.core.config import get_settings
        from app.integrations.synapse_engine.utils.playwright_provider import async_playwright

        settings = get_settings()
        headless = settings.synapse_playwright_headless if headless is None else headless

        pw = await async_playwright().start()
        launch_kwargs: dict[str, Any] = {"headless": headless}
        if settings.synapse_local_chrome_path:
            launch_kwargs["executable_path"] = settings.synapse_local_chrome_path

        browser = await pw.chromium.launch(**launch_kwargs)
        context_kwargs: dict[str, Any] = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            "viewport": {"width": 1280, "height": 800},
        }
        if storage_state:
            context_kwargs["storage_state"] = storage_state
        context = await browser.new_context(**context_kwargs)
        # 把 pw 挂到 browser 上方便后续 stop
        browser._synapse_pw = pw  # type: ignore[attr-defined]
        return browser, context

    async def _close_browser(self, browser) -> None:
        pw = getattr(browser, "_synapse_pw", None)
        try:
            await browser.close()
        except Exception:
            pass
        if pw is not None:
            try:
                await pw.stop()
            except Exception:
                pass

    async def get_qrcode(self) -> QRCodeData:
        """打开登录页，截屏整个页面作为二维码图返回。"""
        if not self.login_url:
            raise RuntimeError(f"平台 {self.platform} 未配置登录页 URL")

        session_id = uuid.uuid4().hex
        browser, context = await self._launch_browser(headless=True)
        page = await context.new_page()
        try:
            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=30000)
            # 等二维码区域出现（多数平台 2-3 秒内出现）
            await asyncio.sleep(3)
            screenshot = await page.screenshot(full_page=False)
            qr_base64 = base64.b64encode(screenshot).decode("ascii")
        except Exception as e:
            await self._close_browser(browser)
            raise RuntimeError(f"获取 {self.platform} 登录二维码失败: {e}") from e

        self._sessions[session_id] = {
            "browser": browser,
            "context": context,
            "page": page,
            "created_at": time.time(),
            "last_status": LoginStatus.WAITING,
            "cookies": None,
        }

        return QRCodeData(
            session_id=session_id,
            qr_url=self.login_url,
            qr_image=f"data:image/png;base64,{qr_base64}",
            expires_in=300,
        )

    async def poll_status(self, session_id: str) -> LoginResult:
        sess = self._sessions.get(session_id)
        if not sess:
            return LoginResult(
                status=LoginStatus.EXPIRED,
                message="会话不存在或已过期",
                cookies=None,
                user_info=None,
            )

        # 超时检查（5 分钟过期）
        if time.time() - sess["created_at"] > 300:
            await self.cleanup_session(session_id)
            return LoginResult(
                status=LoginStatus.EXPIRED,
                message="二维码已过期",
                cookies=None,
                user_info=None,
            )

        page = sess.get("page")
        if page is None or page.is_closed():
            await self.cleanup_session(session_id)
            return LoginResult(
                status=LoginStatus.EXPIRED,
                message="浏览器页面已关闭",
                cookies=None,
                user_info=None,
            )

        try:
            current_url = page.url
            # 简单判断：URL 变化（离开了登录页）= 登录成功
            if self.login_url and current_url != self.login_url and "login" not in current_url.lower():
                # 获取 cookies 和 storage_state
                context = sess["context"]
                cookies = await context.cookies()
                storage_state = await context.storage_state()
                sess["cookies"] = cookies
                sess["storage_state"] = storage_state
                sess["last_status"] = LoginStatus.CONFIRMED

                # 尝试抓取用户名（通用方法：找页面上的头像 alt 或用户名元素）
                user_info = await self._extract_user_info(page)

                return LoginResult(
                    status=LoginStatus.CONFIRMED,
                    message="登录成功",
                    cookies=cookies,
                    user_info=user_info,
                    full_state=storage_state,
                )

            # 否则继续等待
            sess["last_status"] = LoginStatus.WAITING
            return LoginResult(
                status=LoginStatus.WAITING,
                message="等待扫码",
                cookies=None,
                user_info=None,
            )
        except Exception as e:
            logger.warning("轮询 %s 登录态失败: %s", self.platform, e)
            return LoginResult(
                status=LoginStatus.WAITING,
                message=f"轮询异常: {e}",
                cookies=None,
                user_info=None,
            )

    async def _extract_user_info(self, page) -> UserInfo:
        """从登录后的页面提取用户信息（尽力而为，失败返回空）。"""
        try:
            # 通用策略：尝试获取 document.title 或常见用户名元素
            title = await page.title()
            return UserInfo(
                user_id="",
                name=title or self.platform_name,
                username="",
                avatar="",
                extra={"url": page.url},
            )
        except Exception:
            return UserInfo(user_id="", name=self.platform_name, username="", avatar="", extra={})

    async def cleanup_session(self, session_id: str) -> None:
        sess = self._sessions.pop(session_id, None)
        if not sess:
            return
        browser = sess.get("browser")
        if browser is not None:
            await self._close_browser(browser)

    async def validate_cookie(self, storage_state: dict) -> dict:
        """校验 storage_state 是否仍有效：打开主页判断是否被重定向到登录页。"""
        if not storage_state:
            return {"valid": False, "reason": "storage_state 为空"}
        browser, context = await self._launch_browser(headless=True, storage_state=storage_state)
        try:
            page = await context.new_page()
            test_url = self.publish_url or self.login_url
            await page.goto(test_url, wait_until="domcontentloaded", timeout=20000)
            current = page.url
            # 如果被重定向回登录页，cookie 已失效
            if "login" in current.lower() or "passport" in current.lower():
                return {"valid": False, "reason": "Cookie 已失效，被重定向到登录页"}
            return {"valid": True, "reason": "Cookie 有效"}
        except Exception as e:
            return {"valid": False, "reason": f"校验异常: {e}"}
        finally:
            await self._close_browser(browser)

    async def publish_content(
        self,
        storage_state: dict,
        title: str,
        description: str,
        tags: list[str] | None = None,
        media_paths: list[str] | None = None,
        cover_path: str | None = None,
        publish_mode: str = "direct",  # direct|schedule
        scheduled_at: str | None = None,
        artifact_dir: str | None = None,
    ) -> dict:
        """真实发布流程：打开发布页 -> 填写标题/正文 -> 上传素材 -> 点击发布按钮 -> 等待发布成功。

        各平台 DOM 不同，使用 _PLATFORM_*_SELECTORS 中配置的选择器。
        发布成功判定：URL 跳转到管理页 / 成功页（_PLATFORM_SUCCESS_URL_PATTERNS）。
        artifact_dir 非空时，在关键步骤截图留痕并在返回值中带 artifacts 列表。
        """
        if not self.publish_url:
            return {
                "success": False,
                "status": "no_publish_url",
                "error": f"平台 {self.platform} 未配置发布页 URL",
                "artifacts": [],
            }

        artifacts: list[dict] = []
        browser, context = await self._launch_browser(headless=True, storage_state=storage_state)
        try:
            page = await context.new_page()
            await page.goto(self.publish_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 若被重定向回登录页，说明 cookie 已失效
            if "login" in page.url.lower() or "passport" in page.url.lower() or "signin" in page.url.lower():
                await self._capture(page, artifact_dir, "cookie_invalid", artifacts, kind="error_screenshot")
                return {
                    "success": False,
                    "status": "cookie_invalid",
                    "error": "打开发布页时被重定向到登录页，cookie 已失效，请重新扫码登录",
                    "page_url": page.url,
                    "artifacts": artifacts,
                }

            # 1. 上传文件（如果有）- 视频平台需先上传，标题/正文在上传后才出现
            if media_paths:
                await self._upload_files(page, media_paths)
                await self._wait_for_upload_complete(page)

            # 2. 填写标题
            await self._fill_title(page, title)

            # 3. 填写正文/描述
            if description:
                await self._fill_body(page, description)

            # 4. 填写标签/话题（如果提供）
            if tags:
                await self._fill_tags(page, tags)

            # 5. 设置封面（如果提供）
            if cover_path:
                await self._set_cover(page, cover_path)

            # 填表完成截图
            await self._capture(page, artifact_dir, "before_publish", artifacts)

            # 6. 点击发布按钮
            click_result = await self._click_publish_button(page)
            if not click_result["clicked"]:
                await self._capture(page, artifact_dir, "button_not_found", artifacts, kind="error_screenshot")
                return {
                    "success": False,
                    "status": "publish_button_not_found",
                    "error": click_result.get("error", "未找到发布按钮"),
                    "page_url": page.url,
                    "artifacts": artifacts,
                }

            # 7. 等待发布成功（URL 跳转）
            success = await self._wait_for_publish_success(page)
            await self._capture(
                page, artifact_dir,
                "after_publish" if success else "publish_unknown",
                artifacts,
                kind="screenshot" if success else "error_screenshot",
            )
            if success:
                return {
                    "success": True,
                    "status": "published",
                    "message": f"已成功发布到 {self.platform_name}",
                    "publish_url": page.url,
                    "page_url": page.url,
                    "artifacts": artifacts,
                }
            # 发布按钮点击了但没有跳转到成功页 - 可能是定时发布或需要二次确认
            return {
                "success": False,
                "status": "publish_unknown",
                "error": "已点击发布按钮，但未检测到成功跳转（可能是定时发布或需要二次确认）",
                "page_url": page.url,
                "artifacts": artifacts,
            }
        except Exception as e:
            logger.exception("发布到 %s 失败", self.platform)
            return {
                "success": False,
                "status": "publish_error",
                "error": str(e),
                "artifacts": artifacts,
            }
        finally:
            await self._close_browser(browser)

    async def _capture(
        self,
        page,
        artifact_dir: str | None,
        name: str,
        artifacts: list[dict],
        kind: str = "screenshot",
    ) -> None:
        """在关键步骤截图并记录到 artifacts 列表（artifact_dir 为空时跳过）。"""
        if not artifact_dir:
            return
        try:
            import os
            os.makedirs(artifact_dir, exist_ok=True)
            filename = f"{int(time.time() * 1000)}_{self.platform}_{name}.png"
            filepath = os.path.join(artifact_dir, filename)
            await page.screenshot(path=filepath, full_page=False)
            artifacts.append({
                "type": kind,
                "filename": filename,
                "path": filepath,
                "note": name,
            })
        except Exception as e:
            logger.warning("%s 截图 %s 失败: %s", self.platform, name, e)

    async def _upload_files(self, page, media_paths: list[str]) -> None:
        """上传媒体文件。"""
        selectors = _PLATFORM_FILE_INPUT_SELECTORS.get(self.platform, ['input[type="file"]'])
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.set_input_files(media_paths)
                    await asyncio.sleep(2)
                    return
            except Exception:
                continue
        # 回退：找所有 file input
        try:
            loc = page.locator('input[type="file"]').first
            if await loc.count() > 0:
                await loc.set_input_files(media_paths)
                await asyncio.sleep(2)
        except Exception as e:
            logger.warning("%s 上传文件失败: %s", self.platform, e)

    async def _wait_for_upload_complete(self, page, timeout: int = 120) -> None:
        """等待上传完成。通用策略：等待上传进度条消失或上传成功提示出现。"""
        try:
            # 等待上传进度条消失（多数平台用 .upload-progress 或 [class*="progress"]）
            progress_selectors = [
                '.upload-progress',
                '[class*="upload-progress"]',
                '[class*="progress-bar"]',
            ]
            for sel in progress_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        # 等待进度条消失（最多 timeout 秒）
                        await loc.wait_for(state="hidden", timeout=timeout * 1000)
                        break
                except Exception:
                    continue
            # 额外等待 2 秒确保上传后 DOM 稳定
            await asyncio.sleep(2)
        except Exception:
            # 超时不一定失败，可能是该平台没有进度条 UI
            await asyncio.sleep(3)

    async def _fill_title(self, page, title: str) -> None:
        """填写标题。"""
        if not title:
            return
        selectors = _PLATFORM_TITLE_SELECTORS.get(
            self.platform,
            ['input[placeholder*="标题"]', 'textarea[placeholder*="标题"]', '#title'],
        )
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.click()
                    await loc.fill(title)
                    return
            except Exception:
                continue
        logger.warning("%s 未找到标题输入框", self.platform)

    async def _fill_body(self, page, body: str) -> None:
        """填写正文/描述。"""
        selectors = _PLATFORM_BODY_SELECTORS.get(
            self.platform,
            ['[contenteditable="true"]', 'textarea[placeholder*="描述"]'],
        )
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.click()
                    await loc.fill(body)
                    return
            except Exception:
                continue
        logger.warning("%s 未找到正文输入框", self.platform)

    async def _fill_tags(self, page, tags: list[str]) -> None:
        """填写标签/话题。通用策略：在标题或正文后追加 #话题# """
        if not tags:
            return
        # 多数平台支持在正文里 #话题# 触发话题选择
        # 这里只做简单追加，真实生产可能需要更复杂的话题选择器交互
        tag_text = " ".join(f"#{t}#" if not t.startswith("#") else t for t in tags)
        try:
            body_selectors = _PLATFORM_BODY_SELECTORS.get(
                self.platform, ['[contenteditable="true"]']
            )
            for sel in body_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0:
                        await loc.press("End")
                        await loc.type(f" {tag_text}", delay=50)
                        return
                except Exception:
                    continue
        except Exception as e:
            logger.warning("%s 填写标签失败: %s", self.platform, e)

    async def _set_cover(self, page, cover_path: str) -> None:
        """设置封面图。"""
        cover_selectors = [
            'input[type="file"][accept*="image"]',
            '.cover-upload input[type="file"]',
            '[class*="cover"] input[type="file"]',
        ]
        for sel in cover_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.set_input_files(cover_path)
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue
        logger.warning("%s 未找到封面上传入口", self.platform)

    async def _click_publish_button(self, page) -> dict:
        """点击发布按钮。返回 {"clicked": bool, "error": str | None}。"""
        selectors = _PLATFORM_PUBLISH_BUTTON_SELECTORS.get(
            self.platform, ['button:has-text("发布")', 'button:has-text("发表")']
        )
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    # 等待按钮可点击
                    await loc.wait_for(state="visible", timeout=10000)
                    await loc.click()
                    logger.info("%s 已点击发布按钮: %s", self.platform, sel)
                    return {"clicked": True, "error": None}
            except Exception as e:
                logger.debug("%s 尝试选择器 %s 失败: %s", self.platform, sel, e)
                continue
        # 最后回退：找所有可见按钮中文字含"发布"或"发表"的
        try:
            buttons = page.get_by_role("button")
            count = await buttons.count()
            for i in range(count):
                btn = buttons.nth(i)
                text = (await btn.text_content() or "").strip()
                if text in ("发布", "发表", "立即投稿", "发布视频", "发布笔记"):
                    await btn.click()
                    logger.info("%s 已点击发布按钮（回退匹配）: %s", self.platform, text)
                    return {"clicked": True, "error": None}
        except Exception:
            pass
        return {"clicked": False, "error": f"未找到 {self.platform} 的发布按钮"}

    async def _wait_for_publish_success(self, page, timeout: int = 60) -> bool:
        """等待发布成功（URL 跳转到管理页/成功页）。

        Args:
            page: Playwright page
            timeout: 最大等待秒数

        Returns:
            True 表示检测到成功跳转；False 表示超时未跳转
        """
        patterns = _PLATFORM_SUCCESS_URL_PATTERNS.get(self.platform, [])
        if not patterns:
            # 没有配置成功 URL 模式，只等待 5 秒看是否有跳转
            try:
                await page.wait_for_url(lambda url: url != self.publish_url, timeout=10000)
                return True
            except Exception:
                return False

        compiled = [re.compile(p) for p in patterns]
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                current_url = page.url
                for pat in compiled:
                    if pat.search(current_url):
                        logger.info("%s 发布成功跳转到: %s", self.platform, current_url)
                        return True
                # 检查是否有成功提示弹窗
                try:
                    success_toast = page.locator('[class*="success"]:has-text("成功"), [class*="toast"]:has-text("成功")')
                    if await success_toast.count() > 0:
                        logger.info("%s 发布成功（检测到成功提示）", self.platform)
                        return True
                except Exception:
                    pass
            except Exception:
                pass
            await asyncio.sleep(1)
        return False


class ImageTextPlatformAdapter(BuiltinPlatformAdapter):
    """图文平台适配器（百家号图文 / 知乎文章）。

    与短视频平台不同：图文平台先填标题、正文，再把图片插入到正文富文本编辑器中，
    而不是把媒体作为顶层上传后才出现表单。选择器待真实账号联调验证。
    """

    async def publish_content(
        self,
        storage_state: dict,
        title: str,
        description: str,
        tags: list[str] | None = None,
        media_paths: list[str] | None = None,
        cover_path: str | None = None,
        publish_mode: str = "direct",
        scheduled_at: str | None = None,
        artifact_dir: str | None = None,
    ) -> dict:
        if not self.publish_url:
            return {
                "success": False,
                "status": "no_publish_url",
                "error": f"平台 {self.platform} 未配置发布页 URL",
                "artifacts": [],
            }

        artifacts: list[dict] = []
        browser, context = await self._launch_browser(headless=True, storage_state=storage_state)
        try:
            page = await context.new_page()
            await page.goto(self.publish_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            if "login" in page.url.lower() or "passport" in page.url.lower() or "signin" in page.url.lower():
                await self._capture(page, artifact_dir, "cookie_invalid", artifacts, kind="error_screenshot")
                return {
                    "success": False,
                    "status": "cookie_invalid",
                    "error": "打开发布页时被重定向到登录页，cookie 已失效，请重新扫码登录",
                    "page_url": page.url,
                    "artifacts": artifacts,
                }

            # 1. 标题
            await self._fill_title(page, title)
            # 2. 正文
            if description:
                await self._fill_body(page, description)
            # 3. 正文插图（图文平台核心）
            if media_paths:
                await self._insert_body_images(page, media_paths)
            # 4. 标签（追加到正文尾部）
            if tags:
                await self._fill_tags(page, tags)

            await self._capture(page, artifact_dir, "before_publish", artifacts)

            # 5. 点击发布（部分平台需二次确认）
            click_result = await self._click_publish_button(page)
            if not click_result["clicked"]:
                await self._capture(page, artifact_dir, "button_not_found", artifacts, kind="error_screenshot")
                return {
                    "success": False,
                    "status": "publish_button_not_found",
                    "error": click_result.get("error", "未找到发布按钮"),
                    "page_url": page.url,
                    "artifacts": artifacts,
                }
            await asyncio.sleep(1)
            await self._confirm_publish_dialog(page)

            success = await self._wait_for_publish_success(page)
            await self._capture(
                page, artifact_dir,
                "after_publish" if success else "publish_unknown",
                artifacts,
                kind="screenshot" if success else "error_screenshot",
            )
            if success:
                return {
                    "success": True,
                    "status": "published",
                    "message": f"已成功发布到 {self.platform_name}",
                    "publish_url": page.url,
                    "page_url": page.url,
                    "artifacts": artifacts,
                }
            return {
                "success": False,
                "status": "publish_unknown",
                "error": "已点击发布按钮，但未检测到成功跳转（可能需要二次确认或平台审核中）",
                "page_url": page.url,
                "artifacts": artifacts,
            }
        except Exception as e:
            logger.exception("图文发布到 %s 失败", self.platform)
            return {
                "success": False,
                "status": "publish_error",
                "error": str(e),
                "artifacts": artifacts,
            }
        finally:
            await self._close_browser(browser)

    async def _insert_body_images(self, page, media_paths: list[str]) -> None:
        """把图片插入正文富文本编辑器：优先点击图片工具按钮触发 file input，回退直接 set 隐藏 input。"""
        images = [p for p in media_paths if p]
        if not images:
            return
        btn_selectors = _PLATFORM_IMAGE_BUTTON_SELECTORS.get(self.platform, [])
        file_selectors = _PLATFORM_FILE_INPUT_SELECTORS.get(self.platform, ['input[type="file"][accept*="image"]', 'input[type="file"]'])
        # 先尝试点击图片工具按钮，弹出上传 input
        for sel in btn_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.click()
                    await asyncio.sleep(1)
                    break
            except Exception:
                continue
        # 设置文件到 image file input
        for sel in file_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.set_input_files(images)
                    await self._wait_for_upload_complete(page)
                    return
            except Exception:
                continue
        logger.warning("%s 未找到正文插图入口，跳过插图", self.platform)

    async def _confirm_publish_dialog(self, page) -> None:
        """处理发布二次确认弹窗（知乎/百家号点发布后可能弹确认框）。"""
        confirm_selectors = [
            '.Modal button:has-text("发布")',
            '.Modal button:has-text("确定")',
            'button:has-text("确认发布")',
        ]
        for sel in confirm_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.wait_for(state="visible", timeout=3000)
                    await loc.click()
                    logger.info("%s 已点击二次确认发布: %s", self.platform, sel)
                    return
            except Exception:
                continue


class VideoPlatformAdapter(BuiltinPlatformAdapter):
    """短视频平台适配器（视频号 / 抖音）。

    与图文平台不同：先上传视频文件，等待转码/处理完成（视频较大，耗时更长），
    编辑表单（标题、描述、封面）在上传完成后才渲染，随后填表并发布。
    继承基类发布流程（上传→填表→发布），仅强化「视频上传完成」的等待判定。
    """

    # 视频上传+转码等待上限（秒）：视频较大，给足处理时间
    _VIDEO_UPLOAD_TIMEOUT = 600

    async def _wait_for_upload_complete(self, page, timeout: int | None = None) -> None:
        """等待视频上传+转码完成。

        判定策略（尽力而为，任一命中即认为可继续）：
        1) 上传进度条 / loading 元素消失
        2) 标题输入框出现（编辑表单渲染 = 上传完成）
        3) 页面出现「上传成功 / 转码完成 / 重新上传」等提示
        """
        timeout = timeout or self._VIDEO_UPLOAD_TIMEOUT
        deadline = time.time() + timeout
        title_selectors = _PLATFORM_TITLE_SELECTORS.get(self.platform, [])
        progress_selectors = [
            '.upload-progress',
            '[class*="upload-progress"]',
            '[class*="progress-bar"]',
            '[class*="uploading"]',
        ]
        done_text_selectors = [
            'text=上传成功',
            'text=转码完成',
            'text=重新上传',
            '[class*="upload-success"]',
        ]
        # 先等表单/成功提示出现（说明上传已推进到可编辑阶段）
        while time.time() < deadline:
            try:
                for sel in title_selectors:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible():
                            await asyncio.sleep(2)
                            return
                    except Exception:
                        continue
                for sel in done_text_selectors:
                    try:
                        if await page.locator(sel).first.count() > 0:
                            await asyncio.sleep(2)
                            return
                    except Exception:
                        continue
                # 进度条已消失也视为完成
                any_progress = False
                for sel in progress_selectors:
                    try:
                        if await page.locator(sel).first.count() > 0:
                            any_progress = True
                            break
                    except Exception:
                        continue
                if not any_progress:
                    # 无进度条且无表单：可能还在初始化，短暂等待后继续轮询
                    await asyncio.sleep(2)
            except Exception:
                pass
            await asyncio.sleep(2)
        logger.warning("%s 视频上传等待超时（%ss），继续尝试后续步骤", self.platform, timeout)


# 平台 -> 适配器类映射（可扩展为不同子类）
_ADAPTER_REGISTRY: dict[str, type[BuiltinPlatformAdapter]] = {
    "xiaohongshu": BuiltinPlatformAdapter,
    "channels": VideoPlatformAdapter,
    "douyin": VideoPlatformAdapter,
    "kuaishou": VideoPlatformAdapter,
    "bilibili": VideoPlatformAdapter,
    "baijiahao": ImageTextPlatformAdapter,
    "zhihu": ImageTextPlatformAdapter,
}


def get_adapter(platform: str, config: dict | None = None) -> PlatformAdapter:
    """工厂方法：返回指定平台的内置适配器实例。"""
    cls = _ADAPTER_REGISTRY.get(platform, BuiltinPlatformAdapter)
    return cls(platform=platform, config=config)


__all__ = [
    "BuiltinPlatformAdapter",
    "ImageTextPlatformAdapter",
    "VideoPlatformAdapter",
    "get_adapter",
]

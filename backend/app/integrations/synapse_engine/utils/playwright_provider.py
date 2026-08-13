"""Playwright 运行时提供者。

复刻 Synapse utils/playwright_provider.py 的运行时切换能力：
- SYNAPSE_PLAYWRIGHT_RUNTIME=patchright 优先使用 patchright（反检测增强版）
- SYNAPSE_PLAYWRIGHT_RUNTIME=playwright 强制使用 playwright
- 未设置时按 patchright -> playwright 顺序回退

注意：本模块在 import 时不会立即加载 Playwright 运行时，
只有真正调用 async_playwright() 等函数时才触发加载。
这样应用启动时不需要 Playwright 也能正常 import 其它模块。

用法：
    from app.integrations.synapse_engine.utils.playwright_provider import async_playwright
    pw = await async_playwright().start()  # 返回 Playwright 实例
    # 或
    async with async_playwright() as pw:  # 上下文管理器
        browser = await pw.chromium.launch()
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PLAYWRIGHT_RUNTIME = os.getenv("SYNAPSE_PLAYWRIGHT_RUNTIME", "").strip().lower()

_runtime_module: Any = None
_load_error: Exception | None = None
_loaded = False


def _try_load(name: str):
    """尝试加载 playwright/patchright 的 async_api 子模块。"""
    global _load_error
    # 优先加载 async_api 子模块（async_playwright 函数所在）
    try:
        return importlib.import_module(f"{name}.async_api")
    except Exception as exc:
        _load_error = exc
        # 回退到顶层包
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "async_playwright"):
                return mod
            # 尝试访问 async_api 子模块
            if hasattr(mod, "async_api"):
                return mod.async_api
            _load_error = ImportError(f"{name} has no async_playwright")
            return None
        except Exception as exc2:
            _load_error = exc2
            return None


def _ensure_loaded() -> Any:
    """惰性加载 Playwright 运行时模块。"""
    global _runtime_module, _loaded
    if _loaded:
        return _runtime_module
    _loaded = True

    if PLAYWRIGHT_RUNTIME == "playwright":
        _runtime_module = _try_load("playwright")
    elif PLAYWRIGHT_RUNTIME == "patchright":
        _runtime_module = _try_load("patchright") or _try_load("playwright")
    else:
        _runtime_module = _try_load("patchright") or _try_load("playwright")

    if _runtime_module is None:
        raise ImportError(
            "未找到可用的 Playwright 运行时（patchright 或 playwright）。"
            f" 请先 pip install playwright 或 pip install patchright。"
            f" 最后一次错误：{_load_error}"
        )
    logger.info("Playwright 运行时加载成功: %s", _runtime_module.__name__)
    return _runtime_module


def async_playwright():
    """返回 async_playwright 上下文管理器实例。

    用法：
        pw = await async_playwright().start()
        # 或
        async with async_playwright() as pw:
            ...
    """
    mod = _ensure_loaded()
    fn = getattr(mod, "async_playwright", None)
    if fn is None:
        raise AttributeError(f"{mod.__name__} 没有 async_playwright 函数")
    return fn()  # 返回 AsyncPlaywrightContextManager 实例


def sync_playwright():
    """返回 sync_playwright 上下文管理器实例（可能不存在）。"""
    mod = _ensure_loaded()
    fn = getattr(mod, "sync_playwright", None)
    if fn is None:
        return None
    return fn()


def get_runtime_info() -> dict:
    """返回运行时信息（不触发加载）。"""
    return {
        "configured_runtime": PLAYWRIGHT_RUNTIME or "auto",
        "loaded": _loaded,
        "module_name": getattr(_runtime_module, "__name__", None),
        "load_error": str(_load_error) if _load_error else None,
    }


def runtime_available() -> bool:
    """运行时包是否已安装；用于 API/UI 前置能力判断。"""
    if PLAYWRIGHT_RUNTIME == "playwright":
        return importlib.util.find_spec("playwright") is not None
    if PLAYWRIGHT_RUNTIME == "patchright":
        return importlib.util.find_spec("patchright") is not None or importlib.util.find_spec("playwright") is not None
    return importlib.util.find_spec("patchright") is not None or importlib.util.find_spec("playwright") is not None


@lru_cache(maxsize=1)
def browser_executable_available() -> bool:
    """浏览器可执行文件是否真实可用；供生产就绪检查使用。"""
    configured_path = os.getenv("SYNAPSE_LOCAL_CHROME_PATH", "").strip()
    if configured_path:
        return Path(configured_path).is_file() and os.access(configured_path, os.X_OK)
    if not runtime_available():
        return False

    manager = None
    playwright = None
    try:
        runtime_names = ["patchright", "playwright"]
        if PLAYWRIGHT_RUNTIME in runtime_names:
            runtime_names.remove(PLAYWRIGHT_RUNTIME)
            runtime_names.insert(0, PLAYWRIGHT_RUNTIME)
        for name in runtime_names:
            try:
                sync_api = importlib.import_module(f"{name}.sync_api")
                manager = sync_api.sync_playwright()
                playwright = manager.start()
                return Path(playwright.chromium.executable_path).is_file()
            except Exception:
                if playwright is not None:
                    playwright.stop()
                manager = None
                playwright = None
                continue
        return False
    finally:
        if playwright is not None:
            playwright.stop()


# 类型符号占位（实际类型在 Playwright 加载后可用）
# 这里用 type: ignore 避免静态检查报错
Browser = None  # type: ignore[assignment]
BrowserContext = None  # type: ignore[assignment]
BrowserType = None  # type: ignore[assignment]
Page = None  # type: ignore[assignment]
Locator = None  # type: ignore[assignment]
Playwright = None  # type: ignore[assignment]
TimeoutError = Exception  # type: ignore[assignment]


def configure_windows_event_loop() -> None:
    """Windows 平台必须切换到 ProactorEventLoop，否则 Playwright subprocess 会失败。"""
    if sys.platform.startswith("win"):
        import asyncio
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass


__all__ = [
    "PLAYWRIGHT_RUNTIME",
    "async_playwright",
    "sync_playwright",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "Page",
    "Locator",
    "Playwright",
    "TimeoutError",
    "configure_windows_event_loop",
    "get_runtime_info",
    "runtime_available",
    "browser_executable_available",
]

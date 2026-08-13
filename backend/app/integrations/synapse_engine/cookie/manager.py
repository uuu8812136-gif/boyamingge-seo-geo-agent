"""Cookie 管理器。

简化版的 Synapse CookieManager，负责：
1. 把 Playwright storage_state（含 cookies 和 origins/localStorage）落盘为 JSON
2. 按 (platform, account_id) 加载已保存的 storage_state
3. 删除失效的 cookie 文件
4. 内存缓存避免反复读盘

文件命名规则：<SYNAPSE_COOKIE_DIR>/<platform>_<account_id>.json
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CookieManager:
    """单个进程内的 Cookie 存储管理器（线程安全由调用方保证，本类不做加锁）。"""

    def __init__(self, cookie_dir: str | os.PathLike[str] | None = None):
        if cookie_dir is None:
            from app.core.config import get_settings
            cookie_dir = get_settings().synapse_cookie_dir
        self.cookie_dir = Path(cookie_dir)
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        # 内存缓存：<key, (storage_state, mtime)>
        self._cache: dict[str, tuple[dict | None, float]] = {}

    def _key(self, platform: str, account_id: str) -> str:
        return f"{platform}_{account_id}"

    def _path(self, platform: str, account_id: str) -> Path:
        # account_id 可能含 /，做一次 hash 兜底
        safe_account = account_id.replace("/", "_").replace("\\", "_")
        return self.cookie_dir / f"{platform}_{safe_account}.json"

    def save(self, platform: str, account_id: str, storage_state: dict) -> Path:
        """保存 storage_state 到磁盘。"""
        path = self._path(platform, account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        self._cache[self._key(platform, account_id)] = (storage_state, time.time())
        logger.info("保存 %s 账号 %s 的 storage_state -> %s", platform, account_id, path)
        return path

    def load(self, platform: str, account_id: str) -> dict | None:
        """加载 storage_state；优先用内存缓存，磁盘文件不存在返回 None。"""
        key = self._key(platform, account_id)
        path = self._path(platform, account_id)
        if not path.exists():
            return None
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        cached = self._cache.get(key)
        if cached and cached[1] >= mtime:
            return cached[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._cache[key] = (state, mtime)
            return state
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("读取 %s 失败: %s", path, e)
            return None

    def delete(self, platform: str, account_id: str) -> bool:
        """删除 cookie 文件。"""
        path = self._path(platform, account_id)
        self._cache.pop(self._key(platform, account_id), None)
        if path.exists():
            try:
                path.unlink()
                logger.info("删除 %s 账号 %s 的 cookie 文件", platform, account_id)
                return True
            except OSError as e:
                logger.warning("删除 %s 失败: %s", path, e)
                return False
        return False

    def exists(self, platform: str, account_id: str) -> bool:
        return self._path(platform, account_id).exists()

    def list_accounts(self, platform: str | None = None) -> list[dict[str, str]]:
        """列出已保存的账号 cookie 文件。"""
        result: list[dict[str, str]] = []
        if not self.cookie_dir.exists():
            return result
        for f in self.cookie_dir.glob("*.json"):
            stem = f.stem  # platform_accountid
            if "_" not in stem:
                continue
            plat, _, acc = stem.partition("_")
            if platform and plat != platform:
                continue
            result.append({"platform": plat, "account_id": acc, "path": str(f)})
        return result


__all__ = ["CookieManager"]

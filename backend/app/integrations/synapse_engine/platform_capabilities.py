"""平台能力单一源（前后端共用）。

tier 含义：
- verified: 已用真实账号回归验证，可放心发布
- beta:     已接入网页自动化，但选择器未用真实账号联调验证，可用未实测
- planned:  未实现，仅保留数据结构与 UI 位置，禁用创建任务

can_publish=True 的平台允许创建发布任务；False 的平台在 API 层直接拒绝。
"""
from __future__ import annotations

PLATFORM_CAPABILITIES: list[dict] = [
    {
        "code": 1,
        "name": "xiaohongshu",
        "display": "小红书",
        "tier": "beta",
        "can_publish": True,
        "note": "自动化已实现；正式上线前需用贵司账号完成一次真实发布验收",
    },
    {
        "code": 10,
        "name": "baijiahao",
        "display": "百家号",
        "tier": "beta",
        "can_publish": True,
        "note": "可用未实测，选择器待真实账号验证",
    },
    {
        "code": 11,
        "name": "zhihu",
        "display": "知乎",
        "tier": "beta",
        "can_publish": True,
        "note": "可用未实测，选择器待真实账号验证",
    },
    {
        "code": 2,
        "name": "channels",
        "display": "视频号",
        "tier": "planned",
        "can_publish": False,
        "note": "待接入，视频发布未联调",
    },
    {
        "code": 3,
        "name": "douyin",
        "display": "抖音",
        "tier": "planned",
        "can_publish": False,
        "note": "待接入，视频发布未联调",
    },
    {
        "code": 4,
        "name": "kuaishou",
        "display": "快手",
        "tier": "planned",
        "can_publish": False,
        "note": "待接入，视频发布未联调",
    },
    {
        "code": 5,
        "name": "bilibili",
        "display": "B站",
        "tier": "planned",
        "can_publish": False,
        "note": "待接入，视频发布未联调",
    },
]

PLATFORM_BY_NAME: dict[str, dict] = {p["name"]: p for p in PLATFORM_CAPABILITIES}
PLATFORM_NAME_TO_CODE: dict[str, int] = {p["name"]: p["code"] for p in PLATFORM_CAPABILITIES}
PUBLISHABLE_PLATFORMS: set[str] = {p["name"] for p in PLATFORM_CAPABILITIES if p["can_publish"]}
ALL_PLATFORM_NAMES: set[str] = {p["name"] for p in PLATFORM_CAPABILITIES}

# 图文平台（用于 task_spec 构造）
IMAGE_TEXT_PLATFORMS: set[str] = {"xiaohongshu", "baijiahao", "zhihu"}
# 短视频平台（用于 task_spec 构造，目前均 can_publish=False）
VIDEO_PLATFORMS: set[str] = {"channels", "douyin", "kuaishou", "bilibili"}


def get_platform(name: str) -> dict | None:
    """按平台名获取能力 dict，不存在返回 None。"""
    return PLATFORM_BY_NAME.get((name or "").strip().lower())


def is_publishable(name: str) -> bool:
    """平台是否允许创建发布任务。"""
    p = get_platform(name)
    return bool(p and p["can_publish"])


__all__ = [
    "PLATFORM_CAPABILITIES",
    "PLATFORM_BY_NAME",
    "PLATFORM_NAME_TO_CODE",
    "PUBLISHABLE_PLATFORMS",
    "ALL_PLATFORM_NAMES",
    "IMAGE_TEXT_PLATFORMS",
    "VIDEO_PLATFORMS",
    "get_platform",
    "is_publishable",
]

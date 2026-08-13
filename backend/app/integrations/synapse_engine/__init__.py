"""Synapse 内嵌发布引擎。

把 SynapseAutomation 的核心能力（扫码登录、Cookie 管理、平台发布器）
作为本项目内部 Python 模块加载，所有调用均为进程内 import，不走 HTTP。

对外暴露 EmbeddedSynapseService 及平台相关常量。
"""

from app.integrations.synapse_engine.service import EmbeddedSynapseService
from app.integrations.synapse_engine.platforms.base import (
    LoginStatus,
    QRCodeData,
    PlatformAdapter,
)
from app.integrations.synapse_engine.platforms.codes import (
    PLATFORM_CODES,
    CODE_TO_PLATFORM,
    PLATFORM_NAMES,
)

__all__ = [
    "EmbeddedSynapseService",
    "PlatformAdapter",
    "LoginStatus",
    "QRCodeData",
    "PLATFORM_CODES",
    "CODE_TO_PLATFORM",
    "PLATFORM_NAMES",
]

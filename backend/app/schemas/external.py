"""外部平台账号与发布任务 Schema。"""
from datetime import datetime
from pydantic import BaseModel, Field


# ── 平台 ──

class PlatformInfo(BaseModel):
    code: int
    name: str  # 内部名
    display: str  # 中文名
    supported: bool  # 是否已真实接入（兼容旧字段，= can_publish）
    tier: str = "planned"  # verified | beta | planned
    can_publish: bool = False  # 是否允许创建发布任务
    note: str = ""


class PlatformListResponse(BaseModel):
    items: list[PlatformInfo]


# ── 外部账号 ──

class ExternalAccountCreate(BaseModel):
    platform: str = Field(pattern="^(xiaohongshu|baijiahao|zhihu|douyin|kuaishou|bilibili|channels)$")
    display_name: str = Field(min_length=1, max_length=128)
    city: str | None = None
    dealer_id: str | None = None
    note: str | None = None


class ExternalAccountItem(BaseModel):
    id: int
    platform: str
    platform_code: int
    display_name: str
    internal_account_id: str | None = None
    user_id: str | None = None
    avatar: str | None = None
    cookie_status: str
    cookie_path: str | None = None
    last_login_at: datetime | None = None
    status: str
    city: str | None = None
    note: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExternalAccountListResponse(BaseModel):
    total: int
    items: list[ExternalAccountItem]


class LoginStartResponse(BaseModel):
    session_id: str
    qr_url: str
    qr_image: str  # data:image/png;base64,...
    platform: str
    account_id: int | None = None  # 发起扫码的 SocialAccount.id


class LoginStatusResponse(BaseModel):
    session_id: str
    status: str  # waiting|scanned|confirmed|expired|failed
    account_id: int | None = None  # 登录成功后回写的 SocialAccount.id
    internal_account_id: str | None = None  # 内部 account_id（cookie 文件 key）
    message: str = ""
    user_info: dict | None = None  # 平台用户信息（user_id/nickname/avatar）


# ── 发布任务 ──

class PublishTaskCreate(BaseModel):
    content_id: int
    platform: str
    account_id: int
    title: str | None = None
    description: str | None = None
    topics: list[str] = Field(default_factory=list)
    cover_path: str | None = None
    publish_mode: str = Field(default="direct", pattern="^(direct|schedule)$")
    scheduled_at: str | None = None


class PublishTaskItem(BaseModel):
    id: int
    content_id: int
    platform: str
    social_account_id: int
    title: str
    status: str
    error_message: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublishTaskListResponse(BaseModel):
    total: int
    items: list[PublishTaskItem]


class PublishLogItem(BaseModel):
    id: int
    task_id: int
    level: str
    message: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublishLogListResponse(BaseModel):
    total: int
    items: list[PublishLogItem]


# ── 发布制品（截图/HTML 留痕）──

class PublishArtifactItem(BaseModel):
    id: int
    task_id: int
    artifact_type: str
    filename: str
    url: str | None = None
    note: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublishArtifactListResponse(BaseModel):
    total: int
    items: list[PublishArtifactItem]


# ── 内容社媒素材（视频/封面）──

class ContentMaterialItem(BaseModel):
    id: int
    content_id: int | None = None
    filename: str
    file_type: str  # video|image|cover
    url: str | None = None  # 可访问 URL（/uploads/...）
    cover_url: str | None = None
    size_mb: float | None = None
    duration_sec: float | None = None
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentMaterialListResponse(BaseModel):
    total: int
    items: list[ContentMaterialItem]

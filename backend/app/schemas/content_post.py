"""站内内容发布相关 Schema。"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContentPostCreate(BaseModel):
    """创建内容。"""
    title: str = Field(min_length=1, max_length=500)
    markdown: str = Field(min_length=1)
    post_type: str = Field(default="article", pattern="^(article|case|knowledge|seo_page)$")
    city: str = Field(min_length=1, max_length=64)
    store_id: int | None = None
    summary: str | None = None
    cover_image: str | None = None
    cover_image_alt: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    canonical: str | None = None
    keywords: list[str] = Field(default_factory=list)
    type: str = Field(default="seo", pattern="^(seo|geo|schema)$")


class ContentPostUpdate(BaseModel):
    """编辑内容（所有字段可选）。"""
    title: str | None = Field(default=None, min_length=1, max_length=500)
    markdown: str | None = Field(default=None, min_length=1)
    post_type: str | None = Field(default=None, pattern="^(article|case|knowledge|seo_page)$")
    city: str | None = Field(default=None, min_length=1, max_length=64)
    summary: str | None = None
    cover_image: str | None = None
    cover_image_alt: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    canonical: str | None = None
    keywords: list[str] | None = None
    store_id: int | None = None


class ContentPostItem(BaseModel):
    """内容列表项。"""
    id: int
    title: str | None = None
    slug: str | None = None
    post_type: str
    city: str
    store_id: int | None = None
    status: str
    summary: str | None = None
    cover_image: str | None = None
    seo_title: str | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentPostListResponse(BaseModel):
    total: int
    items: list[ContentPostItem]


class ContentPostDetail(ContentPostItem):
    markdown: str
    type: str
    eeat_score: int | None = None
    seo_description: str | None = None
    canonical: str | None = None
    keywords: list[str] = Field(default_factory=list)
    cover_image_alt: str | None = None
    model_used: str | None = None
    author_id: int | None = None


class PublishActionRequest(BaseModel):
    """发布/定时发布请求。"""
    publish_mode: str = Field(default="direct", pattern="^(direct|schedule)$")
    scheduled_at: str | None = None  # ISO 格式，publish_mode=schedule 时必填


class PublicationRecord(BaseModel):
    """发布记录。"""
    id: int
    content_id: int
    platform: str
    tier: str
    url: str | None = None
    status: str
    publish_mode: str
    published_at: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublicationListResponse(BaseModel):
    total: int
    items: list[PublicationRecord]


class ExternalPublishTarget(BaseModel):
    """外部分发目标。"""
    platform: str
    platform_name: str
    account_id: int | None = None
    account_display: str | None = None
    status: str = "pending"  # pending|queued|running|success|failed
    publish_url: str | None = None
    error_message: str | None = None
    task_id: int | None = None


class ExternalPublishRequest(BaseModel):
    """外部分发请求。"""
    content_id: int
    targets: list[ExternalPublishTarget]
    publish_mode: str = Field(default="direct", pattern="^(direct|schedule)$")
    scheduled_at: str | None = None


class ExternalPublishResponse(BaseModel):
    batch_id: int | None = None
    tasks: list[dict]  # 每个目标的派发结果
    total: int
    queued: int

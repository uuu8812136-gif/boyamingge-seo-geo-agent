"""总部后台城市/门店/case/faq/user 管理 schema。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.city import (
    CityCaseItem,
    CityDetailResponse,
    CityItem,
    CityFaqItem,
    StoreItem,
)


# ── City 管理 ──

class AdminCityItem(CityItem):
    """后台城市列表项（含门店数）。"""
    stores_count: int = 0


class AdminCityListResponse(BaseModel):
    total: int
    items: list[AdminCityItem]


class AdminCityDetail(CityDetailResponse):
    """后台城市详情（复用 CityDetailResponse，含 stores/cases/faqs/primary_store）。"""
    pass


class AdminCityCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64, pattern="^[a-z0-9-]+$")
    province: str = Field(min_length=1, max_length=32)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool = True
    has_store: bool = False
    seo_title: str | None = None
    seo_description: str | None = None
    hero_title: str | None = None
    hero_subtitle: str | None = None
    subdomain: str | None = Field(default=None, max_length=64, pattern="^[a-z0-9-]+$")
    custom_domain: str | None = None
    canonical_url: str | None = None
    seo_keywords: list[str] = Field(default_factory=list)
    seo_indexable: bool = True
    robots_policy: Literal["index_follow", "noindex", "noindex_follow", "noindex_nofollow"] = "index_follow"
    hero_image: str | None = None
    service_area_json: list[str] = Field(default_factory=list)
    service_tags: list[str] = Field(default_factory=list)
    content_status: Literal["draft", "ready", "published", "archived"] = "draft"


class AdminCityUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    province: str | None = Field(default=None, min_length=1, max_length=32)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None
    has_store: bool | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    hero_title: str | None = None
    hero_subtitle: str | None = None
    subdomain: str | None = Field(default=None, max_length=64)
    custom_domain: str | None = None
    canonical_url: str | None = None
    seo_keywords: list[str] | None = None
    seo_indexable: bool | None = None
    robots_policy: Literal["index_follow", "noindex", "noindex_follow", "noindex_nofollow"] | None = None
    hero_image: str | None = None
    service_area_json: list[str] | None = None
    service_tags: list[str] | None = None
    content_status: Literal["draft", "ready", "published", "archived"] | None = None


# ── Store 管理 ──

class AdminStoreItem(StoreItem):
    pass


class AdminStoreListResponse(BaseModel):
    total: int
    items: list[AdminStoreItem]


class AdminStoreCreateRequest(BaseModel):
    city_id: int
    store_name: str = Field(min_length=1, max_length=128)
    province: str = Field(min_length=1, max_length=32)
    city: str = Field(min_length=1, max_length=64)
    district: str = Field(min_length=1, max_length=64)
    address: str = Field(min_length=1, max_length=256)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    phone: str = Field(min_length=1, max_length=32)
    opening_hours: str | None = None
    services: list[str] = Field(default_factory=list)
    cover_image: str | None = None
    is_active: bool = True
    sort_order: int = 0
    store_code: str | None = None
    manager_user_id: int | None = None
    dealer_code: str | None = None
    is_primary: bool = False
    booking_url: str | None = None
    wechat_qr: str | None = None
    gallery: list[str] = Field(default_factory=list)
    service_radius: str | None = None
    status: Literal["active", "hidden", "closed"] = "active"


class AdminStoreUpdateRequest(BaseModel):
    store_name: str | None = Field(default=None, min_length=1, max_length=128)
    province: str | None = Field(default=None, min_length=1, max_length=32)
    city: str | None = Field(default=None, min_length=1, max_length=64)
    district: str | None = Field(default=None, min_length=1, max_length=64)
    address: str | None = Field(default=None, min_length=1, max_length=256)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    opening_hours: str | None = None
    services: list[str] | None = None
    cover_image: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    store_code: str | None = None
    manager_user_id: int | None = None
    dealer_code: str | None = None
    booking_url: str | None = None
    wechat_qr: str | None = None
    gallery: list[str] | None = None
    service_radius: str | None = None
    status: Literal["active", "hidden", "closed"] | None = None


# ── CityCase 管理 ──

class AdminCaseItem(CityCaseItem):
    pass


class AdminCaseListResponse(BaseModel):
    total: int
    items: list[AdminCaseItem]


class AdminCaseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    service_type: str | None = None
    content: str = Field(min_length=1)
    images: list[str] = Field(default_factory=list)


class AdminCaseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    service_type: str | None = None
    content: str | None = Field(default=None, min_length=1)
    images: list[str] | None = None


# ── CityFaq 管理 ──

class AdminFaqItem(CityFaqItem):
    pass


class AdminFaqListResponse(BaseModel):
    total: int
    items: list[AdminFaqItem]


class AdminFaqCreateRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1)


class AdminFaqUpdateRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=500)
    answer: str | None = Field(default=None, min_length=1)


# ── User 管理 ──

class AdminUserItem(BaseModel):
    id: int
    username: str
    role: str
    dealer_code: str | None = None
    city_id: int | None = None
    store_id: int | None = None
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserItem]


class AdminUserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "operator", "city_manager", "store_manager", "dealer"]
    dealer_code: str | None = None
    city_id: int | None = None
    store_id: int | None = None
    is_active: bool = True


class AdminUserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=12, max_length=128)
    role: Literal["admin", "operator", "city_manager", "store_manager", "dealer"] | None = None
    dealer_code: str | None = None
    city_id: int | None = None
    store_id: int | None = None
    is_active: bool | None = None


class AdminAuditLogItem(BaseModel):
    id: int
    username: str | None = None
    method: str
    path: str
    status_code: int
    client_ip: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminAuditLogListResponse(BaseModel):
    total: int
    items: list[AdminAuditLogItem]

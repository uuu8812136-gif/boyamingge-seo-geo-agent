from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── City ──────────────────────────────────────────────────────

class CityItem(BaseModel):
    id: int
    name: str
    slug: str
    province: str
    lat: float | None = None
    lng: float | None = None
    is_active: bool = True
    has_store: bool = False
    seo_title: str | None = None
    seo_description: str | None = None
    hero_title: str | None = None
    hero_subtitle: str | None = None
    # ── 二级域名 / SEO 扩展 ──
    subdomain: str | None = None
    custom_domain: str | None = None
    canonical_url: str | None = None
    seo_keywords: list[str] = Field(default_factory=list)
    seo_indexable: bool = True
    robots_policy: str = "index_follow"
    hero_image: str | None = None
    service_area_json: list[Any] = Field(default_factory=list)
    service_tags: list[str] = Field(default_factory=list)
    content_status: str = "draft"
    published_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CityListResponse(BaseModel):
    total: int
    items: list[CityItem]


class CityDetailResponse(CityItem):
    stores: list["StoreItem"] = Field(default_factory=list)
    primary_store: "StoreItem | None" = None
    cases: list["CityCaseItem"] = Field(default_factory=list)
    faqs: list["CityFaqItem"] = Field(default_factory=list)


# ── Store ─────────────────────────────────────────────────────

class StoreItem(BaseModel):
    id: int
    city_id: int
    store_name: str
    province: str
    city: str
    district: str
    address: str
    lat: float | None = None
    lng: float | None = None
    phone: str
    opening_hours: str | None = None
    services: list[str] = Field(default_factory=list)
    cover_image: str | None = None
    is_active: bool = True
    sort_order: int = 0
    # ── 门店扩展 ──
    store_code: str | None = None
    manager_user_id: int | None = None
    dealer_code: str | None = None
    is_primary: bool = False
    booking_url: str | None = None
    wechat_qr: str | None = None
    gallery: list[str] = Field(default_factory=list)
    service_radius: str | None = None
    status: str = "active"

    model_config = {"from_attributes": True}


class StoreListResponse(BaseModel):
    total: int
    items: list[StoreItem]


# ── CityCase ──────────────────────────────────────────────────

class CityCaseItem(BaseModel):
    id: int
    city_id: int
    title: str
    service_type: str | None = None
    content: str
    images: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CityCaseListResponse(BaseModel):
    total: int
    items: list[CityCaseItem]


# ── CityFaq ──────────────────────────────────────────────────

class CityFaqItem(BaseModel):
    id: int
    city_id: int
    question: str
    answer: str

    model_config = {"from_attributes": True}


class CityFaqListResponse(BaseModel):
    total: int
    items: list[CityFaqItem]


# ── Enhanced Lead Submission ──────────────────────────────────

class LeadSubmitRequestV2(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=11, max_length=32)
    city_id: int | None = None
    city_name: str | None = None
    preferred_store_id: int | None = None
    interest: str = Field(default="门窗咨询")
    source: str = Field(default="website")
    source_path: str | None = None
    utm: str | None = None
    # ── 二级域名归因 ──
    host: str | None = None
    landing_url: str | None = None
    utm_json: dict[str, Any] | None = None


class LeadSubmitResponseV2(BaseModel):
    lead_id: int
    status: str
    message: str
    assigned_store: str | None = None
    assigned_city: str | None = None


# ── City Locate ──────────────────────────────────────────────

class CityLocateRequest(BaseModel):
    city_name: str | None = None


class CityLocateResponse(BaseModel):
    city: CityItem | None = None
    redirect_slug: str | None = None
    message: str | None = None

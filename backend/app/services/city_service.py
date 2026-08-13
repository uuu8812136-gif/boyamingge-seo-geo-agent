"""City, Store, CityCase, CityFaq service layer."""
import math
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import cache_get, cache_set
from app.models import City, CityCase, CityFaq, Store
from app.schemas.city import (
    CityDetailResponse,
    CityItem,
    CityLocateRequest,
    CityLocateResponse,
    CityCaseItem,
    CityFaqItem,
    StoreItem,
    LeadSubmitRequestV2,
    LeadSubmitResponseV2,
)
from app.models import Lead

# 城市详情缓存 5 分钟（门店/案例/FAQ 很少变化）
_CITY_CACHE_TTL = 300


def list_cities(db: Session, active_only: bool = True) -> list[CityItem]:
    """公开城市列表。

    active_only=True（公开接口默认）：只返回 is_active=True 且 content_status='published' 的城市，
    草稿城市不出现在公开列表中。
    active_only=False（后台管理用）：返回所有城市，不过滤 content_status。
    """
    query = db.query(City)
    if active_only:
        query = query.filter(City.is_active == True, City.content_status == "published")
    rows = query.order_by(City.id.asc()).all()
    return [CityItem.model_validate(row) for row in rows]


def get_city_by_slug(db: Session, slug: str) -> CityDetailResponse | None:
    """公开城市详情：只返回 is_active=True 且 content_status='published' 的城市。

    草稿（draft）城市返回 None，由路由层转为 404。
    后台查看草稿城市请用 admin_city_service.get_admin_city。
    """
    cache_key = f"city:detail:{slug}"
    cached = cache_get(cache_key)
    if cached:
        return CityDetailResponse(**cached)
    city = (
        db.query(City)
        .filter(City.slug == slug, City.is_active == True, City.content_status == "published")
        .first()
    )
    if not city:
        return None
    result = _build_city_detail(db, city)
    cache_set(cache_key, result.model_dump(mode="json"), ttl=_CITY_CACHE_TTL)
    return result


def get_city_by_name(db: Session, name: str) -> CityDetailResponse | None:
    city = (
        db.query(City)
        .filter(
            City.name == name,
            City.is_active == True,
            City.content_status == "published",
        )
        .first()
    )
    if not city:
        return None
    return _build_city_detail(db, city)


def _build_city_detail(db: Session, city: City) -> CityDetailResponse:
    stores = (
        db.query(Store)
        .filter(
            Store.city_id == city.id,
            Store.is_active == True,
            Store.status == "active",
        )
        .order_by(Store.sort_order.asc())
        .all()
    )
    cases = db.query(CityCase).filter(CityCase.city_id == city.id).order_by(CityCase.id.desc()).all()
    faqs = db.query(CityFaq).filter(CityFaq.city_id == city.id).order_by(CityFaq.id.asc()).all()
    primary = next((s for s in stores if getattr(s, "is_primary", False)), None)
    if primary is None and stores:
        primary = stores[0]
    detail = CityDetailResponse.model_validate(city)
    # canonical_url 自动生成：优先用 subdomain，其次 slug
    if not detail.canonical_url:
        sub = detail.subdomain or detail.slug
        if sub:
            root = get_settings().root_domain
            detail.canonical_url = f"https://{sub}.{root}/"
    detail.stores = [StoreItem.model_validate(s) for s in stores]
    detail.primary_store = StoreItem.model_validate(primary) if primary else None
    detail.cases = [CityCaseItem.model_validate(c) for c in cases]
    detail.faqs = [CityFaqItem.model_validate(f) for f in faqs]
    return detail

def list_stores(db: Session, city_slug: str | None = None) -> list[StoreItem]:
    query = (
        db.query(Store)
        .join(City, Store.city_id == City.id)
        .filter(
            Store.is_active == True,
            Store.status == "active",
            City.is_active == True,
            City.content_status == "published",
        )
    )
    if city_slug:
        city = db.query(City).filter(City.slug == city_slug).first()
        if city:
            query = query.filter(Store.city_id == city.id)
    rows = query.order_by(Store.sort_order.asc()).all()
    return [StoreItem.model_validate(row) for row in rows]


def locate_city(db: Session, city_name: str | None = None) -> CityLocateResponse:
    """Locate city by name for development-stage city detection."""
    if not city_name:
        city = (
            db.query(City)
            .filter(
                City.slug == "guangzhou",
                City.is_active == True,
                City.content_status == "published",
            )
            .first()
        )
        if city:
            return CityLocateResponse(
                city=CityItem.model_validate(city),
                redirect_slug=city.slug if city.has_store else None,
                message="未指定城市，默认推荐广州",
            )
        return CityLocateResponse(message="未找到默认城市")

    city = (
        db.query(City)
        .filter(
            City.name == city_name,
            City.is_active == True,
            City.content_status == "published",
        )
        .first()
    )
    if not city:
        return CityLocateResponse(message=f"城市「{city_name}」不在服务范围")

    if city.has_store:
        return CityLocateResponse(
            city=CityItem.model_validate(city),
            redirect_slug=city.slug,
            message=f"已定位到{city.name}",
        )

    # City without store - find nearest city with store
    nearest = _find_nearest_store_city(db, city)
    if nearest:
        return CityLocateResponse(
            city=CityItem.model_validate(city),
            redirect_slug=nearest.slug,
            message=f"{city.name}暂无门店，推荐最近服务城市{nearest.name}",
        )

    return CityLocateResponse(message=f"{city.name}暂无门店，请拨打400热线咨询")


def _find_nearest_store_city(db: Session, city: City) -> City | None:
    """Find nearest city that has a store.

    Uses Euclidean distance on lat/lng (sufficient for dev-stage city-level
    proximity; not true Haversine — good enough for ranking which city is
    closest among a handful of Chinese metro areas).
    """
    store_cities = (
        db.query(City)
        .join(Store, Store.city_id == City.id)
        .filter(
            City.is_active == True,
            City.content_status == "published",
            Store.is_active == True,
            Store.status == "active",
        )
        .distinct()
        .all()
    )
    if not store_cities:
        return None
    if not city.lat or not city.lng:
        return store_cities[0]

    def distance(c: City) -> float:
        if not c.lat or not c.lng:
            return float("inf")
        return math.sqrt((c.lat - city.lat) ** 2 + (c.lng - city.lng) ** 2)

    return min(store_cities, key=distance)


def submit_lead_v2(db: Session, payload: LeadSubmitRequestV2) -> LeadSubmitResponseV2:
    """Enhanced lead submission with store assignment logic."""
    from datetime import datetime, timezone

    # Determine city
    city = None
    if payload.city_id:
        city = db.query(City).filter(City.id == payload.city_id).first()
    elif payload.city_name:
        city = db.query(City).filter(City.name == payload.city_name).first()

    # Determine store assignment
    assigned_store = None
    public_store_query = (
        db.query(Store)
        .join(City, Store.city_id == City.id)
        .filter(
            Store.is_active == True,
            Store.status == "active",
            City.is_active == True,
            City.content_status == "published",
        )
    )
    if payload.preferred_store_id:
        assigned_store = public_store_query.filter(Store.id == payload.preferred_store_id).first()
        if not assigned_store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preferred_store_id 不存在、未启用或所属城市尚未发布",
            )
        if city and assigned_store.city_id != city.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preferred_store_id 不属于该城市，拒绝跨城市分配",
            )

    if not assigned_store and city and city.is_active and city.content_status == "published":
        # Default store: primary store first, else first active store by sort_order
        assigned_store = (
            public_store_query
            .filter(Store.city_id == city.id, Store.is_active == True, Store.is_primary == True)
            .order_by(Store.sort_order.asc())
            .first()
        )
        if not assigned_store:
            assigned_store = (
                public_store_query
                .filter(Store.city_id == city.id, Store.is_active == True)
                .order_by(Store.sort_order.asc())
                .first()
            )

    if not assigned_store:
        # No store in city - find nearest city with store
        if city and not city.has_store:
            nearest_city = _find_nearest_store_city(db, city)
            if nearest_city:
                assigned_store = (
                    public_store_query
                    .filter(Store.city_id == nearest_city.id, Store.is_active == True)
                    .order_by(Store.sort_order.asc())
                    .first()
                )
        if not assigned_store:
            # Fallback: first active store overall (headquarters)
            assigned_store = public_store_query.order_by(Store.sort_order.asc()).first()

    # Create lead（含二级域名归因字段）
    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        city=city.name if city else (payload.city_name or "未知"),
        interest=payload.interest,
        source=payload.source,
        utm=payload.utm or payload.source_path,
        status="new",
        city_id=city.id if city else None,
        store_id=assigned_store.id if assigned_store else None,
        dealer_id=assigned_store.dealer_code if assigned_store else None,
        host=payload.host,
        source_path=payload.source_path,
        landing_url=payload.landing_url,
        utm_json=payload.utm_json,
        assigned_at=datetime.now(timezone.utc) if assigned_store else None,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Build response
    assigned_store_name = assigned_store.store_name if assigned_store else None
    assigned_city_name = assigned_store.city if assigned_store else None
    message = "留资已提交，客服将尽快与您联系"
    if assigned_store:
        message = f"已为你分配{assigned_store.city}{assigned_store.district}门店"

    return LeadSubmitResponseV2(
        lead_id=lead.id,
        status="received",
        message=message,
        assigned_store=assigned_store_name,
        assigned_city=assigned_city_name,
    )

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.city import (
    CityDetailResponse,
    CityItem,
    CityListResponse,
    CityLocateRequest,
    CityLocateResponse,
    LeadSubmitRequestV2,
    LeadSubmitResponseV2,
    StoreItem,
    StoreListResponse,
)
from app.services.city_service import (
    get_city_by_name,
    get_city_by_slug,
    list_cities,
    list_stores,
    locate_city,
    submit_lead_v2,
)

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=CityListResponse)
def cities_list(
    db: Annotated[Session, Depends(get_db)],
):
    # 公开接口永远只返回 is_active=true 且 content_status=published 的城市。
    # 后台需要所有城市请使用 /api/v1/admin/cities。
    items = list_cities(db, active_only=True)
    return CityListResponse(total=len(items), items=items)


@router.get("/locate", response_model=CityLocateResponse)
def city_locate(
    db: Annotated[Session, Depends(get_db)],
    city_name: str | None = Query(default=None),
):
    return locate_city(db, city_name=city_name)


@router.get("/{slug}", response_model=CityDetailResponse)
def city_detail(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
):
    result = get_city_by_slug(db, slug)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    return result


@router.get("/stores/all", response_model=StoreListResponse)
def stores_list(
    db: Annotated[Session, Depends(get_db)],
    city: str | None = Query(default=None),
):
    items = list_stores(db, city_slug=city)
    return StoreListResponse(total=len(items), items=items)


@router.post("/leads", response_model=LeadSubmitResponseV2)
def leads_submit_v2(
    payload: LeadSubmitRequestV2,
    db: Annotated[Session, Depends(get_db)],
):
    return submit_lead_v2(db, payload)

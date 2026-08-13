"""总部后台城市/门店/case/faq/user 管理 service。"""
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import cache_delete
from app.core.security import (
    ROLE_ADMIN,
    ROLE_CITY_MANAGER,
    ROLE_DEALER,
    ROLE_OPERATOR,
    ROLE_STORE_MANAGER,
    get_password_hash,
    password_strength_error,
)
import re

from app.models import City, CityCase, CityFaq, Content, Dealer, Lead, Store
from app.models.user import User
from app.schemas.admin_city import (
    AdminCaseCreateRequest,
    AdminCaseItem,
    AdminCaseUpdateRequest,
    AdminCityCreateRequest,
    AdminCityDetail,
    AdminCityItem,
    AdminCityUpdateRequest,
    AdminFaqCreateRequest,
    AdminFaqItem,
    AdminFaqUpdateRequest,
    AdminStoreCreateRequest,
    AdminStoreItem,
    AdminStoreUpdateRequest,
    AdminUserCreateRequest,
    AdminUserItem,
    AdminUserUpdateRequest,
)


# 与 frontend/lib/domain.ts 的 RESERVED_SUBDOMAINS 保持一致
RESERVED_SUBDOMAINS = frozenset({
    "www", "admin", "api", "static", "assets", "cdn", "m", "mail", "ftp", "localhost",
})
_SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9-]+$")
_VALID_ROLES = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER, ROLE_DEALER}


def _invalidate_city_detail_cache(db: Session, city_id: int) -> None:
    slug = db.query(City.slug).filter(City.id == city_id).scalar()
    if slug:
        cache_delete(f"city:detail:{slug}")


def _sync_city_has_store(db: Session, city_id: int) -> None:
    has_store = (
        db.query(Store)
        .filter(
            Store.city_id == city_id,
            Store.is_active == True,
            Store.status == "active",
        )
        .count()
        > 0
    )
    db.query(City).filter(City.id == city_id).update({City.has_store: has_store})
    db.commit()


def _validate_subdomain(subdomain: str | None) -> None:
    """校验 subdomain：格式 + 保留字。create/update 均调用。"""
    if not subdomain:
        return
    if not _SUBDOMAIN_PATTERN.match(subdomain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subdomain 格式错误，只允许小写字母、数字和连字符",
        )
    if subdomain in RESERVED_SUBDOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"subdomain '{subdomain}' 是保留子域名，禁止使用",
        )


# ── City ──

def list_admin_cities(db: Session, city_ids: list[int] | None = None) -> list[AdminCityItem]:
    query = db.query(City)
    if city_ids is not None:
        query = query.filter(City.id.in_(city_ids))
    rows = query.order_by(City.id.asc()).all()
    result = []
    for c in rows:
        item = AdminCityItem.model_validate(c)
        item.stores_count = db.query(Store).filter(Store.city_id == c.id, Store.is_active == True).count()
        result.append(item)
    return result


def get_admin_city(db: Session, city_id: int) -> AdminCityDetail:
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    stores = db.query(Store).filter(Store.city_id == city.id).order_by(Store.sort_order.asc()).all()
    cases = db.query(CityCase).filter(CityCase.city_id == city.id).order_by(CityCase.id.desc()).all()
    faqs = db.query(CityFaq).filter(CityFaq.city_id == city.id).order_by(CityFaq.id.asc()).all()
    primary = next((s for s in stores if getattr(s, "is_primary", False)), None)
    if primary is None and stores:
        primary = stores[0]
    detail = AdminCityDetail.model_validate(city)
    if not detail.canonical_url:
        sub = detail.subdomain or detail.slug
        if sub:
            root = get_settings().root_domain
            detail.canonical_url = f"https://{sub}.{root}/"
    detail.stores = [AdminStoreItem.model_validate(s) for s in stores]
    detail.primary_store = AdminStoreItem.model_validate(primary) if primary else None
    detail.cases = [AdminCaseItem.model_validate(c) for c in cases]
    detail.faqs = [AdminFaqItem.model_validate(f) for f in faqs]
    return detail


def create_admin_city(db: Session, payload: AdminCityCreateRequest) -> AdminCityDetail:
    # subdomain 格式 + 保留字校验
    _validate_subdomain(payload.subdomain)
    # 唯一性校验
    if db.query(City).filter(City.slug == payload.slug).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slug 已存在")
    if db.query(City).filter(City.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="城市名已存在")
    if payload.subdomain and db.query(City).filter(City.subdomain == payload.subdomain).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdomain 已存在")
    if payload.custom_domain and db.query(City).filter(City.custom_domain == payload.custom_domain).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="custom_domain 已存在")
    data = payload.model_dump()
    data["has_store"] = False
    city = City(**data)
    db.add(city)
    db.commit()
    db.refresh(city)
    _invalidate_city_detail_cache(db, city.id)
    return get_admin_city(db, city.id)


def update_admin_city(db: Session, city_id: int, payload: AdminCityUpdateRequest) -> AdminCityDetail:
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    data = payload.model_dump(exclude_unset=True)
    data.pop("has_store", None)
    required_fields = {"name", "province", "is_active", "seo_indexable", "robots_policy", "content_status"}
    if any(data.get(field) is None for field in required_fields if field in data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="城市必填字段不能设为空")
    # subdomain 格式 + 保留字校验（若提交了 subdomain 字段）
    if "subdomain" in data:
        _validate_subdomain(data["subdomain"])
    # 唯一性校验
    if "subdomain" in data and data["subdomain"]:
        exists = db.query(City).filter(City.subdomain == data["subdomain"], City.id != city_id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subdomain 已存在")
    if "name" in data and data["name"]:
        exists = db.query(City).filter(City.name == data["name"], City.id != city_id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="城市名已存在")
    if "custom_domain" in data and data["custom_domain"]:
        exists = db.query(City).filter(City.custom_domain == data["custom_domain"], City.id != city_id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="custom_domain 已存在")
    old_name = city.name
    old_province = city.province
    for k, v in data.items():
        setattr(city, k, v)
    if city.name != old_name:
        db.query(Store).filter(Store.city_id == city.id).update({Store.city: city.name}, synchronize_session=False)
        db.query(Content).filter(Content.city == old_name).update({Content.city: city.name}, synchronize_session=False)
        db.query(Lead).filter(Lead.city_id == city.id).update({Lead.city: city.name}, synchronize_session=False)
        db.query(Dealer).filter(Dealer.city == old_name).update({Dealer.city: city.name}, synchronize_session=False)
    if city.province != old_province:
        db.query(Store).filter(Store.city_id == city.id).update({Store.province: city.province}, synchronize_session=False)
    db.commit()
    db.refresh(city)
    _invalidate_city_detail_cache(db, city.id)
    return get_admin_city(db, city.id)


def publish_admin_city(db: Session, city_id: int) -> AdminCityDetail:
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    city.content_status = "published"
    city.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(city)
    _invalidate_city_detail_cache(db, city.id)
    return get_admin_city(db, city.id)


def unpublish_admin_city(db: Session, city_id: int) -> AdminCityDetail:
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    city.content_status = "draft"
    db.commit()
    db.refresh(city)
    _invalidate_city_detail_cache(db, city.id)
    return get_admin_city(db, city.id)


# ── Store ──

def list_admin_stores(
    db: Session,
    city_id: int | None = None,
    city_ids: list[int] | None = None,
    store_ids: list[int] | None = None,
) -> list[AdminStoreItem]:
    """门店列表。

    - city_id: 按单个城市过滤
    - city_ids: 按城市列表过滤（city_manager 限制范围）
    - store_ids: 按门店列表过滤（store_manager 只能看自己门店）；None 表示不限
    """
    query = db.query(Store)
    if city_id:
        query = query.filter(Store.city_id == city_id)
    if city_ids is not None:
        query = query.filter(Store.city_id.in_(city_ids))
    if store_ids is not None:
        query = query.filter(Store.id.in_(store_ids))
    rows = query.order_by(Store.city_id.asc(), Store.sort_order.asc()).all()
    return [AdminStoreItem.model_validate(r) for r in rows]


def create_admin_store(db: Session, payload: AdminStoreCreateRequest) -> AdminStoreItem:
    city = db.query(City).filter(City.id == payload.city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    if payload.store_code:
        if db.query(Store).filter(Store.store_code == payload.store_code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="store_code 已存在")
    if payload.is_primary and (not payload.is_active or payload.status != "active"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="停用或关闭门店不能设为主门店")
    _validate_store_references(db, payload.manager_user_id, payload.dealer_code)
    data = payload.model_dump()
    data["city"] = city.name
    data["province"] = city.province
    store = Store(**data)
    db.add(store)
    db.commit()
    db.refresh(store)
    # 若 is_primary=True，清除同城市其它主门店
    if payload.is_primary:
        _reset_other_primary(db, store.city_id, store.id)
    _sync_city_has_store(db, store.city_id)
    _invalidate_city_detail_cache(db, store.city_id)
    return AdminStoreItem.model_validate(store)


def update_admin_store(db: Session, store_id: int, payload: AdminStoreUpdateRequest) -> AdminStoreItem:
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")
    data = payload.model_dump(exclude_unset=True)
    required_fields = {"store_name", "province", "city", "district", "address", "phone"}
    if any(data.get(field) is None for field in required_fields if field in data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="门店必填字段不能设为空")
    city = db.query(City).filter(City.id == store.city_id).first()
    if city:
        if "city" in data:
            data["city"] = city.name
        if "province" in data:
            data["province"] = city.province
    if "store_code" in data and data["store_code"]:
        exists = db.query(Store).filter(Store.store_code == data["store_code"], Store.id != store_id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="store_code 已存在")
    _validate_store_references(
        db,
        data.get("manager_user_id", store.manager_user_id),
        data.get("dealer_code", store.dealer_code),
        store_id=store.id,
    )
    old_is_primary = store.is_primary
    for k, v in data.items():
        setattr(store, k, v)
    if not store.is_active or store.status != "active":
        store.is_primary = False
    db.commit()
    db.refresh(store)
    # 若本次改为 primary，清除同城市其它主门店
    if not old_is_primary and store.is_primary:
        _reset_other_primary(db, store.city_id, store.id)
    _sync_city_has_store(db, store.city_id)
    _invalidate_city_detail_cache(db, store.city_id)
    return AdminStoreItem.model_validate(store)


def set_primary_store(db: Session, store_id: int) -> AdminStoreItem:
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")
    if not store.is_active or store.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="停用或关闭门店不能设为主门店")
    _reset_other_primary(db, store.city_id, store.id)
    store.is_primary = True
    db.commit()
    db.refresh(store)
    _invalidate_city_detail_cache(db, store.city_id)
    return AdminStoreItem.model_validate(store)


def _reset_other_primary(db: Session, city_id: int, exclude_store_id: int) -> None:
    others = db.query(Store).filter(Store.city_id == city_id, Store.id != exclude_store_id, Store.is_primary == True).all()
    for s in others:
        s.is_primary = False
    db.commit()


# ── CityCase ──

def list_admin_cases(db: Session, city_id: int) -> list[AdminCaseItem]:
    rows = db.query(CityCase).filter(CityCase.city_id == city_id).order_by(CityCase.id.desc()).all()
    return [AdminCaseItem.model_validate(r) for r in rows]


def create_admin_case(db: Session, city_id: int, payload: AdminCaseCreateRequest) -> AdminCaseItem:
    if not db.query(City).filter(City.id == city_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    case = CityCase(city_id=city_id, **payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    _invalidate_city_detail_cache(db, city_id)
    return AdminCaseItem.model_validate(case)


def _validate_store_references(
    db: Session,
    manager_user_id: int | None,
    dealer_code: str | None,
    store_id: int | None = None,
) -> None:
    if manager_user_id:
        manager = db.query(User).filter(User.id == manager_user_id).first()
        if not manager or manager.role != ROLE_STORE_MANAGER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="manager_user_id 必须对应门店管理员")
        if manager.store_id and manager.store_id != store_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该门店管理员已绑定其他门店")
    if dealer_code:
        try:
            dealer_id = int(dealer_code.removeprefix("D2026")) if dealer_code.startswith("D2026") else -1
        except ValueError:
            dealer_id = -1
        if dealer_id < 1 or not db.query(Dealer.id).filter(Dealer.id == dealer_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dealer_code 对应经销商不存在")


def update_admin_case(db: Session, case_id: int, payload: AdminCaseUpdateRequest) -> AdminCaseItem:
    case = db.query(CityCase).filter(CityCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(case, k, v)
    db.commit()
    db.refresh(case)
    _invalidate_city_detail_cache(db, case.city_id)
    return AdminCaseItem.model_validate(case)


def delete_admin_case(db: Session, case_id: int) -> bool:
    case = db.query(CityCase).filter(CityCase.id == case_id).first()
    if not case:
        return False
    city_id = case.city_id
    db.delete(case)
    db.commit()
    _invalidate_city_detail_cache(db, city_id)
    return True


# ── CityFaq ──

def list_admin_faqs(db: Session, city_id: int) -> list[AdminFaqItem]:
    rows = db.query(CityFaq).filter(CityFaq.city_id == city_id).order_by(CityFaq.id.asc()).all()
    return [AdminFaqItem.model_validate(r) for r in rows]


def create_admin_faq(db: Session, city_id: int, payload: AdminFaqCreateRequest) -> AdminFaqItem:
    if not db.query(City).filter(City.id == city_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="城市不存在")
    faq = CityFaq(city_id=city_id, **payload.model_dump())
    db.add(faq)
    db.commit()
    db.refresh(faq)
    _invalidate_city_detail_cache(db, city_id)
    return AdminFaqItem.model_validate(faq)


def update_admin_faq(db: Session, faq_id: int, payload: AdminFaqUpdateRequest) -> AdminFaqItem:
    faq = db.query(CityFaq).filter(CityFaq.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ 不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(faq, k, v)
    db.commit()
    db.refresh(faq)
    _invalidate_city_detail_cache(db, faq.city_id)
    return AdminFaqItem.model_validate(faq)


def delete_admin_faq(db: Session, faq_id: int) -> bool:
    faq = db.query(CityFaq).filter(CityFaq.id == faq_id).first()
    if not faq:
        return False
    city_id = faq.city_id
    db.delete(faq)
    db.commit()
    _invalidate_city_detail_cache(db, city_id)
    return True


# ── User ──

def list_admin_users(db: Session) -> list[AdminUserItem]:
    rows = db.query(User).order_by(User.id.asc()).all()
    return [AdminUserItem.model_validate(r) for r in rows]


def create_admin_user(db: Session, payload: AdminUserCreateRequest) -> AdminUserItem:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    dealer_code, city_id, store_id = _validate_user_scope(
        db,
        payload.role,
        payload.dealer_code,
        payload.city_id,
        payload.store_id,
    )
    if dealer_code and db.query(User.id).filter(User.dealer_code == dealer_code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dealer_code 已绑定其他账号")
    password_error = password_strength_error(payload.password)
    if password_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_error)
    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        dealer_code=dealer_code,
        city_id=city_id,
        store_id=store_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserItem.model_validate(user)


def update_admin_user(db: Session, user_id: int, payload: AdminUserUpdateRequest) -> AdminUserItem:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    role = data.get("role", user.role)
    dealer_code, city_id, store_id = _validate_user_scope(
        db,
        role,
        data.get("dealer_code", user.dealer_code),
        data.get("city_id", user.city_id),
        data.get("store_id", user.store_id),
    )
    if dealer_code and db.query(User.id).filter(User.dealer_code == dealer_code, User.id != user.id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dealer_code 已绑定其他账号")
    next_active = data.get("is_active", user.is_active)
    if user.role == ROLE_ADMIN and (role != ROLE_ADMIN or not next_active):
        active_admins = db.query(User).filter(User.role == ROLE_ADMIN, User.is_active == True).count()
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能停用或降级唯一的有效总部管理员")
    data.update({"role": role, "dealer_code": dealer_code, "city_id": city_id, "store_id": store_id})
    if password:
        password_error = password_strength_error(password)
        if password_error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_error)
        user.hashed_password = get_password_hash(password)
        user.token_version = (user.token_version or 0) + 1
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return AdminUserItem.model_validate(user)


def _validate_user_scope(
    db: Session,
    role: str,
    dealer_code: str | None,
    city_id: int | None,
    store_id: int | None,
) -> tuple[str | None, int | None, int | None]:
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的账号角色")
    if role in (ROLE_ADMIN, ROLE_OPERATOR):
        return None, None, None
    if role == ROLE_CITY_MANAGER:
        if not city_id or not db.query(City.id).filter(City.id == city_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="城市管理员必须绑定有效城市")
        return None, city_id, None
    if role == ROLE_STORE_MANAGER:
        store = db.query(Store).filter(Store.id == store_id).first() if store_id else None
        if not store:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="门店管理员必须绑定有效门店")
        if city_id and city_id != store.city_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号城市与门店所属城市不一致")
        return None, store.city_id, store.id

    if not dealer_code or not dealer_code.startswith("D2026"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="经销商账号必须绑定有效 dealer_code")
    try:
        dealer_id = int(dealer_code.removeprefix("D2026"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dealer_code 格式错误") from exc
    if not db.query(Dealer.id).filter(Dealer.id == dealer_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dealer_code 对应经销商不存在")
    return dealer_code, None, None

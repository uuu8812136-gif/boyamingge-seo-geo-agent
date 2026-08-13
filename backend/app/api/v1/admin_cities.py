"""总部后台 admin 路由：城市/门店/case/faq/user 管理。

权限规则（access_control.py 实现）：
- admin：全部权限
- operator：cities/stores/cases/faqs CRUD + users 只读
- city_manager：限制 city_id（cities 读+改、stores/cases/faqs 限制 scope）
- store_manager：限制 store_id（stores 读+改限制 scope；cases/faqs 读自己 city_id）
- dealer：admin/* 全部 403
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles, ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER
from app.models import AuditLog, CityCase, CityFaq
from app.models.user import User
from app.schemas.admin_city import (
    AdminCaseCreateRequest,
    AdminCaseItem,
    AdminCaseListResponse,
    AdminCaseUpdateRequest,
    AdminCityCreateRequest,
    AdminCityDetail,
    AdminCityItem,
    AdminCityListResponse,
    AdminCityUpdateRequest,
    AdminFaqCreateRequest,
    AdminFaqItem,
    AdminFaqListResponse,
    AdminFaqUpdateRequest,
    AdminStoreCreateRequest,
    AdminStoreItem,
    AdminStoreListResponse,
    AdminStoreUpdateRequest,
    AdminUserCreateRequest,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    AdminAuditLogItem,
    AdminAuditLogListResponse,
)
from app.services import access_control
from app.services.admin_city_service import (
    create_admin_case,
    create_admin_city,
    create_admin_faq,
    create_admin_store,
    create_admin_user,
    delete_admin_case,
    delete_admin_faq,
    get_admin_city,
    list_admin_cases,
    list_admin_cities,
    list_admin_faqs,
    list_admin_stores,
    list_admin_users,
    publish_admin_city,
    set_primary_store,
    unpublish_admin_city,
    update_admin_case,
    update_admin_city,
    update_admin_faq,
    update_admin_store,
    update_admin_user,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# 进入 admin 路由的最低门槛：非 dealer
AdminUser = Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER))]


@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def admin_list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    access_control.assert_user_read_scope(user)
    query = db.query(AuditLog)
    total = query.count()
    rows = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return AdminAuditLogListResponse(total=total, items=[AdminAuditLogItem.model_validate(row) for row in rows])


# ── City ──

@router.get("/cities", response_model=AdminCityListResponse)
def admin_list_cities(
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    city_ids = access_control.filter_city_ids_for_user(db, user)
    items = list_admin_cities(db, city_ids=city_ids)
    return AdminCityListResponse(total=len(items), items=items)


@router.post("/cities", response_model=AdminCityDetail, status_code=status.HTTP_201_CREATED)
def admin_create_city(
    payload: AdminCityCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    if not access_control.can_create_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无新建城市权限")
    return create_admin_city(db, payload)


@router.get("/cities/{city_id}", response_model=AdminCityDetail)
def admin_get_city(
    city_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    return get_admin_city(db, city_id)


@router.patch("/cities/{city_id}", response_model=AdminCityDetail)
def admin_update_city(
    city_id: int,
    payload: AdminCityUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无城市写权限")
    return update_admin_city(db, city_id, payload)


@router.post("/cities/{city_id}/publish", response_model=AdminCityDetail)
def admin_publish_city(
    city_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    if not access_control.can_publish_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无发布权限")
    return publish_admin_city(db, city_id)


@router.post("/cities/{city_id}/unpublish", response_model=AdminCityDetail)
def admin_unpublish_city(
    city_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    if not access_control.can_publish_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无发布权限")
    return unpublish_admin_city(db, city_id)


# ── Store ──

@router.get("/stores", response_model=AdminStoreListResponse)
def admin_list_stores(
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
    city_id: Annotated[int | None, Query()] = None,
):
    city_ids = access_control.filter_city_ids_for_user(db, user)
    store_ids = access_control.filter_store_ids_for_user(user)
    # city_manager 强制限制 city_id；store_manager 强制限制 store_id
    if city_ids is not None:
        if city_id and city_id not in city_ids:
            return AdminStoreListResponse(total=0, items=[])
        city_ids_arg = [city_id] if city_id else city_ids
    else:
        city_ids_arg = [city_id] if city_id else None
    items = list_admin_stores(db, city_id=None, city_ids=city_ids_arg, store_ids=store_ids)
    return AdminStoreListResponse(total=len(items), items=items)


@router.post("/stores", response_model=AdminStoreItem, status_code=status.HTTP_201_CREATED)
def admin_create_store(
    payload: AdminStoreCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, payload.city_id)
    if not access_control.can_create_store(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无新建门店权限（store_manager 不能创建门店）")
    return create_admin_store(db, payload)


@router.patch("/stores/{store_id}", response_model=AdminStoreItem)
def admin_update_store(
    store_id: int,
    payload: AdminStoreUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_store_scope(db, user, store_id)
    if not access_control.can_write_store(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无门店写权限")
    # store_manager 只能改白名单字段，受保护字段（is_active/sort_order/manager_user_id/dealer_code/is_primary/status 等）忽略
    filtered_data = access_control.filter_store_update_fields(user, payload.model_dump(exclude_unset=True))
    if not filtered_data:
        # store_manager 提交的全是受保护字段：返回 403 提示
        if user.role == access_control.ROLE_STORE_MANAGER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="store_manager 无权修改这些字段")
    # 重新构造 payload（用已过滤的 dict 调用 service）
    from app.schemas.admin_city import AdminStoreUpdateRequest as _UpdateReq
    filtered_payload = _UpdateReq(**filtered_data)
    return update_admin_store(db, store_id, filtered_payload)


@router.post("/stores/{store_id}/set-primary", response_model=AdminStoreItem)
def admin_set_primary_store(
    store_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_store_scope(db, user, store_id)
    if not access_control.can_set_primary_store(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无设主门店权限（store_manager 不能 set-primary）")
    return set_primary_store(db, store_id)


# ── CityCase ──

@router.get("/cities/{city_id}/cases", response_model=AdminCaseListResponse)
def admin_list_cases(
    city_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    items = list_admin_cases(db, city_id)
    return AdminCaseListResponse(total=len(items), items=items)


@router.post("/cities/{city_id}/cases", response_model=AdminCaseItem, status_code=status.HTTP_201_CREATED)
def admin_create_case(
    city_id: int,
    payload: AdminCaseCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    return create_admin_case(db, city_id, payload)


@router.patch("/cases/{case_id}", response_model=AdminCaseItem)
def admin_update_case(
    case_id: int,
    payload: AdminCaseUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    case = db.query(CityCase).filter(CityCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    access_control.assert_city_scope(db, user, case.city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    return update_admin_case(db, case_id, payload)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_case(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    case = db.query(CityCase).filter(CityCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    access_control.assert_city_scope(db, user, case.city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    delete_admin_case(db, case_id)
    return None


# ── CityFaq ──

@router.get("/cities/{city_id}/faqs", response_model=AdminFaqListResponse)
def admin_list_faqs(
    city_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    items = list_admin_faqs(db, city_id)
    return AdminFaqListResponse(total=len(items), items=items)


@router.post("/cities/{city_id}/faqs", response_model=AdminFaqItem, status_code=status.HTTP_201_CREATED)
def admin_create_faq(
    city_id: int,
    payload: AdminFaqCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_city_scope(db, user, city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    return create_admin_faq(db, city_id, payload)


@router.patch("/faqs/{faq_id}", response_model=AdminFaqItem)
def admin_update_faq(
    faq_id: int,
    payload: AdminFaqUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    faq = db.query(CityFaq).filter(CityFaq.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ 不存在")
    access_control.assert_city_scope(db, user, faq.city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    return update_admin_faq(db, faq_id, payload)


@router.delete("/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_faq(
    faq_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    faq = db.query(CityFaq).filter(CityFaq.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ 不存在")
    access_control.assert_city_scope(db, user, faq.city_id)
    if not access_control.can_write_city(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无写权限")
    delete_admin_faq(db, faq_id)
    return None


# ── User ──

@router.get("/users", response_model=AdminUserListResponse)
def admin_list_users(
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_user_read_scope(user)
    items = list_admin_users(db)
    return AdminUserListResponse(total=len(items), items=items)


@router.post("/users", response_model=AdminUserItem, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminUserCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_user_write_scope(user)
    return create_admin_user(db, payload)


@router.patch("/users/{user_id}", response_model=AdminUserItem)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: AdminUser,
):
    access_control.assert_user_write_scope(user)
    return update_admin_user(db, user_id, payload)

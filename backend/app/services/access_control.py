"""权限范围校验：基于 user.role / user.city_id / user.store_id。

权限规则（详见 二级域名多城市总部后台改造计划.md §10）：
- admin：全部权限。
- operator：总部运营权限（cities/stores/cases/faqs CRUD），但用户管理只读、不能改系统配置。
- city_manager：只能管理自己的 city_id（cities 读+改、stores/cases/faqs 全部限制 city_id）。
- store_manager：只能管理自己的 store_id（stores 读+改限制 store_id；cases/faqs 读自己 city_id）。
- dealer：不能访问 /api/v1/admin/* 接口。

本模块为纯函数，由路由层显式调用；不依赖 FastAPI Depends，便于单测。
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_ADMIN,
    ROLE_CITY_MANAGER,
    ROLE_DEALER,
    ROLE_OPERATOR,
    ROLE_STORE_MANAGER,
    ADMIN_ROLES,
)
from app.models import Store
from app.models.user import User


def is_admin(user: User) -> bool:
    return user.role == ROLE_ADMIN


def is_admin_or_operator(user: User) -> bool:
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR)


def can_access_admin(user: User) -> bool:
    """是否可进入总部后台 admin/* 接口。dealer 不能。"""
    return user.role in ADMIN_ROLES


def can_manage_users(user: User) -> bool:
    """用户管理权限：仅 admin 可写，operator 只读，其余禁止。"""
    return user.role == ROLE_ADMIN


def can_read_users(user: User) -> bool:
    """用户列表只读权限：admin/operator。"""
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR)


def can_write_city(user: User) -> bool:
    """城市写权限：admin/operator/city_manager（city_manager 仅限自己城市）。"""
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER)


def can_create_city(user: User) -> bool:
    """新建城市：仅 admin/operator。"""
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR)


def can_write_store(user: User) -> bool:
    """门店写权限：admin/operator/city_manager/store_manager（受 scope 限制）。

    store_manager 只能修改自己门店的基本信息（地址/电话等），不能创建门店、不能 set-primary。
    """
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER)


def can_create_store(user: User) -> bool:
    """新建门店权限：仅 admin/operator/city_manager。

    store_manager 不能创建新门店（避免 store_manager 在自己城市无限建店）。
    """
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER)


def can_set_primary_store(user: User) -> bool:
    """设主门店权限：仅 admin/operator/city_manager。

    set-primary 是城市级操作（会清除同城市其它门店的 is_primary），store_manager 无权执行。
    """
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER)


def can_publish_city(user: User) -> bool:
    """城市发布权限：admin/operator/city_manager（限自己城市）。"""
    return user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER)


def assert_admin_access(user: User) -> None:
    """校验可进入 admin 区域；否则 403。"""
    if not can_access_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台访问权限")


def assert_city_scope(db: Session, user: User, city_id: int) -> None:
    """校验用户对指定 city_id 的访问权限。

    - admin/operator：通过。
    - city_manager：user.city_id 必须等于 city_id。
    - store_manager：user.store_id 对应门店的 city_id 必须等于 city_id。
    - dealer：403（不应进入 admin）。
    """
    if not can_access_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台访问权限")
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR):
        return
    if user.role == ROLE_CITY_MANAGER:
        if not user.city_id or user.city_id != city_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该城市")
        return
    if user.role == ROLE_STORE_MANAGER:
        if not user.store_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="门店管理员未绑定门店")
        store = db.query(Store).filter(Store.id == user.store_id).first()
        if not store or store.city_id != city_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该城市")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")


def assert_store_scope(db: Session, user: User, store_id: int) -> None:
    """校验用户对指定 store_id 的访问权限。

    - admin/operator：通过。
    - city_manager：store.city_id 必须等于 user.city_id。
    - store_manager：user.store_id 必须等于 store_id。
    """
    if not can_access_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台访问权限")
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR):
        return
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")
    if user.role == ROLE_CITY_MANAGER:
        if not user.city_id or store.city_id != user.city_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该门店")
        return
    if user.role == ROLE_STORE_MANAGER:
        if not user.store_id or user.store_id != store_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该门店")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作")


def filter_city_ids_for_user(db: Session, user: User) -> list[int] | None:
    """返回用户可访问的 city_id 列表；None 表示可访问全部（admin/operator）。

    - city_manager：[user.city_id]
    - store_manager：[user.store_id 对应门店的 city_id]
    - dealer：[]（空，不应有权限）
    """
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR):
        return None
    if user.role == ROLE_CITY_MANAGER:
        return [user.city_id] if user.city_id else []
    if user.role == ROLE_STORE_MANAGER:
        if not user.store_id:
            return []
        store = db.query(Store).filter(Store.id == user.store_id).first()
        return [store.city_id] if store else []
    return []


def filter_store_ids_for_user(user: User) -> list[int] | None:
    """返回用户可访问的 store_id 列表；None 表示不限（admin/operator/city_manager）。

    - store_manager：[user.store_id]（只能看/改自己门店）
    - dealer：[]（不应有权限）
    """
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER):
        return None
    if user.role == ROLE_STORE_MANAGER:
        return [user.store_id] if user.store_id else []
    return []


# store_manager 允许修改的门店字段白名单（基础展示字段）。
# 受保护字段（is_active/sort_order/manager_user_id/dealer_code/is_primary/status/store_code/city_id）
# store_manager 不得修改，由 admin/operator/city_manager 管理。
STORE_MANAGER_ALLOWED_STORE_FIELDS = frozenset({
    "store_name", "address", "phone", "opening_hours",
    "services", "cover_image", "booking_url", "wechat_qr",
    "gallery", "service_radius", "lat", "lng",
})


def filter_store_update_fields(user: User, data: dict) -> dict:
    """按角色过滤门店更新字段。

    - admin/operator/city_manager：原样返回（保留所有字段）。
    - store_manager：只保留白名单字段，受保护字段静默忽略。
    - 其它：返回空 dict。
    """
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER):
        return data
    if user.role == ROLE_STORE_MANAGER:
        return {k: v for k, v in data.items() if k in STORE_MANAGER_ALLOWED_STORE_FIELDS}
    return {}


# store_manager 允许修改的门店字段白名单（基础展示字段）。
# 受保护字段（is_active/sort_order/manager_user_id/dealer_code/is_primary/status/store_code/city_id）
# store_manager 不得修改，由 admin/operator/city_manager 管理。
STORE_MANAGER_ALLOWED_STORE_FIELDS = frozenset({
    "store_name", "address", "phone", "opening_hours",
    "services", "cover_image", "booking_url", "wechat_qr",
    "gallery", "service_radius", "lat", "lng",
})


def filter_store_update_fields(user: User, data: dict) -> dict:
    """按角色过滤门店更新字段。

    - admin/operator/city_manager：原样返回（保留所有字段）。
    - store_manager：只保留白名单字段，受保护字段静默忽略。
    - 其它：返回空 dict。
    """
    if user.role in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER):
        return data
    if user.role == ROLE_STORE_MANAGER:
        return {k: v for k, v in data.items() if k in STORE_MANAGER_ALLOWED_STORE_FIELDS}
    return {}


def assert_user_write_scope(user: User) -> None:
    """校验可写用户（创建/修改 role/city_id/store_id）：仅 admin。"""
    if not can_manage_users(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无用户管理权限")


def assert_user_read_scope(user: User) -> None:
    """校验可读用户列表：admin/operator。"""
    if not can_read_users(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无用户查看权限")

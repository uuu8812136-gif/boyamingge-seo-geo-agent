"""站内内容发布 API。

端点：
- GET    /api/v1/content/posts           内容列表
- POST   /api/v1/content/posts           创建内容
- GET    /api/v1/content/posts/{id}      内容详情
- PUT    /api/v1/content/posts/{id}      编辑内容
- DELETE /api/v1/content/posts/{id}      删除内容
- POST   /api/v1/content/posts/{id}/publish   发布（立即/定时）
- POST   /api/v1/content/posts/{id}/unpublish 下线
- GET    /api/v1/content/publications    发布记录
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    ROLE_ADMIN,
    ROLE_CITY_MANAGER,
    ROLE_OPERATOR,
    ROLE_STORE_MANAGER,
    get_current_user,
    require_roles,
)
from app.models.user import User
from app.schemas.content_post import (
    ContentPostCreate,
    ContentPostUpdate,
    ContentPostDetail,
    ContentPostListResponse,
    PublicationListResponse,
    PublishActionRequest,
)
from app.services import post_service

router = APIRouter()

_CONTENT_ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER)


@router.get("/content/posts", response_model=ContentPostListResponse, tags=["content-posts"])
def list_posts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
    status: Annotated[str | None, Query()] = None,
    post_type: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return post_service.list_posts(db, user, status, post_type, city, page, page_size)


@router.post("/content/posts", response_model=ContentPostDetail, tags=["content-posts"], status_code=201)
def create_post(
    payload: ContentPostCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    return post_service.create_post(db, user, payload)


@router.get("/content/posts/{post_id}", response_model=ContentPostDetail, tags=["content-posts"])
def get_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    return post_service.get_post(db, user, post_id)


@router.put("/content/posts/{post_id}", response_model=ContentPostDetail, tags=["content-posts"])
def update_post(
    post_id: int,
    payload: ContentPostUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    return post_service.update_post(db, user, post_id, payload)


@router.delete("/content/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["content-posts"])
def delete_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    post_service.delete_post(db, user, post_id)
    return None


@router.post("/content/posts/{post_id}/publish", tags=["content-posts"])
def publish_post(
    post_id: int,
    payload: PublishActionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    return post_service.publish_post(db, user, post_id, payload)


@router.post("/content/posts/{post_id}/unpublish", tags=["content-posts"])
def unpublish_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
):
    return post_service.unpublish_post(db, user, post_id)


@router.get("/content/publications", response_model=PublicationListResponse, tags=["content-posts"])
def list_publications(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(*_CONTENT_ROLES))],
    content_id: Annotated[int | None, Query()] = None,
    platform: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return post_service.list_publications(db, user, content_id, platform, page, page_size)

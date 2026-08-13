"""站内内容发布管理服务。

支持：创建/编辑/删除内容、草稿/发布/下线/定时发布、发布记录查询。
权限：admin/operator 管理全部；city_manager 管理本城市；store_manager 管理本门店。
"""
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models import City, Content, Publication, Store
from app.models.user import User
from app.schemas.content_post import (
    ContentPostCreate,
    ContentPostUpdate,
    ContentPostDetail,
    ContentPostItem,
    ContentPostListResponse,
    PublicationListResponse,
    PublicationRecord,
    PublishActionRequest,
)
from app.services import access_control


# ── slug 生成 ──

def _slugify(text: str) -> str:
    """中文标题转 slug：保留字母数字，中文用拼音首字母（简化版）。"""
    # 简化：取前 30 字符，非字母数字替换为 -
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "-", text[:30]).strip("-")
    # 如果全是中文，用 timestamp 后缀保证唯一
    if not re.search(r"[a-zA-Z0-9]", cleaned):
        cleaned = f"post-{int(datetime.now(timezone.utc).timestamp())}"
    return cleaned.lower()


def _ensure_unique_slug(db: Session, slug: str, exclude_id: int | None = None) -> str:
    """确保 slug 唯一，冲突时加 -2/-3 后缀。"""
    base = slug
    n = 2
    while True:
        q = db.query(Content).filter(Content.slug == slug)
        if exclude_id:
            q = q.filter(Content.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


# ── 权限过滤 ──

def _filter_content_by_user(db: Session, user: User, query):
    """按角色过滤内容可见范围。"""
    if user.role in ("admin", "operator"):
        return query  # 全部可见
    if user.role == "city_manager" and user.city_id:
        city = db.query(City).filter(City.id == user.city_id).first()
        if city:
            return query.filter(Content.city == city.name)
        return query.filter(Content.city.in_(
            db.query(Store.city).filter(Store.city_id == user.city_id).distinct()
        ))
    if user.role == "store_manager" and user.store_id:
        return query.filter(Content.store_id == user.store_id)
    # dealer / 其它：无权
    return query.filter(Content.id == -1)  # 返回空


def _store_city_name(db: Session, store: Store) -> str:
    city = db.query(City).filter(City.id == store.city_id).first()
    return city.name if city else store.city


# ── CRUD ──

def create_post(db: Session, user: User, payload: ContentPostCreate) -> ContentPostDetail:
    """创建内容（草稿状态）。"""
    city = db.query(City).filter(City.name == payload.city).first()
    if not city:
        raise HTTPException(400, "内容必须归属已配置城市")
    target_store = db.query(Store).filter(Store.id == payload.store_id).first() if payload.store_id else None
    if payload.store_id and not target_store:
        raise HTTPException(400, "指定门店不存在")
    if target_store and target_store.city_id != city.id:
        raise HTTPException(400, "内容城市与门店所属城市不一致")

    # store_manager 只能创建到自己门店
    if user.role == "store_manager":
        store = db.query(Store).filter(Store.id == user.store_id).first() if user.store_id else None
        if not store:
            raise HTTPException(403, "store_manager 未绑定有效门店")
        allowed_city = _store_city_name(db, store)
        if payload.store_id and payload.store_id != user.store_id:
            raise HTTPException(403, "store_manager 只能创建本门店内容")
        if payload.city != allowed_city:
            raise HTTPException(403, "store_manager 只能创建本门店所在城市内容")
        payload.store_id = user.store_id
    # city_manager 只能创建到自己城市
    if user.role == "city_manager":
        scoped_city = db.query(City).filter(City.id == user.city_id).first() if user.city_id else None
        if not scoped_city:
            raise HTTPException(403, "city_manager 未绑定有效城市")
        if payload.city != scoped_city.name:
            raise HTTPException(403, "city_manager 只能创建本城市内容")

    slug = _ensure_unique_slug(db, _slugify(payload.title))
    content = Content(
        title=payload.title,
        slug=slug,
        markdown=payload.markdown,
        post_type=payload.post_type,
        city=payload.city,
        store_id=payload.store_id,
        summary=payload.summary,
        cover_image=payload.cover_image,
        cover_image_alt=payload.cover_image_alt,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        canonical=payload.canonical,
        keywords=payload.keywords,
        type=payload.type,
        status="draft",
        author_id=user.id,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return _to_detail(content)


def update_post(db: Session, user: User, post_id: int, payload: ContentPostUpdate) -> ContentPostDetail:
    """编辑内容。"""
    content = _get_owned_post(db, user, post_id)
    data = payload.model_dump(exclude_unset=True)
    required_fields = {"title", "markdown", "post_type", "city"}
    if any(data.get(field) is None for field in required_fields if field in data):
        raise HTTPException(400, "标题、正文、类型和城市不能设为空")
    target_city_name = data.get("city", content.city)
    target_city = db.query(City).filter(City.name == target_city_name).first()
    if not target_city:
        raise HTTPException(400, "内容必须归属已配置城市")
    if "store_id" in data and data["store_id"] is not None:
        target_store = db.query(Store).filter(Store.id == data["store_id"]).first()
        if not target_store:
            raise HTTPException(400, "指定门店不存在")
        if target_store.city_id != target_city.id:
            raise HTTPException(400, "内容城市与门店所属城市不一致")
    elif "city" in data and content.store_id:
        current_store = db.query(Store).filter(Store.id == content.store_id).first()
        if current_store and current_store.city_id != target_city.id:
            raise HTTPException(400, "内容仍绑定其他城市门店，请同时调整门店")
    # store_manager 不能改 store_id
    if user.role == "store_manager":
        store = db.query(Store).filter(Store.id == user.store_id).first() if user.store_id else None
        if not store:
            raise HTTPException(403, "store_manager 未绑定有效门店")
        allowed_city = _store_city_name(db, store)
        if "store_id" in data and data["store_id"] != user.store_id:
            raise HTTPException(403, "store_manager 不能转移内容门店")
        if "city" in data and data["city"] != allowed_city:
            raise HTTPException(403, "store_manager 不能转移内容城市")
        data["store_id"] = user.store_id
        data["city"] = allowed_city
    if user.role == "city_manager":
        city = db.query(City).filter(City.id == user.city_id).first() if user.city_id else None
        if not city:
            raise HTTPException(403, "city_manager 未绑定有效城市")
        if "city" in data and data["city"] != city.name:
            raise HTTPException(403, "city_manager 不能转移内容城市")
    for k, v in data.items():
        setattr(content, k, v)
    # 如果改了 title 且原 slug 为空或自动生成，更新 slug
    if "title" in data and not content.slug:
        content.slug = _ensure_unique_slug(db, _slugify(content.title or "post"), exclude_id=content.id)
    db.commit()
    db.refresh(content)
    return _to_detail(content)


def delete_post(db: Session, user: User, post_id: int) -> None:
    """删除内容（仅 draft/offline 可删）。"""
    content = _get_owned_post(db, user, post_id)
    if content.status == "published":
        raise HTTPException(400, "已发布内容不可直接删除，请先下线")
    db.delete(content)
    db.commit()


def get_post(db: Session, user: User, post_id: int) -> ContentPostDetail:
    content = _get_owned_post(db, user, post_id)
    return _to_detail(content)


def list_posts(
    db: Session, user: User,
    status_filter: str | None = None,
    post_type: str | None = None,
    city: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ContentPostListResponse:
    """内容列表（按角色过滤）。"""
    q = db.query(Content)
    q = _filter_content_by_user(db, user, q)
    if status_filter:
        q = q.filter(Content.status == status_filter)
    if post_type:
        q = q.filter(Content.post_type == post_type)
    if city:
        q = q.filter(Content.city == city)
    total = q.count()
    items = q.order_by(desc(Content.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return ContentPostListResponse(
        total=total,
        items=[ContentPostItem.model_validate(c) for c in items],
    )


# ── 发布管理 ──

def publish_post(db: Session, user: User, post_id: int, payload: PublishActionRequest) -> dict:
    """发布内容（立即或定时）。"""
    content = _get_owned_post(db, user, post_id)
    if content.status == "published":
        existing = db.query(Publication).filter(
            Publication.content_id == content.id,
            Publication.platform == "website",
            Publication.status == "published",
        ).order_by(Publication.id.desc()).first()
        url = existing.url if existing and existing.url else f"/articles/{content.slug}"
        return {
            "status": "published",
            "url": url,
            "published_at": content.published_at.isoformat() if content.published_at else None,
            "publication_id": existing.id if existing else None,
            "content_id": post_id,
            "idempotent": True,
        }
    if content.status not in ("draft", "approved", "offline"):
        raise HTTPException(400, f"当前状态 {content.status} 不可发布")

    if payload.publish_mode == "schedule":
        if not payload.scheduled_at:
            raise HTTPException(400, "定时发布必须提供 scheduled_at")
        try:
            scheduled = datetime.fromisoformat(payload.scheduled_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(400, "scheduled_at 必须是有效 ISO 时间") from exc
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)
        if scheduled <= datetime.now(timezone.utc):
            raise HTTPException(400, "scheduled_at 必须晚于当前时间")
        content.scheduled_at = scheduled
        content.status = "approved"  # 待定时发布
        db.commit()
        return {"status": "scheduled", "scheduled_at": payload.scheduled_at, "content_id": post_id}

    # 立即发布
    now = datetime.now(timezone.utc)
    content.status = "published"
    content.published_at = now
    content.scheduled_at = None
    content.offline_at = None

    # 生成 URL（slug 驱动，前台 Next.js 动态路由）
    slug = content.slug or _ensure_unique_slug(db, _slugify(content.title or "post"), exclude_id=content.id)
    content.slug = slug
    url = f"/articles/{slug}"

    pub = db.query(Publication).filter(
        Publication.content_id == content.id,
        Publication.platform == "website",
        Publication.status == "published",
    ).order_by(Publication.id.desc()).first()
    if pub is None:
        pub = Publication(content_id=content.id, platform="website", tier="L0")
        db.add(pub)
    pub.url = url
    pub.status = "published"
    pub.publish_mode = "direct"
    pub.published_at = now.isoformat()
    pub.operator_id = user.id
    pub.error_message = None
    db.commit()
    return {"status": "published", "url": url, "published_at": now.isoformat(), "publication_id": pub.id, "content_id": post_id}


def unpublish_post(db: Session, user: User, post_id: int) -> dict:
    """下线内容。"""
    content = _get_owned_post(db, user, post_id)
    if content.status != "published":
        raise HTTPException(400, "仅已发布内容可下线")
    content.status = "offline"
    content.offline_at = datetime.now(timezone.utc)
    # 把相关 Publication 标记为 offline
    pubs = db.query(Publication).filter(
        Publication.content_id == content.id,
        Publication.platform == "website",
        Publication.status == "published",
    ).all()
    for pub in pubs:
        pub.status = "offline"
    db.commit()
    return {"status": "offline", "content_id": post_id}


def list_publications(
    db: Session, user: User,
    content_id: int | None = None,
    platform: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PublicationListResponse:
    """发布记录列表。"""
    q = db.query(Publication)
    # 权限：city_manager/store_manager 只看自己内容的发布记录
    if user.role not in ("admin", "operator"):
        content_q = _filter_content_by_user(db, user, db.query(Content.id))
        q = q.filter(Publication.content_id.in_(content_q))
    if content_id:
        q = q.filter(Publication.content_id == content_id)
    if platform:
        q = q.filter(Publication.platform == platform)
    total = q.count()
    items = q.order_by(desc(Publication.created_at), desc(Publication.id)).offset((page - 1) * page_size).limit(page_size).all()
    return PublicationListResponse(
        total=total,
        items=[PublicationRecord.model_validate(p) for p in items],
    )


# ── 定时发布扫描（由后台线程调用）──

def run_scheduled_publish(db: Session) -> int:
    """扫描并执行到时间的定时发布任务，返回发布数量。"""
    now = datetime.now(timezone.utc)
    pending = db.query(Content).filter(
        Content.status == "approved",
        Content.scheduled_at.isnot(None),
        Content.scheduled_at <= now,
    ).all()
    count = 0
    for content in pending:
        content.status = "published"
        content.published_at = now
        content.scheduled_at = None
        slug = content.slug or _ensure_unique_slug(db, _slugify(content.title or "post"), exclude_id=content.id)
        content.slug = slug
        url = f"/articles/{slug}"
        pub = db.query(Publication).filter(
            Publication.content_id == content.id,
            Publication.platform == "website",
            Publication.status == "published",
        ).order_by(Publication.id.desc()).first()
        if pub is None:
            pub = Publication(content_id=content.id, platform="website", tier="L0")
            db.add(pub)
        pub.url = url
        pub.status = "published"
        pub.publish_mode = "schedule"
        pub.published_at = now.isoformat()
        pub.error_message = None
        count += 1
    if count:
        db.commit()
    return count


# ── 内部工具 ──

def _get_owned_post(db: Session, user: User, post_id: int) -> Content:
    """获取内容并校验权限。"""
    content = db.query(Content).filter(Content.id == post_id).first()
    if not content:
        raise HTTPException(404, "内容不存在")
    # 权限校验
    if user.role in ("admin", "operator"):
        return content
    if user.role == "city_manager" and user.city_id:
        city = db.query(City).filter(City.id == user.city_id).first()
        if city and content.city == city.name:
            return content
    if user.role == "store_manager" and user.store_id:
        if content.store_id == user.store_id:
            return content
    raise HTTPException(403, "无权操作此内容")


def _to_detail(content: Content) -> ContentPostDetail:
    return ContentPostDetail.model_validate(content)

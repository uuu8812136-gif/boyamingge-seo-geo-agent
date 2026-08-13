from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Content, Publication
from app.schemas.publish import PublishRequest, PublishResponse
from app.services.llm import CITY_PINYIN

settings = get_settings()


def _slugify(text: str) -> str:
    mapping = {
        "防盗门": "fangdao-men",
        "门窗": "menchuang",
        "断桥铝": "duanqiao-lv",
    }
    return mapping.get(text, text.replace(" ", "-"))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def check_publish_firewall(db: Session, content: Content) -> None:
    city = content.city
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    week_start = (now - timedelta(days=now.weekday())).date().isoformat()

    publications = db.query(Publication).join(Content, Publication.content_id == Content.id).filter(
        Content.city == city,
        Publication.platform == "website",
        Publication.status == "published",
    ).all()

    daily_count = sum(1 for p in publications if p.published_at and p.published_at.startswith(today))
    if daily_count >= settings.publish_daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"单站日均发布上限 {settings.publish_daily_limit} 篇，请排队",
        )

    weekly_count = sum(
        1 for p in publications if p.published_at and p.published_at[:10] >= week_start
    )
    if weekly_count >= settings.publish_weekly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"单站周发布上限 {settings.publish_weekly_limit} 篇，请排队",
        )

    if len(publications) >= settings.new_site_page_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"新站首批页面上限 {settings.new_site_page_limit} 篇，请排队",
        )

    for pub in publications[-5:]:
        prev = db.query(Content).filter(Content.id == pub.content_id).first()
        if prev and _similarity(prev.markdown, content.markdown) > settings.template_similarity_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="同模板页面相似度超过 70%，请排队",
            )


def publish_content(db: Session, payload: PublishRequest) -> PublishResponse:
    scenario = settings.mock_scenario

    # Scenario: publish_fail — 模拟发布失败
    if scenario == "publish_fail":
        raise RuntimeError("模拟发布失败：站点接口返回错误")

    # Scenario: timeout — 模拟发布超时
    if scenario == "timeout":
        import time
        time.sleep(0.1)
        raise TimeoutError("模拟发布超时")

    content = db.query(Content).filter(Content.id == payload.content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")

    if (content.eeat_score or 0) < settings.eeat_threshold or content.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"EEAT 评分低于 {settings.eeat_threshold}，不允许发布",
        )

    check_publish_firewall(db, content)

    published_at = payload.schedule_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    pinyin = CITY_PINYIN.get(content.city, "city")
    intent_slug = _slugify(content.markdown.split("\n")[0].replace("#", "").strip()[:20] or "article")
    slug = f"{pinyin}-{intent_slug}"
    url = f"{settings.site_base_url.rstrip('/')}/articles/{slug}"

    publication = Publication(
        content_id=content.id,
        platform=payload.target,
        tier="L0",
        url=url,
        status="published",
        published_at=published_at,
    )
    content.status = "published"
    db.add(publication)
    db.commit()

    return PublishResponse(status="published", url=url, published_at=published_at)

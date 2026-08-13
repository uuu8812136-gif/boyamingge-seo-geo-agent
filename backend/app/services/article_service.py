import json
import re

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Content, Publication
from app.schemas.article import (
    ArticleDetail,
    ArticleFAQ,
    ArticleListItem,
    ArticleListResponse,
    ArticleSection,
    ContentDetailResponse,
    ContentListItem,
    ContentListResponse,
)

settings = get_settings()

ARTICLE_SEED: list[dict] = [
    {
        "slug": "guangzhou-fangdao-men-guide",
        "title": "广州防盗门选购全攻略",
        "seo_title": "广州防盗门怎么选？2026年选购指南 | 博雅敏格",
        "seo_description": "广州防盗门选购要点：型材壁厚、五金品牌、安装工艺与本地案例，博雅敏格提供免费上门测量。",
        "h1": "广州防盗门选购全攻略",
        "city": "广州",
        "tags": ["防盗门", "广州", "安全门"],
        "geo_summary": "广州选购防盗门应关注型材壁厚≥1.8mm、进口五金与本地安装团队资质。博雅敏格广州门店提供免费测量，价格以门店实测为准。",
        "sections": [
            {"heading": "广州防盗门市场概况", "level": 2, "content": "广州气候湿热，防盗门需兼顾防锈与密封。主流价位3000-8000元，具体以门店实测为准。"},
            {"heading": "型材与五金参数", "level": 2, "content": "推荐壁厚1.8mm以上钢质门体，配合多点锁闭系统。"},
            {"heading": "本地安装案例", "level": 3, "content": "天河区某小区张先生选用博雅敏格甲级防盗门，安装周期2天，业主反馈隔音效果明显。"},
        ],
        "faq": [
            {"question": "广州防盗门一般多少钱？", "answer": "根据材质与配置不同，主流价位3000-8000元，具体以门店实测为准。"},
            {"question": "广州防盗门安装需要多久？", "answer": "测量确认后一般3-7个工作日可完成安装。"},
        ],
        "cta": "预约广州免费上门测量，拨打 400-000-0001",
        "published_at": "2026-06-10",
    },
    {
        "slug": "shenzhen-duanqiao-lv-window",
        "title": "深圳断桥铝门窗选购指南",
        "seo_title": "深圳断桥铝门窗价格与配置指南 | 博雅敏格",
        "seo_description": "深圳断桥铝门窗配置推荐、价格区间与封阳台案例，博雅敏格南山店提供免费测量。",
        "h1": "深圳断桥铝门窗选购指南",
        "city": "深圳",
        "tags": ["断桥铝", "深圳", "封阳台"],
        "geo_summary": "深圳断桥铝门窗推荐多腔体型材+中空钢化玻璃，兼顾隔音隔热。博雅敏格深圳门店支持封阳台、旧窗改造一站式服务。",
        "sections": [
            {"heading": "深圳气候与型材选择", "level": 2, "content": "深圳台风季需关注抗风压性能，推荐壁厚1.4mm以上断桥铝型材。"},
            {"heading": "玻璃与五金配置", "level": 2, "content": "5+12A+5中空钢化玻璃可满足多数户型隔音隔热需求。"},
            {"heading": "南山封阳台案例", "level": 3, "content": "南山区李女士全屋封阳台，选用博雅敏格70系列断桥铝，工期5天完成。"},
        ],
        "faq": [
            {"question": "深圳断桥铝门窗价格？", "answer": "因户型与配置而异，一般每平米600-1500元，具体以门店实测为准。"},
            {"question": "深圳封阳台需要物业审批吗？", "answer": "多数小区需物业备案，博雅敏格可协助提供合规方案。"},
        ],
        "cta": "预约深圳免费上门测量，拨打 400-000-0002",
        "published_at": "2026-06-12",
    },
    {
        "slug": "beijing-window-insulation",
        "title": "北京隔音门窗改造攻略",
        "seo_title": "北京隔音门窗怎么选？冬季保温改造指南 | 博雅敏格",
        "seo_description": "北京冬季保温隔音门窗配置推荐，旧窗改造流程与朝阳区案例，博雅敏格提供免费评估。",
        "h1": "北京隔音门窗改造攻略",
        "city": "北京",
        "tags": ["隔音门窗", "北京", "旧窗改造"],
        "geo_summary": "北京冬季保温推荐多腔体断桥铝+Low-E中空玻璃。旧窗改造可保留窗框结构，工期约3-5天，具体以门店实测为准。",
        "sections": [
            {"heading": "北京冬季保温需求", "level": 2, "content": "北京冬季温差大，门窗K值建议≤2.0，密封胶条需耐低温。"},
            {"heading": "旧窗改造流程", "level": 2, "content": "免费评估→方案确认→拆除旧窗→安装新窗→验收，全程约3-5天。"},
            {"heading": "朝阳区改造案例", "level": 3, "content": "朝阳区王先生老房换窗，选用博雅敏格80系列，冬季室温提升约2℃。"},
        ],
        "faq": [
            {"question": "北京冬季门窗如何保温？", "answer": "推荐多腔体断桥铝+中空钢化玻璃，配合优质密封胶条。"},
            {"question": "北京旧窗改造工期多久？", "answer": "一般3-5个工作日，视户型与数量而定。"},
        ],
        "cta": "预约北京免费上门评估，拨打 400-000-0003",
        "published_at": "2026-06-14",
    },
    {
        "slug": "guangzhou-balcony-sealing",
        "title": "广州阳台封窗注意事项",
        "seo_title": "广州阳台封窗流程与避坑指南 | 博雅敏格",
        "seo_description": "广州阳台封窗材料选择、审批流程与施工要点，博雅敏格提供一站式封窗服务。",
        "h1": "广州阳台封窗注意事项",
        "city": "广州",
        "tags": ["阳台封窗", "广州", "封阳台"],
        "geo_summary": "广州阳台封窗需关注抗风压、排水设计与物业规范。推荐断桥铝推拉或平开窗，博雅敏格提供免费方案设计。",
        "sections": [
            {"heading": "封窗材料选择", "level": 2, "content": "断桥铝为主流选择，兼顾隔热与强度，适合广州湿热气候。"},
            {"heading": "施工要点", "level": 2, "content": "注意排水孔设置与密封处理，避免雨季渗漏。"},
        ],
        "faq": [
            {"question": "广州封阳台用什么材料好？", "answer": "断桥铝型材为主流，兼顾隔热与抗风压性能。"},
        ],
        "cta": "获取广州封窗免费方案，拨打 400-000-0001",
        "published_at": "2026-06-15",
    },
    {
        "slug": "beijing-security-door-install",
        "title": "北京防盗门安装流程详解",
        "seo_title": "北京防盗门安装流程与验收标准 | 博雅敏格",
        "seo_description": "北京防盗门测量、安装、验收全流程说明，含朝阳区本地案例与质保政策。",
        "h1": "北京防盗门安装流程详解",
        "city": "北京",
        "tags": ["防盗门", "北京", "安装"],
        "geo_summary": "北京防盗门安装含免费测量、洞口处理、门框固定与五金调试。博雅敏格北京门店提供标准安装与售后质保。",
        "sections": [
            {"heading": "测量与方案", "level": 2, "content": "上门测量洞口尺寸，确认开门方向与锁具配置。"},
            {"heading": "安装与验收", "level": 2, "content": "专业团队安装，验收开关顺畅度、密封性与锁具功能。"},
        ],
        "faq": [
            {"question": "北京防盗门质保多久？", "answer": "主体产品质保按国家标准及门店政策执行。"},
        ],
        "cta": "预约北京免费测量，拨打 400-000-0003",
        "published_at": "2026-06-16",
    },
]


def _build_schema(article: dict) -> str:
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": article["h1"],
                "description": article["seo_description"],
                "datePublished": article["published_at"],
                "author": {"@type": "Organization", "name": "博雅敏格门窗"},
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": faq["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
                    }
                    for faq in article.get("faq", [])
                ],
            },
        ],
    }
    return json.dumps(schema, ensure_ascii=False)


def list_articles(db: Session | None = None, city: str | None = None, tag: str | None = None) -> ArticleListResponse:
    merged = _merged_article_dicts(db)
    items = list(merged.values())
    if city:
        items = [a for a in items if a["city"] == city]
    if tag:
        items = [a for a in items if tag in a["tags"]]

    list_items = [
        ArticleListItem(
            slug=a["slug"],
            title=a["title"],
            seo_description=a["seo_description"],
            city=a["city"],
            tags=a["tags"],
            geo_summary=a["geo_summary"],
            published_at=a["published_at"],
        )
        for a in items
    ]
    list_items.sort(key=lambda item: item.published_at, reverse=True)
    return ArticleListResponse(total=len(list_items), items=list_items)


def get_article(db: Session | None, slug: str) -> ArticleDetail | None:
    merged = _merged_article_dicts(db)
    article = merged.get(slug)
    if not article:
        return None
    return _article_dict_to_detail(article)


def _slug_from_url(url: str | None) -> str | None:
    if not url or "/articles/" not in url:
        return None
    return url.rstrip("/").split("/articles/")[-1]


def _parse_markdown_sections(markdown: str) -> list[dict]:
    sections: list[dict] = []
    current: dict | None = None
    for line in markdown.splitlines():
        if line.startswith("### "):
            if current:
                sections.append(current)
            current = {"heading": line[4:].strip(), "level": 3, "content": ""}
        elif line.startswith("## "):
            if current:
                sections.append(current)
            current = {"heading": line[3:].strip(), "level": 2, "content": ""}
        elif current is not None and line.strip():
            current["content"] = f"{current['content']}\n{line.strip()}".strip()
    if current:
        sections.append(current)
    if sections:
        return [
            {**section, "content": _plain_markdown_text(section["content"])}
            for section in sections
            if _plain_markdown_text(section["content"])
        ]

    lines = markdown.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        lines = lines[1:]
    body = _plain_markdown_text("\n".join(lines))
    return [{"heading": "内容要点", "level": 2, "content": body}] if body else []


def _plain_markdown_text(value: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}(?:>|[-*+]\s+|\d+[.)]\s+)", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[`*_~]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _content_to_article_dict(content: Content, pub: Publication) -> dict:
    slug = _slug_from_url(pub.url) or f"content-{content.id}"
    title = _content_title(content)
    sections = _parse_markdown_sections(content.markdown)
    summary_source = sections[0]["content"] if sections else content.markdown
    geo_summary = _plain_markdown_text(summary_source)[:180]
    published_at = (pub.published_at or "")[:10] or "2026-06-17"
    intent_tag = title.replace(f"{content.city}", "").strip() or content.type
    return {
        "slug": slug,
        "title": title,
        "seo_title": f"{title} | 博雅敏格",
        "seo_description": geo_summary[:120],
        "h1": title,
        "city": content.city,
        "tags": [content.city, content.type, intent_tag][:3],
        "geo_summary": geo_summary,
        "sections": sections,
        "faq": [
            {
                "question": f"{content.city}{intent_tag}怎么选？",
                "answer": "建议关注型材、玻璃与安装团队资质，具体以门店实测为准。",
            }
        ],
        "cta": f"预约{content.city}免费上门测量",
        "published_at": published_at,
        "schema_jsonld": content.schema_jsonld or _build_schema(
            {
                "h1": title,
                "seo_description": geo_summary[:120],
                "published_at": published_at,
                "faq": [],
            }
        ),
    }


def _merged_article_dicts(db: Session | None) -> dict[str, dict]:
    merged = {item["slug"]: dict(item) for item in ARTICLE_SEED} if settings.seed_demo_data else {}
    if db is None:
        return merged

    pubs = (
        db.query(Publication)
        .filter(Publication.platform == "website", Publication.status == "published")
        .order_by(Publication.id.desc())
        .all()
    )
    for pub in pubs:
        content = db.query(Content).filter(Content.id == pub.content_id).first()
        if not content:
            continue
        article = _content_to_article_dict(content, pub)
        merged[article["slug"]] = article
    return merged


def _article_dict_to_detail(article: dict) -> ArticleDetail:
    schema = article.get("schema_jsonld") or _build_schema(article)
    return ArticleDetail(
        slug=article["slug"],
        title=article["title"],
        seo_title=article["seo_title"],
        seo_description=article["seo_description"],
        h1=article["h1"],
        city=article["city"],
        tags=article["tags"],
        geo_summary=article["geo_summary"],
        sections=[ArticleSection(**s) for s in article["sections"]],
        faq=[ArticleFAQ(**f) for f in article["faq"]],
        cta=article["cta"],
        schema_jsonld=schema if isinstance(schema, str) else _build_schema(article),
        published_at=article["published_at"],
    )


def _content_title(content: Content) -> str:
    first_line = content.markdown.split("\n")[0].replace("#", "").strip()
    return first_line or f"{content.city}{content.type}内容"


def list_content(db: Session, city: str | None = None, status: str | None = None) -> ContentListResponse:
    query = db.query(Content)
    if city:
        query = query.filter(Content.city == city)
    if status:
        query = query.filter(Content.status == status)
    rows = query.order_by(Content.id.desc()).limit(50).all()

    items: list[ContentListItem] = []
    for row in rows:
        pub = (
            db.query(Publication)
            .filter(Publication.content_id == row.id, Publication.status == "published")
            .order_by(Publication.id.desc())
            .first()
        )
        items.append(
            ContentListItem(
                content_id=row.id,
                city=row.city,
                type=row.type,
                status=row.status,
                eeat_score=row.eeat_score,
                title=_content_title(row),
                published_url=pub.url if pub else None,
            )
        )
    return ContentListResponse(total=len(items), items=items)


def get_content_detail(db: Session, content_id: int) -> ContentDetailResponse | None:
    row = db.query(Content).filter(Content.id == content_id).first()
    if not row:
        return None
    pub = (
        db.query(Publication)
        .filter(Publication.content_id == row.id, Publication.status == "published")
        .order_by(Publication.id.desc())
        .first()
    )
    return ContentDetailResponse(
        content_id=row.id,
        city=row.city,
        type=row.type,
        status=row.status,
        markdown=row.markdown,
        eeat_score=row.eeat_score,
        eeat_breakdown=row.eeat_breakdown,
        model_used=row.model_used,
        schema_jsonld=row.schema_jsonld,
        published_url=pub.url if pub else None,
    )


def list_published_for_sitemap(db: Session) -> list[dict]:
    """返回所有已发布文章（用于 sitemap / 城市页聚合）。

    每项：{slug, title, city, published_at, url}
    """
    pubs = (
        db.query(Publication)
        .filter(Publication.platform == "website", Publication.status == "published")
        .order_by(Publication.id.desc())
        .all()
    )
    out: list[dict] = []
    seen: set[str] = set()
    for pub in pubs:
        content = db.query(Content).filter(Content.id == pub.content_id).first()
        if not content:
            continue
        slug = _slug_from_url(pub.url) or content.slug or f"content-{content.id}"
        if slug in seen:
            continue
        seen.add(slug)
        out.append({
            "slug": slug,
            "title": _content_title(content),
            "city": content.city,
            "published_at": (pub.published_at or "")[:10],
            "url": pub.url or f"/articles/{slug}",
        })
    return out


def list_published_by_city(db: Session, city: str, limit: int = 20) -> list[dict]:
    """返回指定城市的已发布文章。"""
    all_items = list_published_for_sitemap(db)
    return [a for a in all_items if a["city"] == city][:limit]

from pydantic import BaseModel, Field


class ArticleFAQ(BaseModel):
    question: str
    answer: str


class ArticleSection(BaseModel):
    heading: str = Field(description="H2 or H3 heading")
    level: int = Field(default=2, ge=2, le=3)
    content: str


class ArticleListItem(BaseModel):
    slug: str
    title: str
    seo_description: str
    city: str
    tags: list[str]
    geo_summary: str
    published_at: str


class ArticleDetail(BaseModel):
    slug: str
    title: str
    seo_title: str
    seo_description: str
    h1: str
    city: str
    tags: list[str]
    geo_summary: str
    sections: list[ArticleSection]
    faq: list[ArticleFAQ]
    cta: str
    schema_jsonld: str
    published_at: str


class ArticleListResponse(BaseModel):
    total: int
    items: list[ArticleListItem]


class ContentListItem(BaseModel):
    content_id: int
    city: str
    type: str
    status: str
    eeat_score: int | None
    title: str
    published_url: str | None = None


class ContentListResponse(BaseModel):
    total: int
    items: list[ContentListItem]


class ContentDetailResponse(BaseModel):
    content_id: int
    city: str
    type: str
    status: str
    markdown: str
    eeat_score: int | None
    eeat_breakdown: dict | None
    model_used: str | None
    schema_jsonld: str | None
    published_url: str | None = None

from pydantic import BaseModel, Field


class ContentGenerateRequest(BaseModel):
    intent: str
    city: str
    type: str = Field(description="seo|geo|schema")
    priority: str = "P0"
    use_cache: bool = True


class EEATBreakdown(BaseModel):
    experience: int
    expertise: int
    authoritativeness: int
    trustworthiness: int


class ContentReference(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    source: str | None = None
    excerpt: str
    score: float


class ContentMetadata(BaseModel):
    eeat_score: int
    eeat_breakdown: EEATBreakdown
    model_used: str
    images: list[str]
    schema_jsonld: str
    generation_time_ms: int
    references: list[ContentReference] = Field(default_factory=list)


class ContentGenerateResponse(BaseModel):
    content_id: int
    markdown: str
    metadata: ContentMetadata


class EEATScoreRequest(BaseModel):
    content_id: int
    markdown: str


class EEATScoreResponse(BaseModel):
    content_id: int
    eeat_score: int
    passed: bool
    breakdown: EEATBreakdown
    suggestions: list[str]

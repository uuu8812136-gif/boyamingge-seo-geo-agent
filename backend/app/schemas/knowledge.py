from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeDocumentBase(BaseModel):
    title: str
    doc_type: str = Field(default="general", description="case|faq|product|policy|general")
    city: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    content: str
    status: str = "active"


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    pass


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = None
    doc_type: str | None = None
    city: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    content: str | None = None
    status: str | None = None


class KnowledgeChunkItem(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    keywords: list[str]
    tags: list[str]

    model_config = {"from_attributes": True}


class KnowledgeDocumentItem(BaseModel):
    id: int
    title: str
    doc_type: str
    city: str | None
    category: str | None
    tags: list[str]
    source: str | None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    chunk_count: int = 0

    model_config = {"from_attributes": True}


class KnowledgeDocumentDetail(KnowledgeDocumentItem):
    content: str
    chunks: list[KnowledgeChunkItem] = Field(default_factory=list)


class KnowledgeListResponse(BaseModel):
    total: int
    items: list[KnowledgeDocumentItem]


class KnowledgeRebuildResponse(BaseModel):
    document_id: int
    chunk_count: int


class KnowledgeSearchRequest(BaseModel):
    query: str
    city: str | None = None
    doc_type: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchHit(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    doc_type: str
    city: str | None
    category: str | None
    source: str | None
    chunk_index: int
    content: str
    keywords: list[str]
    tags: list[str]
    score: int


class KnowledgeSearchResponse(BaseModel):
    total: int
    items: list[KnowledgeSearchHit]

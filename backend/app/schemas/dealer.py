from pydantic import BaseModel, Field


class DealerProfile(BaseModel):
    dealer_code: str
    name: str
    city: str
    phone: str
    baijiahao_account: str | None = None
    status: str
    activation_score: int


class DealerPublicationItem(BaseModel):
    publication_id: int
    content_id: int
    platform: str
    tier: str
    status: str
    title: str
    city: str
    content_type: str
    eeat_score: int | None = None
    markdown_preview: str
    created_at: str | None = None
    expires_at: str | None = None


class DealerPublicationListResponse(BaseModel):
    total: int
    items: list[DealerPublicationItem]


class DealerStats(BaseModel):
    pending: int
    package_ready: int
    confirmed: int
    rejected: int
    published: int
    total_publications: int
    total_leads: int
    new_leads: int
    total_materials: int


class DealerPublicationDetail(BaseModel):
    publication_id: int
    content_id: int
    platform: str
    tier: str
    status: str
    title: str
    city: str
    content_type: str
    eeat_score: int | None = None
    eeat_breakdown: dict | None = None
    markdown: str
    model_used: str | None = None
    schema_jsonld: str | None = None


class ConfirmRequest(BaseModel):
    action: str = Field(pattern="^(confirm|reject)$")


class ConfirmResponse(BaseModel):
    publication_id: int
    status: str
    message: str


class MaterialUploadRequest(BaseModel):
    type: str = Field(default="image", pattern="^(image|video|document)$")
    oss_url: str = Field(min_length=1, max_length=512)
    copyright_declared: str = Field(default="yes", pattern="^(yes|no)$")


class MaterialUploadResponse(BaseModel):
    material_id: int
    status: str
    message: str


class MaterialItem(BaseModel):
    material_id: int
    type: str
    oss_url: str
    copyright_declared: str
    uploaded_at: str | None = None


class MaterialListResponse(BaseModel):
    total: int
    items: list[MaterialItem]


class DealerLeadItem(BaseModel):
    lead_id: int
    name: str
    phone_masked: str
    city: str
    interest: str
    source: str
    status: str
    created_at: str


class DealerLeadListResponse(BaseModel):
    total: int
    items: list[DealerLeadItem]


class LeadStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(new|queued|contacted|converted)$")


class LeadStatusUpdateResponse(BaseModel):
    lead_id: int
    status: str
    message: str

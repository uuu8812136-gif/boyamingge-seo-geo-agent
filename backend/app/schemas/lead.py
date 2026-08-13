from pydantic import BaseModel, Field


class LeadSubmitRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=11, max_length=32)
    city: str
    interest: str = Field(default="门窗咨询")
    source: str = Field(default="website")
    utm: str | None = None


class LeadSubmitResponse(BaseModel):
    lead_id: int
    status: str
    message: str


class LeadListItem(BaseModel):
    lead_id: int
    name: str
    phone_masked: str
    city: str
    interest: str
    source: str
    dealer_id: str | None
    status: str
    created_at: str


class LeadListResponse(BaseModel):
    total: int
    items: list[LeadListItem]

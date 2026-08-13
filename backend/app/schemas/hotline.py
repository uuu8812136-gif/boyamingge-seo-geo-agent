from pydantic import BaseModel


class LeadInfo(BaseModel):
    name: str
    phone: str
    city: str
    interest: str
    source: str
    utm: str | None = None


class HotlinePushRequest(BaseModel):
    lead: LeadInfo


class HotlinePushResponse(BaseModel):
    status: str
    call_id: str
    assigned_dealer: str
    estimated_wait_min: int

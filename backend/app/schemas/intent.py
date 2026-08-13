from pydantic import BaseModel, Field


class IntentRequest(BaseModel):
    search_terms: list[str]
    cities: list[str]
    top_k: int = Field(default=50, ge=1, le=200)


class IntentItem(BaseModel):
    label: str
    intent_type: str
    keywords: list[str]
    city_map: dict[str, str]
    hotness_score: int
    difficulty_score: int
    priority: str


class IntentResponse(BaseModel):
    intents: list[IntentItem]

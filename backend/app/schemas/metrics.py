from pydantic import BaseModel


class MetricItem(BaseModel):
    date: str
    rank_top50_cnt: int | None = None
    uv: int | None = None
    lead_cnt: int | None = None
    cpl: float | None = None


class MetricsSummary(BaseModel):
    total_uv: int
    total_leads: int
    avg_cpl: float
    latest_rank_top50: int
    uv_trend: str
    lead_trend: str
    period_days: int


class MetricsResponse(BaseModel):
    city: str
    metrics: list[MetricItem]
    summary: MetricsSummary | None = None
    data_source: str = "mock"

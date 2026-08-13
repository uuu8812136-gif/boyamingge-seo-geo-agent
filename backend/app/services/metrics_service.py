from datetime import date, timedelta

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Lead
from app.schemas.metrics import MetricItem, MetricsResponse, MetricsSummary

settings = get_settings()

# MVP 基础监测数据（文档 4.8），生产环境对接 ClickHouse + 百度统计
MOCK_METRICS: dict[str, list[dict]] = {
    "广州": [
        {"date": "2026-06-10", "rank_top50_cnt": 8, "uv": 280, "lead_cnt": 5, "cpl": 52.0},
        {"date": "2026-06-11", "rank_top50_cnt": 9, "uv": 295, "lead_cnt": 5, "cpl": 50.0},
        {"date": "2026-06-12", "rank_top50_cnt": 9, "uv": 310, "lead_cnt": 6, "cpl": 49.0},
        {"date": "2026-06-13", "rank_top50_cnt": 10, "uv": 305, "lead_cnt": 6, "cpl": 48.5},
        {"date": "2026-06-14", "rank_top50_cnt": 10, "uv": 320, "lead_cnt": 6, "cpl": 48.0},
        {"date": "2026-06-15", "rank_top50_cnt": 11, "uv": 335, "lead_cnt": 7, "cpl": 46.5},
        {"date": "2026-06-16", "rank_top50_cnt": 12, "uv": 350, "lead_cnt": 8, "cpl": 45.5},
    ],
    "深圳": [
        {"date": "2026-06-10", "rank_top50_cnt": 6, "uv": 220, "lead_cnt": 3, "cpl": 58.0},
        {"date": "2026-06-11", "rank_top50_cnt": 7, "uv": 240, "lead_cnt": 4, "cpl": 56.0},
        {"date": "2026-06-12", "rank_top50_cnt": 7, "uv": 255, "lead_cnt": 4, "cpl": 54.0},
        {"date": "2026-06-13", "rank_top50_cnt": 8, "uv": 265, "lead_cnt": 4, "cpl": 53.0},
        {"date": "2026-06-14", "rank_top50_cnt": 8, "uv": 270, "lead_cnt": 5, "cpl": 52.5},
        {"date": "2026-06-15", "rank_top50_cnt": 9, "uv": 275, "lead_cnt": 5, "cpl": 52.0},
        {"date": "2026-06-16", "rank_top50_cnt": 9, "uv": 280, "lead_cnt": 5, "cpl": 52.0},
    ],
    "北京": [
        {"date": "2026-06-10", "rank_top50_cnt": 5, "uv": 200, "lead_cnt": 2, "cpl": 62.0},
        {"date": "2026-06-11", "rank_top50_cnt": 6, "uv": 215, "lead_cnt": 3, "cpl": 60.0},
        {"date": "2026-06-12", "rank_top50_cnt": 6, "uv": 230, "lead_cnt": 3, "cpl": 58.0},
        {"date": "2026-06-13", "rank_top50_cnt": 7, "uv": 240, "lead_cnt": 3, "cpl": 57.0},
        {"date": "2026-06-14", "rank_top50_cnt": 7, "uv": 250, "lead_cnt": 4, "cpl": 56.0},
        {"date": "2026-06-15", "rank_top50_cnt": 8, "uv": 255, "lead_cnt": 4, "cpl": 55.5},
        {"date": "2026-06-16", "rank_top50_cnt": 8, "uv": 260, "lead_cnt": 4, "cpl": 55.0},
    ],
}


def _trend(values: list[int]) -> str:
    if len(values) < 2:
        return "stable"
    if values[-1] > values[-2]:
        return "up"
    if values[-1] < values[-2]:
        return "down"
    return "stable"


def _build_summary(rows: list[dict]) -> MetricsSummary:
    total_uv = sum(r.get("uv", 0) for r in rows)
    total_leads = sum(r.get("lead_cnt", 0) for r in rows)
    cpl_values = [r["cpl"] for r in rows if r.get("cpl")]
    avg_cpl = round(sum(cpl_values) / len(cpl_values), 1) if cpl_values else 0.0
    latest_rank = rows[-1].get("rank_top50_cnt", 0) if rows else 0
    uv_series = [r.get("uv", 0) for r in rows]
    lead_series = [r.get("lead_cnt", 0) for r in rows]
    return MetricsSummary(
        total_uv=total_uv,
        total_leads=total_leads,
        avg_cpl=avg_cpl,
        latest_rank_top50=latest_rank,
        uv_trend=_trend(uv_series),
        lead_trend=_trend(lead_series),
        period_days=len(rows),
    )


def _db_lead_count(db: Session | None, city: str) -> int:
    if db is None:
        return 0
    return db.query(Lead).filter(Lead.city == city).count()


def _overlay_db_leads(rows: list[dict], db_leads: int) -> list[dict]:
    if db_leads <= 0 or not rows:
        return rows
    merged = [dict(row) for row in rows]
    latest = merged[-1]
    latest["lead_cnt"] = latest.get("lead_cnt", 0) + db_leads
    return merged


def _fetch_live_metrics(city: str, date_from: str | None, date_to: str | None) -> list[dict]:
    """调用百度统计 API 获取真实运营指标。返回与 MOCK_METRICS 相同结构的 rows。

    需配置：BAIDU_TONGJI_TOKEN（access_token）+ BAIDU_TONGJI_SITE_ID（站点ID）
    文档：https://tongji.baidu.com/api/manual/ApiData
    """
    if not settings.baidu_tongji_token or not settings.baidu_tongji_site_id:
        return []

    # 默认查最近 7 天
    today = date.today()
    end = date_to or today.isoformat()
    start = date_from or (today - timedelta(days=6)).isoformat()

    api_base = settings.baidu_tongji_api_base.rstrip("/")
    params = {
        "access_token": settings.baidu_tongji_token,
        "site_id": settings.baidu_tongji_site_id,
        "method": "trend/time/a",               # 按天维度
        "start_date": start.replace("-", ""),
        "end_date": end.replace("-", ""),
        "metrics": "pv_count,visitor_count,ip_count",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{api_base}/report/getData", params=params)
            resp.raise_for_status()
            body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        import logging
        logging.getLogger(__name__).warning("百度统计调用失败: %s", exc)
        return []

    # 百度统计返回结构：{"result": {"items": [[时间], [数值], ...], "fields": [...]}}
    result = body.get("result") or {}
    items = result.get("items") or []
    if len(items) < 2:
        return []

    time_items = items[0]  # [{name: "2026-06-10"}, ...]
    value_items = items[1]  # [{pv_count: "x"}, ...]

    rows: list[dict] = []
    for t, v in zip(time_items, value_items):
        day = (t.get("name") or "")[:10]  # "2026-06-10"
        if not day:
            continue
        pv = int(v.get("pv_count", 0) or 0)
        uv = int(v.get("visitor_count", 0) or 0)
        # 百度统计不直接提供线索数和 CPL，留空由 _overlay_db_leads 叠加真实线索
        rows.append({
            "date": day,
            "rank_top50_cnt": None,   # 百度统计不提供排名，需另接 SEO 工具
            "uv": uv,
            "lead_cnt": 0,
            "cpl": 0.0,
        })

    return rows


def query_metrics(
    db: Session | None,
    city: str,
    date_from: str | None,
    date_to: str | None,
    metric_type: str | None,
) -> MetricsResponse:
    scenario = settings.mock_scenario

    # Scenario: error — 模拟外部 API 异常
    if scenario == "error":
        raise RuntimeError("模拟指标服务异常：外部数据源不可用")

    # Scenario: timeout — 模拟超时
    if scenario == "timeout":
        import time
        time.sleep(0.1)
        raise TimeoutError("模拟指标服务超时")

    # Scenario: empty — 返回空数据
    if scenario == "empty":
        return MetricsResponse(city=city, metrics=[], summary=None, data_source="mock_empty")

    data_source = "mock"
    if settings.metrics_provider == "live":
        rows = _fetch_live_metrics(city, date_from, date_to)
        data_source = "live" if rows else "mock"
        if not rows:
            rows = list(MOCK_METRICS.get(city, MOCK_METRICS["广州"]))
    else:
        rows = list(MOCK_METRICS.get(city, MOCK_METRICS["广州"]))
    rows = _overlay_db_leads(rows, _db_lead_count(db, city))
    if date_from:
        rows = [r for r in rows if r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] <= date_to]

    metrics: list[MetricItem] = []
    for row in rows:
        item = MetricItem(date=row["date"])
        if metric_type in (None, "rank"):
            item.rank_top50_cnt = row.get("rank_top50_cnt")
        if metric_type in (None, "traffic"):
            item.uv = row.get("uv")
        if metric_type in (None, "lead"):
            item.lead_cnt = row.get("lead_cnt")
        if metric_type in (None, "cost"):
            item.cpl = row.get("cpl")
        if metric_type is None:
            item.rank_top50_cnt = row.get("rank_top50_cnt")
            item.uv = row.get("uv")
            item.lead_cnt = row.get("lead_cnt")
            item.cpl = row.get("cpl")
        metrics.append(item)

    if not metrics and city:
        today = date.today().isoformat()
        metrics.append(
            MetricItem(
                date=today,
                rank_top50_cnt=0 if metric_type in (None, "rank") else None,
                uv=0 if metric_type in (None, "traffic") else None,
                lead_cnt=0 if metric_type in (None, "lead") else None,
                cpl=0.0 if metric_type in (None, "cost") else None,
            )
        )

    summary = _build_summary(rows) if rows else None
    return MetricsResponse(city=city, metrics=metrics, summary=summary, data_source=data_source)

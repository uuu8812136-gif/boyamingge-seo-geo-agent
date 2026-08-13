from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CallRecord, Dealer, Lead
from app.schemas.hotline import HotlinePushRequest, HotlinePushResponse

settings = get_settings()


def _queue_hotline(db: Session, payload: HotlinePushRequest, external_call_id: str | None = None) -> HotlinePushResponse:
    dealer = (
        db.query(Dealer)
        .filter(Dealer.city == payload.lead.city, Dealer.status == "active")
        .order_by(Dealer.activation_score.desc())
        .first()
    )
    dealer_code = f"D2026{dealer.id:03d}" if dealer else "D2026001"

    lead = Lead(
        name=payload.lead.name,
        phone=payload.lead.phone,
        city=payload.lead.city,
        interest=payload.lead.interest,
        source=payload.lead.source,
        utm=payload.lead.utm,
        dealer_id=dealer_code,
        status="queued",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    call_id = external_call_id or f"CALL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{lead.id:03d}"
    call_record = CallRecord(
        lead_id=lead.id,
        call_id=call_id,
        duration_sec=None,
        result="queued",
        recording_url=None,
    )
    db.add(call_record)
    db.commit()

    return HotlinePushResponse(
        status="queued",
        call_id=call_id,
        assigned_dealer=dealer_code,
        estimated_wait_min=2,
    )


def _push_hotline_live(payload: HotlinePushRequest) -> str:
    """调用天润融通云呼叫 API 发起外呼，返回外部 call_id。

    需配置：TIANRUN_API_KEY + TIANRUN_API_BASE + TIANRUN_AGENT_ID + TIANRUN_EXT_ID
    文档：https://docs.tianrun.com/
    """
    if not settings.tianrun_api_key or not settings.tianrun_api_base:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="请配置 TIANRUN_API_KEY 与 TIANRUN_API_BASE 后使用 HOTLINE_PROVIDER=live",
        )
    if not settings.tianrun_agent_id or not settings.tianrun_ext_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="请配置 TIANRUN_AGENT_ID 与 TIANRUN_EXT_ID 后使用 HOTLINE_PROVIDER=live",
        )

    api_base = settings.tianrun_api_base.rstrip("/")
    body = {
        "api_key": settings.tianrun_api_key,
        "agent_id": settings.tianrun_agent_id,
        "ext_id": settings.tianrun_ext_id,
        "caller": payload.lead.phone,        # 客户号码
        "called": payload.lead.phone,        # 被叫（实际生产应替换为经销商座席号）
        "customer_name": payload.lead.name,
        "city": payload.lead.city,
        "interest": payload.lead.interest,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{api_base}/call/outbound", json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"天润融通外呼请求超时: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"天润融通外呼调用失败: {exc}",
        ) from exc

    # 天润融通返回结构：{"code": 0, "data": {"call_id": "xxx"}, "msg": "success"}
    if data.get("code") != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"天润融通外呼业务失败: {data.get('msg', '未知错误')}",
        )

    call_id = (data.get("data") or {}).get("call_id")
    if not call_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="天润融通返回数据缺少 call_id",
        )
    return str(call_id)


def push_hotline(db: Session, payload: HotlinePushRequest) -> HotlinePushResponse:
    scenario = settings.mock_scenario

    # Scenario: error — 模拟热线服务异常
    if scenario == "error":
        raise RuntimeError("模拟热线服务异常：天润融通接口不可用")

    # Scenario: timeout — 模拟超时
    if scenario == "timeout":
        import time
        time.sleep(0.1)
        raise TimeoutError("模拟热线服务超时")

    # Scenario: notify_fail — 模拟通知经销商失败
    if scenario == "notify_fail":
        # 线索入库但通知失败
        lead = Lead(
            name=payload.lead.name,
            phone=payload.lead.phone,
            city=payload.lead.city,
            interest=payload.lead.interest,
            source=payload.lead.source,
            utm=payload.lead.utm,
            dealer_id=None,
            status="notify_failed",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return HotlinePushResponse(
            status="notify_failed",
            call_id=None,
            assigned_dealer=None,
            estimated_wait_min=0,
        )

    external_call_id = None
    if settings.hotline_provider == "live":
        external_call_id = _push_hotline_live(payload)
    return _queue_hotline(db, payload, external_call_id)

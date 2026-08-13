from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import City, Dealer, Lead, Store
from app.models.user import User
from app.schemas.lead import LeadListItem, LeadListResponse, LeadSubmitRequest, LeadSubmitResponse


def mask_phone(phone: str) -> str:
    if len(phone) >= 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone[:2] + "****"


def submit_lead(db: Session, payload: LeadSubmitRequest) -> LeadSubmitResponse:
    dealer = (
        db.query(Dealer)
        .filter(Dealer.city == payload.city, Dealer.status == "active")
        .order_by(Dealer.activation_score.desc())
        .first()
    )
    dealer_code = f"D2026{dealer.id:03d}" if dealer else None

    lead = Lead(
        name=payload.name,
        phone=payload.phone,
        city=payload.city,
        interest=payload.interest,
        source=payload.source,
        utm=payload.utm,
        dealer_id=dealer_code,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return LeadSubmitResponse(
        lead_id=lead.id,
        status="received",
        message="留资已提交，客服将尽快与您联系",
    )


def _city_name_for_user(db: Session, user: User) -> str | None:
    if not user.city_id:
        return None
    city = db.query(City).filter(City.id == user.city_id).first()
    return city.name if city else None


def _store_for_user(db: Session, user: User) -> Store | None:
    if not user.store_id:
        return None
    return db.query(Store).filter(Store.id == user.store_id).first()


def _apply_lead_scope(db: Session, query, user: User | None):
    """按后台账号范围过滤线索。

    - admin/operator：全部线索；
    - city_manager：仅本人 city_id / 城市名对应线索；
    - store_manager：仅本人 store_id 对应线索；
    - 其它角色：空结果。
    """
    if user is None or user.role in ("admin", "operator"):
        return query

    if user.role == "city_manager":
        city_name = _city_name_for_user(db, user)
        if not user.city_id and not city_name:
            return query.filter(Lead.id == -1)
        conditions = []
        if user.city_id:
            conditions.append(Lead.city_id == user.city_id)
        if city_name:
            conditions.append(Lead.city == city_name)
        return query.filter(or_(*conditions))

    if user.role == "store_manager":
        store = _store_for_user(db, user)
        if not store:
            return query.filter(Lead.id == -1)
        conditions = [Lead.store_id == store.id]
        if store.dealer_code:
            conditions.append(Lead.dealer_id == store.dealer_code)
        return query.filter(or_(*conditions))

    return query.filter(Lead.id == -1)


def assert_can_access_lead(db: Session, user: User, lead: Lead) -> None:
    if user.role in ("admin", "operator"):
        return
    if user.role == "city_manager":
        city_name = _city_name_for_user(db, user)
        if (user.city_id and lead.city_id == user.city_id) or (city_name and lead.city == city_name):
            return
    if user.role == "store_manager":
        store = _store_for_user(db, user)
        if store and (lead.store_id == store.id or (store.dealer_code and lead.dealer_id == store.dealer_code)):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无线索访问权限")


def list_leads(
    db: Session,
    city: str | None = None,
    status: str | None = None,
    user: User | None = None,
) -> LeadListResponse:
    query = db.query(Lead)
    query = _apply_lead_scope(db, query, user)
    if city:
        query = query.filter(Lead.city == city)
    if status:
        query = query.filter(Lead.status == status)
    rows = query.order_by(Lead.id.desc()).limit(100).all()

    items = [
        LeadListItem(
            lead_id=row.id,
            name=row.name,
            phone_masked=mask_phone(row.phone),
            city=row.city,
            interest=row.interest,
            source=row.source,
            dealer_id=row.dealer_id,
            status=row.status,
            created_at=(row.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M"),
        )
        for row in rows
    ]
    return LeadListResponse(total=len(items), items=items)

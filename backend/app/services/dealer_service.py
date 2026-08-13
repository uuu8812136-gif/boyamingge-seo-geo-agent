from datetime import datetime, timezone
import os
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Content, Dealer, Lead, Material, Publication
from app.schemas.dealer import (
    ConfirmResponse,
    DealerLeadItem,
    DealerLeadListResponse,
    DealerProfile,
    DealerPublicationDetail,
    DealerPublicationItem,
    DealerPublicationListResponse,
    MaterialItem,
    MaterialListResponse,
    MaterialUploadResponse,
)

settings = get_settings()
MATERIAL_UPLOAD_DIR = os.environ.get("MATERIAL_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))


def _content_title(content: Content) -> str:
    first_line = content.markdown.split("\n")[0].replace("#", "").strip()
    return first_line or f"{content.city}{content.type}内容"


def _mask_phone(phone: str) -> str:
    if len(phone) >= 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone[:2] + "****"


def get_dealer_profile(db: Session, dealer_code: str) -> DealerProfile | None:
    dealer = db.query(Dealer).filter(Dealer.id == int(dealer_code.replace("D2026", ""))).first()
    if not dealer:
        return None
    return DealerProfile(
        dealer_code=dealer_code,
        name=dealer.name,
        city=dealer.city,
        phone=dealer.phone,
        baijiahao_account=dealer.baijiahao_account,
        status=dealer.status,
        activation_score=dealer.activation_score,
    )


def list_dealer_publications(db: Session, dealer_code: str, status: str | None = None) -> DealerPublicationListResponse:
    query = db.query(Publication).filter(Publication.dealer_id == dealer_code)
    if status:
        query = query.filter(Publication.status == status)
    pubs = query.order_by(Publication.id.desc()).limit(50).all()

    items: list[DealerPublicationItem] = []
    for pub in pubs:
        content = db.query(Content).filter(Content.id == pub.content_id).first()
        if not content:
            continue
        title = _content_title(content)
        preview = content.markdown[:120].replace("\n", " ")
        items.append(
            DealerPublicationItem(
                publication_id=pub.id,
                content_id=pub.content_id,
                platform=pub.platform,
                tier=pub.tier,
                status=pub.status,
                title=title,
                city=content.city,
                content_type=content.type,
                eeat_score=content.eeat_score,
                markdown_preview=preview,
                expires_at=pub.published_at,
            )
        )
    return DealerPublicationListResponse(total=len(items), items=items)


def get_dealer_stats(db: Session, dealer_code: str) -> dict:
    pubs = db.query(Publication).filter(Publication.dealer_id == dealer_code).all()
    leads = db.query(Lead).filter(Lead.dealer_id == dealer_code).all()
    materials = db.query(Material).filter(Material.dealer_id == dealer_code).all()
    return {
        "pending": len([p for p in pubs if p.status == "pending"]),
        "package_ready": len([p for p in pubs if p.status == "package_ready"]),
        "confirmed": len([p for p in pubs if p.status == "confirmed"]),
        "rejected": len([p for p in pubs if p.status == "rejected"]),
        "published": len([p for p in pubs if p.status == "published"]),
        "total_publications": len(pubs),
        "total_leads": len(leads),
        "new_leads": len([l for l in leads if l.status == "new"]),
        "total_materials": len(materials),
    }


def get_dealer_publication_detail(db: Session, dealer_code: str, publication_id: int) -> DealerPublicationDetail | None:
    pub = (
        db.query(Publication)
        .filter(Publication.id == publication_id, Publication.dealer_id == dealer_code)
        .first()
    )
    if not pub:
        return None
    content = db.query(Content).filter(Content.id == pub.content_id).first()
    if not content:
        return None
    return DealerPublicationDetail(
        publication_id=pub.id,
        content_id=pub.content_id,
        platform=pub.platform,
        tier=pub.tier,
        status=pub.status,
        title=_content_title(content),
        city=content.city,
        content_type=content.type,
        eeat_score=content.eeat_score,
        eeat_breakdown=content.eeat_breakdown,
        markdown=content.markdown,
        model_used=content.model_used,
        schema_jsonld=content.schema_jsonld,
    )


def confirm_publication(db: Session, dealer_code: str, publication_id: int, action: str) -> ConfirmResponse:
    pub = (
        db.query(Publication)
        .filter(Publication.id == publication_id, Publication.dealer_id == dealer_code)
        .first()
    )
    if not pub:
        raise ValueError("内容不存在或无权操作")

    if pub.status not in ("pending", "package_ready"):
        raise ValueError("该内容已处理")

    if action == "confirm":
        pub.status = "confirmed"
        message = "已确认，内容将进入发布队列"
    else:
        pub.status = "rejected"
        message = "已驳回"

    db.commit()
    return ConfirmResponse(publication_id=pub.id, status=pub.status, message=message)


def upload_material(db: Session, dealer_code: str, payload) -> MaterialUploadResponse:
    material = Material(
        dealer_id=dealer_code,
        type=payload.type,
        oss_url=payload.oss_url,
        copyright_declared=payload.copyright_declared,
        uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return MaterialUploadResponse(
        material_id=material.id,
        status="uploaded",
        message="素材上传成功",
    )


def upload_material_file(db: Session, dealer_code: str, file: UploadFile) -> MaterialUploadResponse:
    os.makedirs(MATERIAL_UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "upload.jpg")[1] or ".jpg"
    filename = f"{dealer_code}_{uuid.uuid4().hex[:12]}{ext}"
    filepath = os.path.join(MATERIAL_UPLOAD_DIR, filename)
    content_bytes = file.file.read()
    with open(filepath, "wb") as f:
        f.write(content_bytes)

    material_type = "image" if ext.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif") else "video"
    oss_url = f"/uploads/{filename}"

    material = Material(
        dealer_id=dealer_code,
        type=material_type,
        oss_url=oss_url,
        copyright_declared="yes",
        uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return MaterialUploadResponse(
        material_id=material.id,
        status="uploaded",
        message="素材上传成功",
    )


def list_dealer_materials(db: Session, dealer_code: str) -> MaterialListResponse:
    rows = (
        db.query(Material)
        .filter(Material.dealer_id == dealer_code)
        .order_by(Material.id.desc())
        .limit(50)
        .all()
    )
    items = [
        MaterialItem(
            material_id=row.id,
            type=row.type,
            oss_url=row.oss_url,
            copyright_declared=row.copyright_declared,
            uploaded_at=row.uploaded_at,
        )
        for row in rows
    ]
    return MaterialListResponse(total=len(items), items=items)


def list_dealer_leads(db: Session, dealer_code: str) -> DealerLeadListResponse:
    rows = (
        db.query(Lead)
        .filter(Lead.dealer_id == dealer_code)
        .order_by(Lead.id.desc())
        .limit(50)
        .all()
    )
    items = [
        DealerLeadItem(
            lead_id=row.id,
            name=row.name,
            phone_masked=_mask_phone(row.phone),
            city=row.city,
            interest=row.interest,
            source=row.source,
            status=row.status,
            created_at=(row.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M"),
        )
        for row in rows
    ]
    return DealerLeadListResponse(total=len(items), items=items)


def update_lead_status(db: Session, dealer_code: str, lead_id: int, new_status: str):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.dealer_id == dealer_code)
        .first()
    )
    if not lead:
        raise ValueError("线索不存在或无权操作")
    lead.status = new_status
    db.commit()
    return lead

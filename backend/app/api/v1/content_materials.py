"""内容社媒素材 API（视频/封面绑定，供外部视频平台发布使用）。

端点：
- POST   /api/v1/content/{content_id}/materials/video   上传并绑定视频素材
- GET    /api/v1/content/{content_id}/materials          列出内容的社媒素材
- DELETE /api/v1/content/{content_id}/materials/{id}     软删除素材
"""
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ROLE_ADMIN, ROLE_OPERATOR, require_roles
from app.models import Content, SocialMaterial
from app.models.user import User
from app.schemas.external import ContentMaterialItem, ContentMaterialListResponse
from app.services.media_resolver import get_upload_dir, to_served_url

router = APIRouter()

# 允许的视频扩展名（Playwright 上传的本地文件）
_VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".flv"}
_MAX_VIDEO_MB = 500


def _to_item(m: SocialMaterial) -> ContentMaterialItem:
    return ContentMaterialItem(
        id=m.id,
        content_id=m.content_id,
        filename=m.filename,
        file_type=m.file_type,
        url=to_served_url(m.local_path) if m.local_path else None,
        cover_url=to_served_url(m.cover_path) if m.cover_path else None,
        size_mb=m.size_mb,
        duration_sec=m.duration_sec,
        status=m.status,
        created_at=m.created_at,
    )


@router.post(
    "/content/{content_id}/materials/video",
    response_model=ContentMaterialItem,
    tags=["content-materials"],
    status_code=201,
)
def upload_content_video(
    content_id: int,
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """上传视频文件并绑定为内容的视频素材（供视频号/抖音/快手/B站发布使用）。"""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(404, "内容不存在")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(400, f"不支持的视频格式 {ext or '(空)'}，请上传 mp4/mov/webm 等")

    upload_dir = get_upload_dir()
    subdir = os.path.join(upload_dir, "content_videos", str(content_id))
    os.makedirs(subdir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:16]}{ext}"
    filepath = os.path.join(subdir, stored_name)

    data = file.file.read()
    if not data:
        raise HTTPException(400, "上传的视频文件为空")
    size_mb = round(len(data) / (1024 * 1024), 2)
    if size_mb > _MAX_VIDEO_MB:
        raise HTTPException(400, f"视频过大（{size_mb}MB），上限 {_MAX_VIDEO_MB}MB")
    with open(filepath, "wb") as f:
        f.write(data)

    material = SocialMaterial(
        content_id=content_id,
        filename=file.filename or stored_name,
        local_path=filepath,
        file_type="video",
        size_mb=size_mb,
        status="ready",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return _to_item(material)


@router.get(
    "/content/{content_id}/materials",
    response_model=ContentMaterialListResponse,
    tags=["content-materials"],
)
def list_content_materials(
    content_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
    file_type: Annotated[str | None, Query()] = None,
):
    """列出内容绑定的社媒素材（默认排除已删除）。"""
    q = db.query(SocialMaterial).filter(
        SocialMaterial.content_id == content_id,
        SocialMaterial.status != "deleted",
    )
    if file_type:
        q = q.filter(SocialMaterial.file_type == file_type)
    items = q.order_by(SocialMaterial.id.desc()).all()
    return ContentMaterialListResponse(total=len(items), items=[_to_item(m) for m in items])


@router.delete(
    "/content/{content_id}/materials/{material_id}",
    tags=["content-materials"],
    status_code=204,
)
def delete_content_material(
    content_id: int,
    material_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """软删除内容素材（保留文件，状态置 deleted）。"""
    material = (
        db.query(SocialMaterial)
        .filter(SocialMaterial.id == material_id, SocialMaterial.content_id == content_id)
        .first()
    )
    if not material:
        raise HTTPException(404, "素材不存在")
    material.status = "deleted"
    db.commit()
    return None

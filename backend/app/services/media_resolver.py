"""媒体解析：把内容封面 / 素材图解析为 Playwright 可上传的本地文件路径。

图文/短视频发布需要真实的本地文件（Playwright set_input_files 只接受本地路径）。
本模块负责把各种形态的图片引用（/uploads 路径、http(s) URL、本地路径）统一解析为
上传目录下真实存在的本地文件；http(s) 图片会被下载到本地缓存目录。
"""
from __future__ import annotations

import hashlib
import logging
import os
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = 15
_CACHE_SUBDIR = "publish_cache"


def get_upload_dir() -> str:
    """上传根目录（与 main.py 挂载 /uploads 的目录保持一致）。"""
    upload_dir = os.environ.get("MATERIAL_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def to_served_url(local_path: str) -> str | None:
    """把上传目录下的本地文件路径转换为可访问 URL（/uploads/...）。"""
    if not local_path:
        return None
    try:
        upload_dir = get_upload_dir()
        rel = os.path.relpath(os.path.abspath(local_path), os.path.abspath(upload_dir))
        if rel.startswith(".."):
            return None
        return "/uploads/" + rel.replace(os.sep, "/")
    except Exception:
        return None


def resolve_local_image(value: str | None, *, allow_download: bool = True) -> str | None:
    """把单个图片引用解析为本地存在的文件路径；无法解析返回 None。"""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    upload_dir = get_upload_dir()

    # 1. http(s) 远程图片：下载到缓存目录
    if value.startswith("http://") or value.startswith("https://"):
        if not allow_download:
            return None
        return _download_image(value, upload_dir)

    # 2. /uploads/ 开头：映射到上传目录
    if value.startswith("/uploads/"):
        candidate = os.path.join(upload_dir, value[len("/uploads/"):].replace("/", os.sep))
        return candidate if os.path.isfile(candidate) else None

    # 3. 绝对路径且存在
    if os.path.isabs(value) and os.path.isfile(value):
        return value

    # 4. 相对上传目录 / 当前工作目录
    for base in (upload_dir, os.getcwd()):
        candidate = os.path.join(base, value.lstrip("/").replace("/", os.sep))
        if os.path.isfile(candidate):
            return candidate

    # 5. 其它（如前端 /images 静态资源，后端不存在）无法解析
    return None


def _download_image(url: str, upload_dir: str) -> str | None:
    cache_dir = os.path.join(upload_dir, _CACHE_SUBDIR)
    os.makedirs(cache_dir, exist_ok=True)
    ext = _guess_ext(url)
    name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] + ext
    dest = os.path.join(cache_dir, name)
    if os.path.isfile(dest):
        return dest
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:  # noqa: S310
            data = resp.read()
        if not data:
            return None
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        return dest
    except Exception as e:
        logger.warning("下载图片失败 %s: %s", url, e)
        return None


def _guess_ext(url: str) -> str:
    lower = url.lower().split("?")[0]
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
        if lower.endswith(ext):
            return ext
    return ".jpg"


def resolve_content_media(db, content, cover_path: str | None = None, *, limit: int = 9) -> list[str]:
    """汇总内容的可上传图片本地路径：显式 cover_path + 内容封面 + 绑定素材图。

    Args:
        db: SQLAlchemy Session
        content: Content ORM 实例
        cover_path: 显式指定的封面/首图引用（优先）
        limit: 最多返回图片数

    Returns:
        去重后、本地真实存在的图片路径列表
    """
    from app.models import SocialMaterial

    candidates: list[str] = []
    if cover_path:
        candidates.append(cover_path)
    if content is not None and getattr(content, "cover_image", None):
        candidates.append(content.cover_image)

    if content is not None and getattr(content, "id", None):
        materials = (
            db.query(SocialMaterial)
            .filter(
                SocialMaterial.content_id == content.id,
                SocialMaterial.file_type.in_(("image", "cover")),
                SocialMaterial.status != "deleted",
            )
            .order_by(SocialMaterial.id)
            .all()
        )
        for m in materials:
            if m.local_path:
                candidates.append(m.local_path)

    resolved: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        path = resolve_local_image(c)
        if path and path not in seen:
            seen.add(path)
            resolved.append(path)
        if len(resolved) >= limit:
            break
    return resolved


def resolve_local_video(value: str | None) -> str | None:
    """把单个视频引用解析为本地存在的文件路径；无法解析返回 None。

    与图片不同，视频文件通常较大，不做 http(s) 远程下载（避免超时/占用），
    仅支持 /uploads 路径、绝对路径、相对上传目录/CWD 的本地视频文件。
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    if value.startswith("http://") or value.startswith("https://"):
        # 视频不下载：远程视频需先入库为本地素材
        return None

    upload_dir = get_upload_dir()
    if value.startswith("/uploads/"):
        candidate = os.path.join(upload_dir, value[len("/uploads/"):].replace("/", os.sep))
        return candidate if os.path.isfile(candidate) else None
    if os.path.isabs(value) and os.path.isfile(value):
        return value
    for base in (upload_dir, os.getcwd()):
        candidate = os.path.join(base, value.lstrip("/").replace("/", os.sep))
        if os.path.isfile(candidate):
            return candidate
    return None


def resolve_content_video(db, content, *, material_id: int | None = None) -> dict:
    """解析视频平台发布所需的视频文件与封面。

    优先级：显式 material_id 指定的视频素材 > 内容绑定的第一条 ready 视频素材。

    Returns:
        {"video_path": str | None, "cover_path": str | None, "material_id": int | None}
    """
    from app.models import SocialMaterial

    result = {"video_path": None, "cover_path": None, "material_id": None}
    material = None
    if material_id:
        material = (
            db.query(SocialMaterial)
            .filter(SocialMaterial.id == material_id, SocialMaterial.file_type == "video")
            .first()
        )
    if material is None and content is not None and getattr(content, "id", None):
        material = (
            db.query(SocialMaterial)
            .filter(
                SocialMaterial.content_id == content.id,
                SocialMaterial.file_type == "video",
                SocialMaterial.status != "deleted",
            )
            .order_by(SocialMaterial.id)
            .first()
        )
    if material is None:
        return result

    result["material_id"] = material.id
    result["video_path"] = resolve_local_video(material.local_path)
    # 封面优先用素材自带封面，其次内容封面
    cover_ref = material.cover_path or (getattr(content, "cover_image", None) if content is not None else None)
    result["cover_path"] = resolve_local_image(cover_ref) if cover_ref else None
    return result


__all__ = [
    "get_upload_dir",
    "to_served_url",
    "resolve_local_image",
    "resolve_local_video",
    "resolve_content_media",
    "resolve_content_video",
]

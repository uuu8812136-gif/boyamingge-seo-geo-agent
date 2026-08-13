"""外部平台账号管理 API。

端点：
- GET    /api/v1/external-accounts/platforms    支持的平台列表
- GET    /api/v1/external-accounts              账号列表
- POST   /api/v1/external-accounts              手动添加账号
- DELETE /api/v1/external-accounts/{id}         删除账号
- POST   /api/v1/external-accounts/{id}/login   启动扫码登录
- GET    /api/v1/external-accounts/login/status 轮询登录状态
- POST   /api/v1/external-accounts/{id}/check   校验 cookie
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ROLE_ADMIN, ROLE_OPERATOR, require_roles
from app.integrations.synapse_engine.platform_capabilities import (
    PLATFORM_CAPABILITIES,
    PLATFORM_NAME_TO_CODE,
    is_publishable,
)
from app.models import SocialAccount
from app.models.user import User
from app.schemas.external import (
    ExternalAccountCreate,
    ExternalAccountItem,
    ExternalAccountListResponse,
    LoginStartResponse,
    LoginStatusResponse,
    PlatformInfo,
    PlatformListResponse,
)

router = APIRouter()


@router.get("/external-accounts/platforms", response_model=PlatformListResponse, tags=["external-accounts"])
def list_platforms(
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """返回平台能力清单（verified/beta/planned）。"""
    from app.integrations.synapse_engine.utils.playwright_provider import runtime_available
    runtime_ready = runtime_available()
    items = []
    for cap in PLATFORM_CAPABILITIES:
        can_publish = bool(cap["can_publish"] and runtime_ready)
        items.append(PlatformInfo(
            code=cap["code"],
            name=cap["name"],
            display=cap["display"],
            supported=can_publish,
            tier=cap["tier"],
            can_publish=can_publish,
            note=cap["note"] if runtime_ready or not cap["can_publish"] else "发布运行时未安装，当前环境不可用",
        ))
    return PlatformListResponse(items=items)


@router.get("/external-accounts", response_model=ExternalAccountListResponse, tags=["external-accounts"])
def list_accounts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
    platform: Annotated[str | None, Query()] = None,
    cookie_status: Annotated[str | None, Query(alias="status")] = None,
):
    q = db.query(SocialAccount)
    if platform:
        q = q.filter(SocialAccount.platform == platform)
    if cookie_status:
        q = q.filter(SocialAccount.cookie_status == cookie_status)
    items = q.order_by(SocialAccount.created_at.desc()).all()
    return ExternalAccountListResponse(
        total=len(items),
        items=[ExternalAccountItem.model_validate(a) for a in items],
    )


@router.post("/external-accounts", response_model=ExternalAccountItem, tags=["external-accounts"], status_code=201)
def create_account(
    payload: ExternalAccountCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    code = PLATFORM_NAME_TO_CODE.get(payload.platform)
    if code is None:
        raise HTTPException(400, f"不支持的平台: {payload.platform}")
    account = SocialAccount(
        platform=payload.platform,
        platform_code=code,
        display_name=payload.display_name,
        cookie_status="missing_cookie",
        status="active",
        city=payload.city,
        dealer_id=payload.dealer_id,
        note=payload.note,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return ExternalAccountItem.model_validate(account)


@router.delete("/external-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["external-accounts"])
def delete_account(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "账号不存在")

    # 尝试删除 cookie 文件
    try:
        from app.integrations.synapse_engine import EmbeddedSynapseService
        svc = EmbeddedSynapseService()
        if account.internal_account_id:
            try:
                svc.delete_account_cookie(account.platform, account.internal_account_id)
            except Exception:
                pass  # cookie 文件可能不存在
    except ImportError:
        pass  # synapse_engine 未安装时静默跳过
    db.delete(account)
    db.commit()
    return None


@router.post("/external-accounts/{account_id}/login", response_model=LoginStartResponse, tags=["external-accounts"])
def start_login(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """启动扫码登录。

    关键修复：把 SocialAccount.id 作为 internal_account_id 传给 Synapse，
    确保登录成功后能精准回写到发起扫码的那个账号，不会串号。
    """
    account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "账号不存在")

    from app.integrations.synapse_engine.utils.playwright_provider import runtime_available
    if not runtime_available():
        raise HTTPException(503, "发布运行时未安装，无法启动扫码登录")

    try:
        from app.integrations.synapse_engine import EmbeddedSynapseService
        svc = EmbeddedSynapseService()
        # 用 SocialAccount.id 作为 internal_account_id，登录成功后 cookie 文件以此命名
        result = svc.start_login(account.platform, account_id=str(account.id))
    except ImportError:
        raise HTTPException(503, "发布引擎未安装，请联系管理员")
    except Exception as e:
        raise HTTPException(500, f"启动登录失败: {e}") from e

    return LoginStartResponse(
        session_id=result["session_id"],
        qr_url=result.get("qr_url", ""),
        qr_image=result.get("qr_image", ""),
        platform=account.platform,
        account_id=account.id,
    )


@router.get("/external-accounts/login/status", response_model=LoginStatusResponse, tags=["external-accounts"])
def poll_login_status(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """轮询扫码登录状态。

    关键修复：登录成功后按 result.account_id（即 start_login 传入的 SocialAccount.id）
    精准找到发起扫码的账号并回写，不再按 platform 找最新账号。
    """
    try:
        from app.integrations.synapse_engine import EmbeddedSynapseService
        svc = EmbeddedSynapseService()
        result = svc.poll_login_status(session_id)
    except ImportError:
        raise HTTPException(503, "发布引擎未安装")
    except Exception as e:
        raise HTTPException(500, f"轮询登录状态失败: {e}") from e

    status_val = result.get("status", "unknown")
    message = result.get("message", "")
    internal_account_id = result.get("account_id")  # str(SocialAccount.id)
    user_info = result.get("user_info") or {}

    updated_account_id: int | None = None

    # 登录成功时，精准回写到发起扫码的 SocialAccount
    if status_val == "confirmed" and internal_account_id:
        try:
            social_account_id = int(internal_account_id)
        except (TypeError, ValueError):
            social_account_id = None

        if social_account_id is not None:
            account = db.query(SocialAccount).filter(SocialAccount.id == social_account_id).first()
            if account:
                account.internal_account_id = internal_account_id
                account.cookie_status = "active"
                account.last_login_at = datetime.now(timezone.utc)
                # 回写平台用户信息
                if user_info:
                    uid = user_info.get("user_id")
                    account.user_id = str(uid) if uid not in (None, "") else None
                    account.avatar = user_info.get("avatar") or None
                    account.raw = user_info
                # 回写 cookie 文件路径
                try:
                    cookie_path = svc.get_account_cookie_path(account.platform, internal_account_id)
                    if cookie_path:
                        account.cookie_path = cookie_path
                except Exception:
                    pass
                db.commit()
                db.refresh(account)
                updated_account_id = account.id

    return LoginStatusResponse(
        session_id=session_id,
        status=status_val,
        account_id=updated_account_id,
        internal_account_id=internal_account_id,
        message=message,
        user_info=user_info if user_info else None,
    )


@router.post("/external-accounts/{account_id}/check", tags=["external-accounts"])
def check_cookie(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    """校验账号 cookie 是否仍有效（基于 internal_account_id）。"""
    account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    if not account:
        raise HTTPException(404, "账号不存在")

    if not account.internal_account_id:
        return {"status": "missing_cookie", "valid": False, "message": "未登录，请先扫码登录"}

    try:
        from app.integrations.synapse_engine import EmbeddedSynapseService
        svc = EmbeddedSynapseService()
        result = svc.validate_account_cookie(account.platform, account.internal_account_id)
    except ImportError:
        return {"status": "unavailable", "valid": False, "message": "发布引擎未安装"}
    except Exception as e:
        return {"status": "error", "valid": False, "message": str(e)}

    valid = bool(result.get("valid", False)) if isinstance(result, dict) else False
    account.cookie_status = "active" if valid else "expired"
    db.commit()

    return {"status": account.cookie_status, "valid": valid}

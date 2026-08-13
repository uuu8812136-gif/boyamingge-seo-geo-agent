from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

settings = get_settings()
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

ROLE_ADMIN = "admin"
ROLE_DEALER = "dealer"
ROLE_OPERATOR = "operator"
ROLE_CITY_MANAGER = "city_manager"      # 城市管理员：只能管理自己的 city_id
ROLE_STORE_MANAGER = "store_manager"    # 门店管理员：只能管理自己的 store_id

# 可进入总部后台的角色集合（dealer 不能进入 admin/* 接口）
ADMIN_ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None


class CurrentUserProfile(BaseModel):
    id: int
    username: str
    role: str
    dealer_code: str | None = None
    city_id: int | None = None
    store_id: int | None = None
    is_active: bool = True
    password_changed_at: datetime | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def password_strength_error(password: str) -> str | None:
    """统一密码策略；返回 None 表示可接受。"""
    if len(password) < 12 or len(password) > 128:
        return "密码长度必须为 12–128 位"
    normalized = password.strip().lower()
    if normalized in {
        "admin123",
        "operator123",
        "dealer123",
        "password",
        "12345678",
        "123456789012",
    } or any(marker in normalized for marker in ("replace_with", "change-me", "your_password")):
        return "不能使用默认、常见或占位密码"
    categories = sum(
        (
            any(char.islower() for char in password),
            any(char.isupper() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
            any(ord(char) > 127 for char in password),
        )
    )
    if categories < 3:
        return "密码需至少包含大小写字母、数字、符号或中文中的三类"
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user or not getattr(user, "is_active", True):
        return None
    try:
        verified, updated_hash = password_hash.verify_and_update(password, user.hashed_password)
    except Exception:
        return None
    if not verified:
        return None
    if updated_hash:
        user.hashed_password = updated_hash
        db.commit()
    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未授权",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")
        if username is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    if payload.get("ver") != getattr(user, "token_version", 0):
        raise credentials_exception
    return user


def require_roles(*roles: str):
    def checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
        return current_user

    return checker


async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token_data = {"sub": user.username, "role": user.role, "ver": user.token_version}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


def refresh_access_token(refresh_token: str, db: Session) -> Token:
    """使用 refresh_token 换取新的 access_token + refresh_token。

    流程：解码 JWT → 校验 type=refresh → 校验用户存在且启用 → 签发新 token 对。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="刷新令牌无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if username is None or token_type != "refresh":
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用"
        )
    if payload.get("ver") != getattr(user, "token_version", 0):
        raise credentials_exception

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token_data = {"sub": user.username, "role": user.role, "ver": user.token_version}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )

"""Create the first production administrator without loading demo data."""
from __future__ import annotations

import argparse
import os
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import ROLE_ADMIN, get_password_hash, password_strength_error
from app.models.user import User


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化首个总部管理员")
    parser.add_argument("--username", default=os.getenv("INITIAL_ADMIN_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("INITIAL_ADMIN_PASSWORD", ""))
    parser.add_argument("--require-in-production", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if db.query(User.id).filter(User.role == ROLE_ADMIN, User.is_active == True).first():
            print("已有有效总部管理员，跳过初始化")
            return 0

        settings = get_settings()
        if not args.username or not args.password:
            if args.require_in_production and settings.is_production:
                print(
                    "生产数据库没有管理员；请设置 INITIAL_ADMIN_USERNAME 和 INITIAL_ADMIN_PASSWORD 后重启",
                    file=sys.stderr,
                )
                return 2
            print("未配置初始管理员，跳过初始化")
            return 0

        password_error = password_strength_error(args.password)
        if password_error:
            print(f"初始管理员密码不符合要求：{password_error}", file=sys.stderr)
            return 2
        if db.query(User.id).filter(User.username == args.username).first():
            print("指定用户名已存在但不是有效管理员，请更换用户名或在数据库中修复该账号", file=sys.stderr)
            return 2

        db.add(
            User(
                username=args.username,
                hashed_password=get_password_hash(args.password),
                role=ROLE_ADMIN,
                is_active=True,
            )
        )
        db.commit()
        print(f"已创建首个总部管理员：{args.username}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

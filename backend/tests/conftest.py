import os

# 测试使用 SQLite，必须在导入 app 模块之前设置
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_MOCK_MODE"] = "true"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["MOCK_SCENARIO"] = "normal"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-32-characters"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
import app.main as main_module
from app.models import City, Dealer
from app.models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite://"


@pytest.fixture()
def client():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(
        User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
        )
    )
    db.add(
        Dealer(
            name="测试经销商",
            city="测试城",
            phone="020-88886668",
            status="active",
            activation_score=0,
        )
    )
    db.add_all(
        [
            City(
                name="广州",
                slug="guangzhou",
                province="广东",
                is_active=True,
                content_status="published",
            ),
            City(
                name="深圳",
                slug="shenzhen",
                province="广东",
                is_active=True,
                content_status="published",
            ),
        ]
    )
    db.commit()
    db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    previous_session_local = main_module.SessionLocal
    main_module.SessionLocal = TestingSessionLocal
    os.environ["LLM_MOCK_MODE"] = "true"

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    main_module.SessionLocal = previous_session_local


@pytest.fixture()
def auth_headers(client: TestClient):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

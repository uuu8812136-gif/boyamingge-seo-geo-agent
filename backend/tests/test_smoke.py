"""端到端冒烟测试：验证 MVP 主链路 API 可用。"""
import pytest


def test_smoke_public_endpoints(client):
    health = client.get("/health")
    assert health.status_code == 200

    articles = client.get("/api/v1/articles")
    assert articles.status_code == 200
    assert articles.json()["total"] >= 3

    detail = client.get("/api/v1/articles/guangzhou-fangdao-men-guide")
    assert detail.status_code == 200
    assert detail.json()["h1"]

    lead = client.post(
        "/api/v1/leads",
        json={
            "name": "冒烟测试",
            "phone": "13900001111",
            "city": "广州",
            "interest": "防盗门",
        },
    )
    assert lead.status_code == 200
    assert lead.json()["status"] == "received"


def test_smoke_admin_pipeline(client, auth_headers):
    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin123"},
    )
    assert token_resp.status_code == 200
    assert "access_token" in token_resp.json()

    intents = client.post(
        "/api/v1/intents",
        json={"search_terms": ["防盗门"], "cities": ["广州"], "top_k": 5},
        headers=auth_headers,
    )
    assert intents.status_code == 200

    gen = client.post(
        "/api/v1/content/generate",
        json={
            "intent": "防盗门",
            "city": "广州",
            "type": "seo",
            "priority": "P0",
            "use_cache": False,
        },
        headers=auth_headers,
    )
    assert gen.status_code == 200
    content_id = gen.json()["content_id"]
    markdown = gen.json()["markdown"]

    eeat = client.post(
        "/api/v1/content/eeat-score",
        json={"content_id": content_id, "markdown": markdown},
        headers=auth_headers,
    )
    assert eeat.status_code == 200

    pub = client.post(
        "/api/v1/publish",
        json={"content_id": content_id, "target": "website"},
        headers=auth_headers,
    )
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    metrics = client.get("/api/v1/metrics?city=广州", headers=auth_headers)
    assert metrics.status_code == 200
    assert metrics.json()["summary"]["total_uv"] > 0

    leads = client.get("/api/v1/leads", headers=auth_headers)
    assert leads.status_code == 200

    content_list = client.get("/api/v1/content", headers=auth_headers)
    assert content_list.status_code == 200

    content_detail = client.get(f"/api/v1/content/{content_id}", headers=auth_headers)
    assert content_detail.status_code == 200
    assert content_detail.json()["content_id"] == content_id

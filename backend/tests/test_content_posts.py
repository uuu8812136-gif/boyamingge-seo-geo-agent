"""站内内容发布 API 端到端测试。

覆盖创建、编辑、发布、下线、定时、删除、发布记录、未授权、空字段校验。
"""
from datetime import datetime, timedelta, timezone


def _create_post(client, headers, **overrides):
    payload = {
        "title": "广州防盗门选购指南",
        "markdown": "# 广州防盗门选购指南\n\n正文内容...",
        "post_type": "article",
        "city": "广州",
        "summary": "广州本地防盗门选购要点",
        "cover_image": "https://example.com/cover.jpg",
        "seo_title": "广州防盗门选购-博雅敏格",
        "seo_description": "广州防盗门选购专业建议",
        "keywords": ["防盗门", "广州"],
        "type": "seo",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/content/posts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_post_returns_draft(client, auth_headers):
    data = _create_post(client, auth_headers)
    assert data["id"] > 0
    assert data["status"] == "draft"
    assert data["title"] == "广州防盗门选购指南"
    assert data["city"] == "广州"
    assert data["post_type"] == "article"
    assert data["keywords"] == ["防盗门", "广州"]


def test_create_post_rejects_empty_title(client, auth_headers):
    resp = client.post(
        "/api/v1/content/posts",
        json={"title": "", "markdown": "正文", "city": "广州"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_create_post_requires_auth(client):
    resp = client.post(
        "/api/v1/content/posts",
        json={"title": "test", "markdown": "正文", "city": "广州"},
    )
    assert resp.status_code == 401


def test_get_post_detail(client, auth_headers):
    created = _create_post(client, auth_headers)
    resp = client.get(f"/api/v1/content/posts/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == created["id"]
    assert detail["markdown"].startswith("# 广州防盗门")
    assert detail["seo_title"] == "广州防盗门选购-博雅敏格"


def test_list_posts_filter_by_status(client, auth_headers):
    _create_post(client, auth_headers, title="草稿A")
    resp = client.get("/api/v1/content/posts?status=draft", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(item["status"] == "draft" for item in body["items"])


def test_list_posts_filter_by_city(client, auth_headers):
    _create_post(client, auth_headers, title="广州文章", city="广州")
    _create_post(client, auth_headers, title="深圳文章", city="深圳")
    resp = client.get("/api/v1/content/posts?city=广州", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["city"] == "广州" for item in body["items"])


def test_update_post(client, auth_headers):
    created = _create_post(client, auth_headers)
    resp = client.put(
        f"/api/v1/content/posts/{created['id']}",
        json={"title": "更新后的标题", "summary": "更新摘要"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "更新后的标题"
    assert updated["summary"] == "更新摘要"


def test_publish_post_direct(client, auth_headers):
    created = _create_post(client, auth_headers)
    resp = client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "direct"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "published"
    assert body["published_at"] is not None

    detail = client.get(f"/api/v1/content/posts/{created['id']}", headers=auth_headers).json()
    assert detail["status"] == "published"


def test_publish_post_direct_is_idempotent(client, auth_headers):
    created = _create_post(client, auth_headers, title="幂等发布测试")
    first = client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "direct"},
        headers=auth_headers,
    )
    second = client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "direct"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    records = client.get(
        f"/api/v1/content/publications?content_id={created['id']}&platform=website",
        headers=auth_headers,
    ).json()
    assert len([item for item in records["items"] if item["status"] == "published"]) == 1


def test_publish_post_schedule(client, auth_headers):
    created = _create_post(client, auth_headers)
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    resp = client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "schedule", "scheduled_at": future},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "scheduled"
    assert body["scheduled_at"] is not None


def test_unpublish_post(client, auth_headers):
    created = _create_post(client, auth_headers)
    client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "direct"},
        headers=auth_headers,
    )
    resp = client.post(
        f"/api/v1/content/posts/{created['id']}/unpublish",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    detail = client.get(f"/api/v1/content/posts/{created['id']}", headers=auth_headers).json()
    assert detail["status"] == "offline"


def test_list_publications(client, auth_headers):
    created = _create_post(client, auth_headers)
    client.post(
        f"/api/v1/content/posts/{created['id']}/publish",
        json={"publish_mode": "direct"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/content/publications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    pub = body["items"][0]
    assert pub["content_id"] == created["id"]
    assert pub["platform"] == "website"
    assert pub["status"] == "published"


def test_list_publications_filter_by_content(client, auth_headers):
    a = _create_post(client, auth_headers, title="A")
    b = _create_post(client, auth_headers, title="B")
    client.post(f"/api/v1/content/posts/{a['id']}/publish", json={"publish_mode": "direct"}, headers=auth_headers)
    client.post(f"/api/v1/content/posts/{b['id']}/publish", json={"publish_mode": "direct"}, headers=auth_headers)
    resp = client.get(f"/api/v1/content/publications?content_id={a['id']}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["content_id"] == a["id"] for item in body["items"])


def test_delete_post(client, auth_headers):
    created = _create_post(client, auth_headers, title="待删除")
    resp = client.delete(f"/api/v1/content/posts/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204
    not_found = client.get(f"/api/v1/content/posts/{created['id']}", headers=auth_headers)
    assert not_found.status_code == 404


def test_get_nonexistent_post_returns_404(client, auth_headers):
    resp = client.get("/api/v1/content/posts/99999", headers=auth_headers)
    assert resp.status_code == 404

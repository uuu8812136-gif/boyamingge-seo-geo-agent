def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_intents_api(client, auth_headers):
    resp = client.post(
        "/api/v1/intents",
        json={"search_terms": ["门窗 安装"], "cities": ["广州"], "top_k": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["intents"]) >= 1
    assert data["intents"][0]["priority"] in {"P0", "P1", "P2"}


def test_content_generate_and_eeat(client, auth_headers):
    gen = client.post(
        "/api/v1/content/generate",
        json={"intent": "防盗门", "city": "广州", "type": "seo", "priority": "P0"},
        headers=auth_headers,
    )
    assert gen.status_code == 200
    content_id = gen.json()["content_id"]
    assert gen.json()["metadata"]["model_used"] == "deepseek-v4-pro"
    assert "AI可引用摘要" in gen.json()["markdown"]
    assert '"@type": "Service"' in gen.json()["metadata"]["schema_jsonld"]

    score = client.post(
        "/api/v1/content/eeat-score",
        json={"content_id": content_id, "markdown": gen.json()["markdown"]},
        headers=auth_headers,
    )
    assert score.status_code == 200
    assert "eeat_score" in score.json()


def test_knowledge_crud_search_and_generation_references(client, auth_headers):
    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "广州阳台封窗雨季施工口径",
            "doc_type": "case",
            "city": "广州",
            "category": "阳台封窗",
            "tags": ["阳台封窗", "雨季", "排水"],
            "source": "internal://case/gz-balcony-rain",
            "content": (
                "广州雨季阳台封窗必须提前确认排水坡度和外沿密封。"
                "\n\n天河区案例中，博雅敏格采用断桥铝型材和双道密封胶，施工后雨季无渗漏。"
            ),
        },
        headers=auth_headers,
    )
    assert created.status_code == 200
    document_id = created.json()["id"]
    assert created.json()["chunk_count"] >= 1

    listing = client.get("/api/v1/knowledge?city=广州", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    search = client.post(
        "/api/v1/knowledge/search",
        json={"query": "阳台封窗 排水", "city": "广州", "limit": 3},
        headers=auth_headers,
    )
    assert search.status_code == 200
    assert search.json()["items"][0]["document_id"] == document_id

    gen = client.post(
        "/api/v1/content/generate",
        json={"intent": "阳台封窗", "city": "广州", "type": "seo", "priority": "P0", "use_cache": False},
        headers=auth_headers,
    )
    assert gen.status_code == 200
    references = gen.json()["metadata"]["references"]
    assert any(item["document_id"] == document_id for item in references)

    rebuilt = client.post(f"/api/v1/knowledge/{document_id}/rebuild", headers=auth_headers)
    assert rebuilt.status_code == 200
    assert rebuilt.json()["chunk_count"] >= 1

    deleted = client.delete(f"/api/v1/knowledge/{document_id}", headers=auth_headers)
    assert deleted.status_code == 204


def test_publish_flow(client, auth_headers):
    gen = client.post(
        "/api/v1/content/generate",
        json={"intent": "防盗门", "city": "广州", "type": "seo", "priority": "P0", "use_cache": False},
        headers=auth_headers,
    )
    content_id = gen.json()["content_id"]
    pub = client.post(
        "/api/v1/publish",
        json={"content_id": content_id, "target": "website"},
        headers=auth_headers,
    )
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"
    slug = pub.json()["url"].rstrip("/").split("/articles/")[-1]
    listed = client.get("/api/v1/articles?city=广州")
    assert listed.status_code == 200
    slugs = [item["slug"] for item in listed.json()["items"]]
    assert slug in slugs
    detail = client.get(f"/api/v1/articles/{slug}")
    assert detail.status_code == 200
    article = detail.json()
    assert article["city"] == "广州"
    assert not article["geo_summary"].startswith("#")
    assert all(not section["content"].startswith("#") for section in article["sections"])


def test_distribute_and_hotline(client, auth_headers):
    gen = client.post(
        "/api/v1/content/generate",
        json={"intent": "门窗", "city": "深圳", "type": "geo", "priority": "P2", "use_cache": False},
        headers=auth_headers,
    )
    content_id = gen.json()["content_id"]

    dist = client.post(
        "/api/v1/distribute",
        json={"content_id": content_id, "platforms": ["baijiahao"], "dealer_id": "D2026001"},
        headers=auth_headers,
    )
    assert dist.status_code == 200
    assert dist.json()["tasks"][0]["status"] == "pending"

    assist = client.post(
        "/api/v1/distribute/assist",
        json={"content_id": content_id, "platforms": ["xiaohongshu"]},
        headers=auth_headers,
    )
    assert assist.status_code == 200
    assert assist.json()["packages"][0]["platform"] == "xiaohongshu"

    hotline = client.post(
        "/api/v1/hotline/push",
        json={
            "lead": {
                "name": "张三",
                "phone": "13800138000",
                "city": "广州",
                "interest": "防盗门",
                "source": "seo",
            }
        },
        headers=auth_headers,
    )
    assert hotline.status_code == 200
    assert hotline.json()["status"] == "queued"


def test_metrics(client, auth_headers):
    resp = client.get("/api/v1/metrics?city=广州", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "广州"
    assert data["summary"] is not None
    assert data["summary"]["total_uv"] > 0


def test_metrics_with_leads(client, auth_headers):
    client.post(
        "/api/v1/leads",
        json={"name": "指标测试", "phone": "13900139000", "city": "广州", "interest": "门窗"},
    )
    resp = client.get("/api/v1/metrics?city=广州", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_leads"] >= 8


def test_articles_public(client):
    resp = client.get("/api/v1/articles")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 3

    detail = client.get("/api/v1/articles/guangzhou-fangdao-men-guide")
    assert detail.status_code == 200
    assert detail.json()["city"] == "广州"


def test_leads_submit_and_list(client, auth_headers):
    submit = client.post(
        "/api/v1/leads",
        json={
            "name": "测试用户",
            "phone": "13800138000",
            "city": "广州",
            "interest": "防盗门",
        },
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "received"

    listing = client.get("/api/v1/leads", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert "****" in listing.json()["items"][0]["phone_masked"]


def test_content_list(client, auth_headers):
    client.post(
        "/api/v1/content/generate",
        json={"intent": "门窗", "city": "北京", "type": "seo", "priority": "P1", "use_cache": False},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/content", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
def test_change_password_invalidates_existing_tokens(client):
    login = client.post("/api/v1/auth/token", data={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    pair = login.json()
    headers = {"Authorization": f"Bearer {pair['access_token']}"}

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "admin123", "new_password": "SecureAdmin123!"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/token", data={"username": "admin", "password": "admin123"}).status_code == 401
    assert client.post("/api/v1/auth/token", data={"username": "admin", "password": "SecureAdmin123!"}).status_code == 200


def test_weak_and_placeholder_passwords_are_rejected(client, auth_headers):
    weak_change = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "admin123", "new_password": "aaaaaaaaaaaa"},
        headers=auth_headers,
    )
    assert weak_change.status_code == 400

    placeholder_user = client.post(
        "/api/v1/admin/users",
        json={
            "username": "placeholder_password_user",
            "password": "REPLACE_WITH_AT_LEAST_12_CHARS_PASSWORD",
            "role": "operator",
        },
        headers=auth_headers,
    )
    assert placeholder_user.status_code == 400


def test_admin_faq_crud_and_audit_log(client, auth_headers):
    cities = client.get("/api/v1/admin/cities", headers=auth_headers).json()["items"]
    city_id = cities[0]["id"]
    created = client.post(
        f"/api/v1/admin/cities/{city_id}/faqs",
        json={"question": "测试问题？", "answer": "测试回答。"},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    faq_id = created.json()["id"]
    listed = client.get(f"/api/v1/admin/cities/{city_id}/faqs", headers=auth_headers)
    assert any(item["id"] == faq_id for item in listed.json()["items"])
    logs = client.get("/api/v1/admin/audit-logs", headers=auth_headers)
    assert logs.status_code == 200
    assert any(item["path"].endswith("/faqs") and item["method"] == "POST" for item in logs.json()["items"])

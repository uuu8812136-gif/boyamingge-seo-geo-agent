"""Delivery-level regressions for publication, assignment and account scopes."""
from datetime import datetime, timedelta, timezone


def _create_city(client, headers, name: str, slug: str, status: str = "published") -> dict:
    response = client.post(
        "/api/v1/admin/cities",
        json={
            "name": name,
            "slug": slug,
            "province": "测试省",
            "is_active": True,
            "content_status": status,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_store(client, headers, city: dict, name: str, **extra) -> dict:
    payload = {
        "city_id": city["id"],
        "store_name": name,
        "province": "错误省份应被纠正",
        "city": "错误城市应被纠正",
        "district": "测试区",
        "address": "测试路 1 号",
        "phone": "020-88880001",
        **extra,
    }
    response = client.post("/api/v1/admin/stores", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_post(client, headers, city: str, store_id: int | None = None) -> dict:
    response = client.post(
        "/api/v1/content/posts",
        json={
            "title": f"{city}交付测试文章",
            "markdown": "真实正文",
            "post_type": "article",
            "city": city,
            "store_id": store_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_draft_city_and_its_store_are_never_public(client, auth_headers):
    city = _create_city(client, auth_headers, "草稿隔离城", "draft-isolation", "draft")
    store = _create_store(client, auth_headers, city, "草稿城门店")

    public_stores = client.get("/api/v1/cities/stores/all")
    assert public_stores.status_code == 200
    assert store["id"] not in {item["id"] for item in public_stores.json()["items"]}

    located = client.get("/api/v1/cities/locate?city_name=草稿隔离城")
    assert located.status_code == 200
    assert located.json()["city"] is None
    assert located.json()["redirect_slug"] is None


def test_store_state_and_lead_assignment_stay_consistent(client, auth_headers):
    city = _create_city(client, auth_headers, "门店状态城", "store-state-city")
    store = _create_store(
        client,
        auth_headers,
        city,
        "状态测试门店",
        dealer_code="D2026001",
        is_primary=True,
    )
    assert store["city"] == city["name"]
    assert store["province"] == city["province"]

    detail = client.get(f"/api/v1/admin/cities/{city['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["has_store"] is True

    lead = client.post(
        "/api/v1/cities/leads",
        json={
            "name": "归属测试客户",
            "phone": "13800001111",
            "city_name": city["name"],
            "preferred_store_id": store["id"],
            "interest": "阳台封窗",
        },
    )
    assert lead.status_code == 200, lead.text
    leads = client.get("/api/v1/leads", headers=auth_headers).json()["items"]
    assert next(item for item in leads if item["lead_id"] == lead.json()["lead_id"])["dealer_id"] == "D2026001"

    closed = client.patch(
        f"/api/v1/admin/stores/{store['id']}",
        json={"status": "closed"},
        headers=auth_headers,
    )
    assert closed.status_code == 200
    assert closed.json()["is_primary"] is False
    assert client.get(f"/api/v1/admin/cities/{city['id']}", headers=auth_headers).json()["has_store"] is False

    rejected = client.post(
        "/api/v1/cities/leads",
        json={
            "name": "关闭门店客户",
            "phone": "13800002222",
            "city_name": city["name"],
            "preferred_store_id": store["id"],
            "interest": "旧窗改造",
        },
    )
    assert rejected.status_code == 400


def test_city_name_prevents_cross_city_preferred_store(client, auth_headers):
    city_a = _create_city(client, auth_headers, "分配城甲", "assignment-city-a")
    city_b = _create_city(client, auth_headers, "分配城乙", "assignment-city-b")
    store_b = _create_store(client, auth_headers, city_b, "乙城门店")

    response = client.post(
        "/api/v1/cities/leads",
        json={
            "name": "跨城测试客户",
            "phone": "13800003333",
            "city_name": city_a["name"],
            "preferred_store_id": store_b["id"],
            "interest": "隔音窗",
        },
    )
    assert response.status_code == 400


def test_city_rename_cascades_store_lead_and_content(client, auth_headers):
    city = _create_city(client, auth_headers, "改名前城市", "rename-city")
    store = _create_store(client, auth_headers, city, "改名测试门店")
    post = _create_post(client, auth_headers, city["name"], store["id"])
    lead = client.post(
        "/api/v1/cities/leads",
        json={
            "name": "城市改名客户",
            "phone": "13800004444",
            "city_id": city["id"],
            "preferred_store_id": store["id"],
            "interest": "断桥铝门窗",
        },
    )
    assert lead.status_code == 200

    renamed = client.patch(
        f"/api/v1/admin/cities/{city['id']}",
        json={"name": "改名后城市", "province": "新测试省"},
        headers=auth_headers,
    )
    assert renamed.status_code == 200, renamed.text
    stores = client.get(f"/api/v1/admin/stores?city_id={city['id']}", headers=auth_headers).json()["items"]
    assert stores[0]["city"] == "改名后城市"
    assert stores[0]["province"] == "新测试省"
    assert client.get(f"/api/v1/content/posts/{post['id']}", headers=auth_headers).json()["city"] == "改名后城市"
    lead_rows = client.get("/api/v1/leads", headers=auth_headers).json()["items"]
    assert next(item for item in lead_rows if item["lead_id"] == lead.json()["lead_id"])["city"] == "改名后城市"


def test_user_scope_and_unique_admin_guards(client, auth_headers):
    city = _create_city(client, auth_headers, "账号权限城", "account-scope-city")
    store = _create_store(client, auth_headers, city, "账号权限门店")

    missing_scope = client.post(
        "/api/v1/admin/users",
        json={"username": "missing_scope", "password": "SecurePass123!", "role": "city_manager"},
        headers=auth_headers,
    )
    assert missing_scope.status_code == 400

    store_user = client.post(
        "/api/v1/admin/users",
        json={
            "username": "bound_store_user",
            "password": "SecurePass123!",
            "role": "store_manager",
            "store_id": store["id"],
        },
        headers=auth_headers,
    )
    assert store_user.status_code == 201
    assert store_user.json()["city_id"] == city["id"]

    dealer = client.post(
        "/api/v1/admin/users",
        json={
            "username": "dealer_once",
            "password": "SecurePass123!",
            "role": "dealer",
            "dealer_code": "D2026004",
        },
        headers=auth_headers,
    )
    assert dealer.status_code == 201, dealer.text
    duplicate = client.post(
        "/api/v1/admin/users",
        json={
            "username": "dealer_twice",
            "password": "SecurePass123!",
            "role": "dealer",
            "dealer_code": "D2026004",
        },
        headers=auth_headers,
    )
    assert duplicate.status_code == 400

    users = client.get("/api/v1/admin/users", headers=auth_headers).json()["items"]
    admin_id = next(item["id"] for item in users if item["username"] == "admin")
    demote = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"role": "operator"},
        headers=auth_headers,
    )
    assert demote.status_code == 400


def test_content_relations_and_schedule_validation(client, auth_headers):
    city_a = _create_city(client, auth_headers, "内容城甲", "content-city-a")
    city_b = _create_city(client, auth_headers, "内容城乙", "content-city-b")
    store_a = _create_store(client, auth_headers, city_a, "内容甲门店")

    missing_city = client.post(
        "/api/v1/content/posts",
        json={"title": "不存在城市", "markdown": "正文", "city": "未配置城市"},
        headers=auth_headers,
    )
    assert missing_city.status_code == 400

    mismatch = client.post(
        "/api/v1/content/posts",
        json={"title": "跨城内容", "markdown": "正文", "city": city_b["name"], "store_id": store_a["id"]},
        headers=auth_headers,
    )
    assert mismatch.status_code == 400

    post = _create_post(client, auth_headers, city_a["name"], store_a["id"])
    invalid = client.post(
        f"/api/v1/content/posts/{post['id']}/publish",
        json={"publish_mode": "schedule", "scheduled_at": "not-a-date"},
        headers=auth_headers,
    )
    assert invalid.status_code == 400
    past = client.post(
        f"/api/v1/content/posts/{post['id']}/publish",
        json={
            "publish_mode": "schedule",
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert past.status_code == 400

    cross_city_update = client.put(
        f"/api/v1/content/posts/{post['id']}",
        json={"city": city_b["name"]},
        headers=auth_headers,
    )
    assert cross_city_update.status_code == 400


def test_invalid_nullable_and_enum_updates_are_rejected(client, auth_headers):
    city = _create_city(client, auth_headers, "输入校验城", "input-validation-city")
    store = _create_store(client, auth_headers, city, "输入校验门店")

    assert client.patch(
        f"/api/v1/admin/cities/{city['id']}", json={"name": None}, headers=auth_headers
    ).status_code in (400, 422)
    assert client.patch(
        f"/api/v1/admin/stores/{store['id']}", json={"address": None}, headers=auth_headers
    ).status_code in (400, 422)
    assert client.patch(
        f"/api/v1/admin/stores/{store['id']}", json={"status": "unexpected"}, headers=auth_headers
    ).status_code == 422
    robots = client.patch(
        f"/api/v1/admin/cities/{city['id']}",
        json={"robots_policy": "noindex_nofollow"},
        headers=auth_headers,
    )
    assert robots.status_code == 200
    assert robots.json()["robots_policy"] == "noindex_nofollow"

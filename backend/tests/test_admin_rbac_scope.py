"""Admin role scope regression tests.

These tests cover the practical account hierarchy used by the operations
dashboard: headquarters can see all data; city managers see only their city;
store managers see only their own store.
"""


def _login(client, username: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_city(client, headers, name: str, slug: str) -> int:
    resp = client.post(
        "/api/v1/admin/cities",
        json={
            "name": name,
            "slug": slug,
            "province": "测试省",
            "is_active": True,
            "has_store": True,
            "content_status": "published",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_store(client, headers, city_id: int, name: str, district: str) -> int:
    resp = client.post(
        "/api/v1/admin/stores",
        json={
            "city_id": city_id,
            "store_name": name,
            "province": "测试省",
            "city": "权限城",
            "district": district,
            "address": f"{district}测试路 1 号",
            "phone": "020-88880000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_user(client, headers, username: str, password: str, role: str, **scope):
    resp = client.post(
        "/api/v1/admin/users",
        json={"username": username, "password": password, "role": role, **scope},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _submit_store_lead(client, city_id: int, store_id: int, name: str):
    resp = client.post(
        "/api/v1/cities/leads",
        json={
            "name": name,
            "phone": "13800008888",
            "city_id": city_id,
            "preferred_store_id": store_id,
            "interest": "阳台封窗",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["lead_id"]


def test_auth_me_and_scoped_admin_data(client, auth_headers):
    city_a = _create_city(client, auth_headers, "权限城A", "rbac-city-a")
    city_b = _create_city(client, auth_headers, "权限城B", "rbac-city-b")
    store_a1 = _create_store(client, auth_headers, city_a, "权限城A一店", "一区")
    store_a2 = _create_store(client, auth_headers, city_a, "权限城A二店", "二区")
    store_b1 = _create_store(client, auth_headers, city_b, "权限城B一店", "三区")

    _create_user(client, auth_headers, "rbac_city_mgr", "SecureCity123!", "city_manager", city_id=city_a)
    _create_user(client, auth_headers, "rbac_store_mgr", "SecureStore123!", "store_manager", store_id=store_a1)

    city_headers = _login(client, "rbac_city_mgr", "SecureCity123!")
    store_headers = _login(client, "rbac_store_mgr", "SecureStore123!")

    me = client.get("/api/v1/auth/me", headers=store_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "store_manager"
    assert me.json()["store_id"] == store_a1

    city_stores = client.get("/api/v1/admin/stores", headers=city_headers)
    assert city_stores.status_code == 200
    assert {item["id"] for item in city_stores.json()["items"]} == {store_a1, store_a2}

    store_stores = client.get("/api/v1/admin/stores", headers=store_headers)
    assert store_stores.status_code == 200
    assert [item["id"] for item in store_stores.json()["items"]] == [store_a1]

    assert client.post(
        "/api/v1/admin/stores",
        json={
            "city_id": city_a,
            "store_name": "越权门店",
            "province": "测试省",
            "city": "权限城",
            "district": "四区",
            "address": "测试地址",
            "phone": "020-00000000",
        },
        headers=store_headers,
    ).status_code == 403

    _submit_store_lead(client, city_a, store_a1, "一店客户")
    _submit_store_lead(client, city_a, store_a2, "二店客户")
    _submit_store_lead(client, city_b, store_b1, "三店客户")

    city_leads = client.get("/api/v1/leads", headers=city_headers)
    assert city_leads.status_code == 200
    assert {item["name"] for item in city_leads.json()["items"]} == {"一店客户", "二店客户"}

    store_leads = client.get("/api/v1/leads", headers=store_headers)
    assert store_leads.status_code == 200
    assert [item["name"] for item in store_leads.json()["items"]] == ["一店客户"]

    assert client.get("/api/v1/metrics?city=权限城A", headers=city_headers).status_code == 200
    assert client.get("/api/v1/metrics?city=权限城B", headers=city_headers).status_code == 403
    assert client.get("/api/v1/metrics?city=权限城A", headers=store_headers).status_code == 403

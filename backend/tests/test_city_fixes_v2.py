"""多城市防呆修复 v2 测试。

覆盖：
- Fix 1：store_manager 更新门店字段白名单（受保护字段被忽略或 403）
- Fix 2：subdomain 格式 + 保留字校验（create/update）
- Fix 3：公开城市接口强制 active_only=true（active_only 参数失效）
"""
import pytest


# ── 辅助函数（复用 v1 模式）──

def _create_city(client, headers, name="测试城市", slug="test-city",
                 content_status="published", is_active=True, has_store=True,
                 subdomain=None):
    payload = {
        "name": name, "slug": slug, "province": "测试省",
        "is_active": is_active, "content_status": content_status,
        "has_store": has_store,
    }
    if subdomain:
        payload["subdomain"] = subdomain
    resp = client.post("/api/v1/admin/cities", json=payload, headers=headers)
    assert resp.status_code == 201, f"创建城市失败: {resp.text}"
    return resp.json()["id"]


def _create_store(client, headers, city_id, store_name="测试门店"):
    resp = client.post("/api/v1/admin/stores", json={
        "city_id": city_id, "store_name": store_name,
        "province": "测试省", "city": "测试市", "district": "测试区",
        "address": "测试地址1号", "phone": "020-00000000",
    }, headers=headers)
    assert resp.status_code == 201, f"创建门店失败: {resp.text}"
    return resp.json()["id"]


def _create_user(client, admin_headers, username, password, role,
                 city_id=None, store_id=None):
    payload = {"username": username, "password": password, "role": role}
    if city_id is not None:
        payload["city_id"] = city_id
    if store_id is not None:
        payload["store_id"] = store_id
    resp = client.post("/api/v1/admin/users", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201), f"创建用户失败: {resp.text}"
    return resp.json()


def _login(client, username, password):
    resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ═══════════════════════════════════════════════════════════
# Fix 1：store_manager 更新门店字段白名单
# ═══════════════════════════════════════════════════════════

class TestFix1StoreManagerFields:
    """store_manager 只能改基础展示字段，受保护字段被忽略或 403。"""

    @pytest.fixture(autouse=True)
    def _setup(self, client, auth_headers):
        self.city_id = _create_city(client, auth_headers, name="字段测试城市", slug="field-test-city")
        self.store_id = _create_store(client, auth_headers, self.city_id, "字段测试门店")
        _create_user(client, auth_headers, "sm_fields", "SecureSm123!", "store_manager", store_id=self.store_id)
        self.sm_headers = _login(client, "sm_fields", "SecureSm123!")

    def test_store_manager_can_update_allowed_field(self, client):
        """store_manager 改 store_name（白名单字段）→ 200。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "store_name": "新门店名",
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        assert resp.json()["store_name"] == "新门店名"

    def test_store_manager_can_update_address_and_phone(self, client):
        """store_manager 改 address/phone/opening_hours（白名单）→ 200。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "address": "新地址99号",
            "phone": "020-99999999",
            "opening_hours": "09:00-21:00",
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        assert resp.json()["address"] == "新地址99号"
        assert resp.json()["phone"] == "020-99999999"

    def test_store_manager_is_active_ignored(self, client):
        """store_manager 改 is_active（受保护）→ 字段被忽略，门店仍 active。"""
        # 先确认初始状态
        before = client.get(f"/api/v1/admin/stores", headers=self.sm_headers).json()["items"][0]
        assert before["is_active"] is True

        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "is_active": False,
            "store_name": "合法改名",  # 混入一个白名单字段避免 403
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        # is_active 被忽略，仍为 True
        assert resp.json()["is_active"] is True
        # store_name 生效
        assert resp.json()["store_name"] == "合法改名"

    def test_store_manager_status_ignored(self, client):
        """store_manager 改 status（受保护）→ 被忽略。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "status": "closed",
            "store_name": "改名2",
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        # status 被忽略，仍为 "active"
        assert resp.json()["status"] == "active"

    def test_store_manager_dealer_code_ignored(self, client):
        """store_manager 改 dealer_code（受保护）→ 被忽略。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "dealer_code": "D9999",
            "store_name": "改名3",
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        # dealer_code 被忽略（保持 null 或原值）
        assert resp.json()["dealer_code"] is None

    def test_store_manager_manager_user_id_ignored(self, client):
        """store_manager 改 manager_user_id（受保护）→ 被忽略。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "manager_user_id": 999,
            "store_name": "改名4",
        }, headers=self.sm_headers)
        assert resp.status_code == 200
        assert resp.json()["manager_user_id"] is None

    def test_store_manager_only_protected_fields_returns_403(self, client):
        """store_manager 只提交受保护字段（无白名单字段）→ 403。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "is_active": False,
            "status": "closed",
            "dealer_code": "D9999",
        }, headers=self.sm_headers)
        assert resp.status_code == 403

    def test_admin_can_update_protected_fields(self, client, auth_headers):
        """admin 可以改 is_active/sort_order 等受保护字段。"""
        resp = client.patch(f"/api/v1/admin/stores/{self.store_id}", json={
            "is_active": False,
            "sort_order": 99,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["sort_order"] == 99


# ═══════════════════════════════════════════════════════════
# Fix 2：subdomain 校验
# ═══════════════════════════════════════════════════════════

class TestFix2SubdomainValidation:
    """create/update 城市 subdomain 格式 + 保留字校验。"""

    def test_create_reserved_subdomain_admin(self, client, auth_headers):
        """subdomain=admin → 400。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "保留测试1", "slug": "reserved-test-1", "province": "测试省",
            "subdomain": "admin",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "保留子域名" in resp.json()["detail"]

    def test_create_reserved_subdomain_api(self, client, auth_headers):
        """subdomain=api → 400。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "保留测试2", "slug": "reserved-test-2", "province": "测试省",
            "subdomain": "api",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_reserved_subdomain_www(self, client, auth_headers):
        """subdomain=www → 400。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "保留测试3", "slug": "reserved-test-3", "province": "测试省",
            "subdomain": "www",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_invalid_subdomain_uppercase(self, client, auth_headers):
        """subdomain=Guangzhou（大写）→ 400 或 422（Pydantic 请求层拦截）。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "格式测试1", "slug": "format-test-1", "province": "测试省",
            "subdomain": "Guangzhou",
        }, headers=auth_headers)
        # 400（service 层）或 422（Pydantic 请求层）都算拒绝成功
        assert resp.status_code in (400, 422)

    def test_create_invalid_subdomain_special_chars(self, client, auth_headers):
        """subdomain 含特殊字符 → 400 或 422（Pydantic 请求层拦截）。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "格式测试2", "slug": "format-test-2", "province": "测试省",
            "subdomain": "guang_zhou",
        }, headers=auth_headers)
        assert resp.status_code in (400, 422)

    def test_create_valid_subdomain(self, client, auth_headers):
        """subdomain=guangzhou（合法）→ 201。"""
        resp = client.post("/api/v1/admin/cities", json={
            "name": "合法subdomain测试", "slug": "valid-sub-test", "province": "测试省",
            "subdomain": "guangzhou-city",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["subdomain"] == "guangzhou-city"

    def test_update_to_reserved_subdomain(self, client, auth_headers):
        """update 城市 subdomain=admin → 400。"""
        city_id = _create_city(client, auth_headers, name="更新保留测试", slug="upd-reserved-test")
        resp = client.patch(f"/api/v1/admin/cities/{city_id}", json={
            "subdomain": "admin",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "保留子域名" in resp.json()["detail"]

    def test_update_to_invalid_subdomain(self, client, auth_headers):
        """update 城市 subdomain 含特殊字符 → 400。"""
        city_id = _create_city(client, auth_headers, name="更新格式测试", slug="upd-format-test")
        resp = client.patch(f"/api/v1/admin/cities/{city_id}", json={
            "subdomain": "Bad_Name!",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_update_to_valid_subdomain(self, client, auth_headers):
        """update 城市 subdomain=合法值 → 200。"""
        city_id = _create_city(client, auth_headers, name="更新合法测试", slug="upd-valid-test")
        resp = client.patch(f"/api/v1/admin/cities/{city_id}", json={
            "subdomain": "new-valid-sub",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["subdomain"] == "new-valid-sub"


# ═══════════════════════════════════════════════════════════
# Fix 3：公开城市接口强制 active_only=true
# ═══════════════════════════════════════════════════════════

class TestFix3PublicApiLockedDown:
    """公开 /api/v1/cities 永远只返回 published 城市。"""

    def test_public_list_ignores_active_only_param(self, client, auth_headers):
        """传 active_only=false 也无效，仍只返回 published 城市。"""
        _create_city(client, auth_headers, name="公开发布城市", slug="pub-locked-test",
                     content_status="published")
        _create_city(client, auth_headers, name="公开草稿城市", slug="draft-locked-test",
                     content_status="draft")

        # 无论传不传 active_only，公开列表都只有 published
        r1 = client.get("/api/v1/cities").json()
        r2 = client.get("/api/v1/cities?active_only=false").json()
        r3 = client.get("/api/v1/cities?active_only=true").json()

        slugs1 = {c["slug"] for c in r1["items"]}
        slugs2 = {c["slug"] for c in r2["items"]}
        slugs3 = {c["slug"] for c in r3["items"]}

        # 三次请求结果一致：包含 published，不含 draft
        assert slugs1 == slugs2 == slugs3
        assert "pub-locked-test" in slugs1
        assert "draft-locked-test" not in slugs1

    def test_admin_list_returns_all_cities(self, client, auth_headers):
        """/api/v1/admin/cities 返回所有城市（含 draft）。"""
        _create_city(client, auth_headers, name="后台发布", slug="admin-pub-test",
                     content_status="published")
        _create_city(client, auth_headers, name="后台草稿", slug="admin-draft-test",
                     content_status="draft")

        resp = client.get("/api/v1/admin/cities", headers=auth_headers)
        assert resp.status_code == 200
        slugs = {c["slug"] for c in resp.json()["items"]}
        assert "admin-pub-test" in slugs
        assert "admin-draft-test" in slugs

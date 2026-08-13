"""多城市二级域名 + 总部后台闭环修复测试。

覆盖：
- Fix 1：公开城市页遵守发布状态（draft 城市 404，unpublish 后公开 404 + admin 可见）
- Fix 2：store_manager 权限收紧（只看自己门店、不能创建、不能 set-primary）
- Fix 5：留资门店归因校验（跨城市门店拒绝）

注意：不依赖 lifespan 种子数据，全部通过 admin API 自建。
"""
import pytest


# ── 辅助函数 ──────────────────────────────────────────────

def _create_city(client, headers, name="测试城市A", slug="test-city-a",
                 content_status="published", is_active=True, has_store=True):
    """通过 admin API 创建城市，返回 city_id。"""
    resp = client.post("/api/v1/admin/cities", json={
        "name": name, "slug": slug, "province": "测试省",
        "is_active": is_active, "content_status": content_status,
        "has_store": has_store,
    }, headers=headers)
    assert resp.status_code == 201, f"创建城市失败: {resp.text}"
    return resp.json()["id"]


def _create_store(client, headers, city_id, store_name="测试门店", district="测试区"):
    """通过 admin API 创建门店，返回 store_id。"""
    resp = client.post("/api/v1/admin/stores", json={
        "city_id": city_id,
        "store_name": store_name,
        "province": "测试省", "city": "测试市", "district": district,
        "address": "测试地址123号", "phone": "020-00000000",
    }, headers=headers)
    assert resp.status_code == 201, f"创建门店失败: {resp.text}"
    return resp.json()["id"]


def _create_user(client, admin_headers, username, password, role,
                 city_id=None, store_id=None, dealer_code=None):
    """通过 admin API 创建用户。"""
    payload = {"username": username, "password": password, "role": role}
    if city_id is not None:
        payload["city_id"] = city_id
    if store_id is not None:
        payload["store_id"] = store_id
    if dealer_code:
        payload["dealer_code"] = dealer_code
    resp = client.post("/api/v1/admin/users", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201), f"创建用户失败: {resp.text}"
    return resp.json()


def _login(client, username, password):
    """登录获取 auth headers。"""
    resp = client.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ═══════════════════════════════════════════════════════════
# Fix 1：公开城市页遵守发布状态
# ═══════════════════════════════════════════════════════════

class TestFix1PublishStatus:
    """公开 API 只返回 is_active=true 且 content_status=published 的城市。"""

    def test_public_list_excludes_draft(self, client, auth_headers):
        """active_only=true 不返回 draft 城市，但包含 published 城市。"""
        pub_id = _create_city(client, auth_headers, name="发布城市", slug="pub-city-1",
                              content_status="published")
        _create_city(client, auth_headers, name="草稿城市", slug="draft-city-1",
                     content_status="draft")

        public = client.get("/api/v1/cities?active_only=true").json()
        slugs = [c["slug"] for c in public["items"]]
        assert "pub-city-1" in slugs
        assert "draft-city-1" not in slugs

    def test_draft_city_detail_404(self, client, auth_headers):
        """公开详情接口对 draft 城市返回 404。"""
        _create_city(client, auth_headers, name="草稿详情", slug="draft-detail-1",
                     content_status="draft")

        resp = client.get("/api/v1/cities/draft-detail-1")
        assert resp.status_code == 404

    def test_published_city_detail_200(self, client, auth_headers):
        """公开详情接口对 published 城市返回 200。"""
        _create_city(client, auth_headers, name="已发布", slug="pub-detail-1",
                     content_status="published")

        resp = client.get("/api/v1/cities/pub-detail-1")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "pub-detail-1"

    def test_unpublish_public_404_admin_visible(self, client, auth_headers):
        """unpublish 后公开接口 404，后台接口仍可见（content_status=draft）。"""
        city_id = _create_city(client, auth_headers, name="下架测试", slug="unpub-test-1",
                               content_status="published")

        # 公开接口可见
        assert client.get("/api/v1/cities/unpub-test-1").status_code == 200

        # 下架
        resp = client.post(f"/api/v1/admin/cities/{city_id}/unpublish", headers=auth_headers)
        assert resp.status_code == 200

        # 公开接口 404
        assert client.get("/api/v1/cities/unpub-test-1").status_code == 404

        # 后台接口仍可见
        admin_detail = client.get(f"/api/v1/admin/cities/{city_id}", headers=auth_headers)
        assert admin_detail.status_code == 200
        assert admin_detail.json()["content_status"] == "draft"


# ═══════════════════════════════════════════════════════════
# Fix 2：store_manager 权限收紧
# ═══════════════════════════════════════════════════════════

class TestFix2RBAC:
    """store_manager 只能看/改自己 store_id；不能创建门店、不能 set-primary。"""

    @pytest.fixture(autouse=True)
    def _setup_data(self, client, auth_headers):
        """创建两个城市 + 门店 + 各角色用户。"""
        # 城市 A（广州代替）+ 2 个门店
        self.city_a_id = _create_city(client, auth_headers, name="城市甲", slug="city-a-1")
        self.store_a1_id = _create_store(client, auth_headers, self.city_a_id, "门店甲1", "区域1")
        self.store_a2_id = _create_store(client, auth_headers, self.city_a_id, "门店甲2", "区域2")

        # 城市 B + 1 个门店
        self.city_b_id = _create_city(client, auth_headers, name="城市乙", slug="city-b-1")
        self.store_b1_id = _create_store(client, auth_headers, self.city_b_id, "门店乙1", "区域3")

        # city_manager：绑定城市甲
        _create_user(client, auth_headers, "cm_test", "SecureCm123!", "city_manager", city_id=self.city_a_id)
        self.cm_headers = _login(client, "cm_test", "SecureCm123!")

        # store_manager：绑定门店甲1
        _create_user(client, auth_headers, "sm_test", "SecureSm123!", "store_manager", store_id=self.store_a1_id)
        self.sm_headers = _login(client, "sm_test", "SecureSm123!")

        # dealer
        _create_user(client, auth_headers, "dealer_test2", "SecureDealer1!", "dealer", dealer_code="D2026004")
        self.dealer_headers = _login(client, "dealer_test2", "SecureDealer1!")

    def test_store_manager_only_sees_own_store(self, client):
        """store_manager GET /admin/stores 只返回自己的 store_id。"""
        resp = client.get("/api/v1/admin/stores", headers=self.sm_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == self.store_a1_id

    def test_store_manager_cannot_create_store(self, client):
        """store_manager POST /admin/stores 返回 403。"""
        resp = client.post("/api/v1/admin/stores", json={
            "city_id": self.city_a_id,
            "store_name": "非法新建",
            "province": "测试省", "city": "测试市", "district": "区域",
            "address": "测试", "phone": "020-00000000",
        }, headers=self.sm_headers)
        assert resp.status_code == 403

    def test_store_manager_cannot_set_primary(self, client):
        """store_manager POST /admin/stores/{id}/set-primary 返回 403。"""
        resp = client.post(f"/api/v1/admin/stores/{self.store_a1_id}/set-primary",
                           headers=self.sm_headers)
        assert resp.status_code == 403

    def test_city_manager_lists_own_city_stores(self, client):
        """city_manager GET /admin/stores 只返回自己城市的门店。"""
        resp = client.get("/api/v1/admin/stores", headers=self.cm_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2  # 城市甲有 2 个门店
        for item in items:
            assert item["city_id"] == self.city_a_id

    def test_city_manager_can_create_store(self, client):
        """city_manager 可以在自己城市创建门店。"""
        resp = client.post("/api/v1/admin/stores", json={
            "city_id": self.city_a_id,
            "store_name": "cm新建门店",
            "province": "测试省", "city": "测试市", "district": "区域4",
            "address": "测试路", "phone": "020-11111111",
        }, headers=self.cm_headers)
        assert resp.status_code == 201

    def test_city_manager_cannot_create_other_city_store(self, client):
        """city_manager 不能在其它城市创建门店。"""
        resp = client.post("/api/v1/admin/stores", json={
            "city_id": self.city_b_id,
            "store_name": "跨城市",
            "province": "测试省", "city": "测试市", "district": "区域",
            "address": "测试", "phone": "020-00000000",
        }, headers=self.cm_headers)
        assert resp.status_code == 403

    def test_dealer_cannot_access_admin(self, client):
        """dealer GET /admin/cities 返回 403。"""
        resp = client.get("/api/v1/admin/cities", headers=self.dealer_headers)
        assert resp.status_code == 403

    def test_admin_can_list_all_stores(self, client, auth_headers):
        """admin 可以看到所有门店。"""
        resp = client.get("/api/v1/admin/stores", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3


# ═══════════════════════════════════════════════════════════
# Fix 5：留资门店归因校验
# ═══════════════════════════════════════════════════════════

class TestFix5LeadAttribution:
    """city_id + preferred_store_id 必须属于同一城市，否则 400。"""

    @pytest.fixture(autouse=True)
    def _setup_data(self, client, auth_headers):
        """创建两个城市 + 门店。"""
        self.city_a_id = _create_city(client, auth_headers, name="留资城市甲", slug="lead-city-a")
        self.store_a_id = _create_store(client, auth_headers, self.city_a_id, "留资门店甲")

        self.city_b_id = _create_city(client, auth_headers, name="留资城市乙", slug="lead-city-b")
        self.store_b_id = _create_store(client, auth_headers, self.city_b_id, "留资门店乙")

    def test_cross_city_store_rejected(self, client):
        """city_id=城市甲 + preferred_store_id=城市乙门店 → 400。"""
        resp = client.post("/api/v1/cities/leads", json={
            "name": "跨城市测试",
            "phone": "13800001111",
            "city_id": self.city_a_id,
            "preferred_store_id": self.store_b_id,
            "interest": "防盗门",
        })
        assert resp.status_code == 400
        assert "跨城市" in resp.json()["detail"]

    def test_same_city_store_accepted(self, client):
        """city_id=城市甲 + preferred_store_id=城市甲门店 → 200。"""
        resp = client.post("/api/v1/cities/leads", json={
            "name": "同城测试",
            "phone": "13800002222",
            "city_id": self.city_a_id,
            "preferred_store_id": self.store_a_id,
            "interest": "防盗门",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    def test_no_store_id_uses_default(self, client):
        """只传 city_id，不传 preferred_store_id → 自动分配。"""
        resp = client.post("/api/v1/cities/leads", json={
            "name": "自动分配测试",
            "phone": "13800003333",
            "city_id": self.city_a_id,
            "interest": "阳台封窗",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

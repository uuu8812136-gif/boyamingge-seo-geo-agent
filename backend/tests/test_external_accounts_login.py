"""外部账号扫码登录与发布任务前置校验测试。

覆盖：
- 平台能力清单返回 verified/beta/planned 三档
- 扫码确认后精准回写发起扫码的账号（不串号）
- 同平台多账号扫码不会互相覆盖
- planned 平台禁止创建发布任务
- 缺少 internal_account_id 时立即发布被拒绝
"""
from datetime import datetime, timezone
from types import SimpleNamespace


def _make_account(client, headers, platform="xiaohongshu", name="测试账号A"):
    resp = client.post(
        "/api/v1/external-accounts",
        json={"platform": platform, "display_name": name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _mock_synapse(monkeypatch, confirmed_account_id: str, user_info: dict | None = None):
    """mock EmbeddedSynapseService，模拟扫码确认成功。

    confirmed_account_id: start_login 传入的 account_id，poll 时原样返回。
    """
    fake_user = user_info or {"user_id": "plat-123", "name": "小红书用户", "avatar": "https://x.com/a.png"}

    class FakeSvc:
        def __init__(self):
            self.saved_cookie_path = f"/tmp/cookie_{confirmed_account_id}.json"

        def start_login(self, platform, account_id=None):
            return {
                "session_id": "sess-fake-001",
                "platform": platform,
                "account_id": account_id or "temp",
                "qr_image": "data:image/png;base64,AAA",
                "qr_url": "https://x.com/qr",
                "expires_in": 300,
            }

        def poll_login_status(self, session_id):
            return {
                "status": "confirmed",
                "message": "登录成功",
                "platform": "xiaohongshu",
                "account_id": confirmed_account_id,
                "user_info": fake_user,
                "saved": True,
            }

        def get_account_cookie_path(self, platform, account_id):
            return self.saved_cookie_path

        def validate_account_cookie(self, platform, account_id):
            return {"valid": True}

        def delete_account_cookie(self, platform, account_id):
            return True

    import app.api.v1.external_accounts as mod
    monkeypatch.setattr("app.integrations.synapse_engine.EmbeddedSynapseService", FakeSvc)
    # 同时 patch 外部账号模块里延迟导入的路径
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "app.integrations.synapse_engine":
            return SimpleNamespace(EmbeddedSynapseService=FakeSvc)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    return FakeSvc


def test_platform_capabilities_returns_tiers(client, auth_headers):
    """平台能力清单包含 verified/beta/planned 三档。"""
    resp = client.get("/api/v1/external-accounts/platforms", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    by_name = {p["name"]: p for p in items}
    assert by_name["xiaohongshu"]["tier"] == "beta"
    assert by_name["xiaohongshu"]["can_publish"] is True
    assert by_name["baijiahao"]["tier"] == "beta"
    assert by_name["zhihu"]["tier"] == "beta"
    assert by_name["douyin"]["tier"] == "planned"
    assert by_name["douyin"]["can_publish"] is False
    assert by_name["bilibili"]["can_publish"] is False


def test_scan_login_writes_back_correct_account(client, auth_headers, monkeypatch):
    """扫码确认后精准回写发起扫码的账号。"""
    account = _make_account(client, auth_headers, name="账号A")
    _mock_synapse(monkeypatch, confirmed_account_id=str(account["id"]))

    # 启动扫码登录
    resp = client.post(f"/api/v1/external-accounts/{account['id']}/login", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["account_id"] == account["id"]

    # 轮询登录状态
    resp = client.get(
        "/api/v1/external-accounts/login/status?session_id=sess-fake-001",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["account_id"] == account["id"]
    assert body["internal_account_id"] == str(account["id"])

    # 验证 DB 已回写
    resp = client.get("/api/v1/external-accounts", headers=auth_headers)
    items = resp.json()["items"]
    target = [a for a in items if a["id"] == account["id"]][0]
    assert target["cookie_status"] == "active"
    assert target["internal_account_id"] == str(account["id"])
    assert target["user_id"] == "plat-123"
    assert target["avatar"] == "https://x.com/a.png"
    assert target["last_login_at"] is not None


def test_same_platform_multiple_accounts_no_crosstalk(client, auth_headers, monkeypatch):
    """同平台多账号扫码不会串号：只更新发起扫码的那个。"""
    account_a = _make_account(client, auth_headers, name="账号A")
    account_b = _make_account(client, auth_headers, name="账号B")

    # 只对 account_b 发起扫码
    _mock_synapse(monkeypatch, confirmed_account_id=str(account_b["id"]))

    client.post(f"/api/v1/external-accounts/{account_b['id']}/login", headers=auth_headers)
    client.get(
        "/api/v1/external-accounts/login/status?session_id=sess-fake-001",
        headers=auth_headers,
    )

    resp = client.get("/api/v1/external-accounts", headers=auth_headers)
    items = {a["id"]: a for a in resp.json()["items"]}

    # account_b 被回写为 active
    assert items[account_b["id"]]["cookie_status"] == "active"
    assert items[account_b["id"]]["internal_account_id"] == str(account_b["id"])
    # account_a 保持 missing_cookie，未被串号
    assert items[account_a["id"]]["cookie_status"] == "missing_cookie"
    assert items[account_a["id"]]["internal_account_id"] is None


def test_planned_platform_rejects_task_creation(client, auth_headers):
    """planned 平台禁止创建发布任务。"""
    # 先创建一条内容用于发布
    content_resp = client.post(
        "/api/v1/content/posts",
        json={"title": "测试内容", "markdown": "正文", "city": "广州"},
        headers=auth_headers,
    )
    content_id = content_resp.json()["id"]

    # 创建抖音账号
    acct_resp = client.post(
        "/api/v1/external-accounts",
        json={"platform": "douyin", "display_name": "抖音号"},
        headers=auth_headers,
    )
    account_id = acct_resp.json()["id"]

    # 尝试创建抖音发布任务 → 应被拒绝
    resp = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content_id,
            "platform": "douyin",
            "account_id": account_id,
            "publish_mode": "direct",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "待接入" in resp.json()["detail"]


def test_publish_task_rejected_without_internal_account_id(client, auth_headers):
    """账号未扫码登录（缺 internal_account_id）时立即发布被拒绝。"""
    content_resp = client.post(
        "/api/v1/content/posts",
        json={"title": "测试内容", "markdown": "正文", "city": "广州"},
        headers=auth_headers,
    )
    content_id = content_resp.json()["id"]

    # 创建小红书账号但不扫码登录
    acct_resp = client.post(
        "/api/v1/external-accounts",
        json={"platform": "xiaohongshu", "display_name": "未登录账号"},
        headers=auth_headers,
    )
    account_id = acct_resp.json()["id"]

    resp = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content_id,
            "platform": "xiaohongshu",
            "account_id": account_id,
            "publish_mode": "direct",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "扫码登录" in resp.json()["detail"]

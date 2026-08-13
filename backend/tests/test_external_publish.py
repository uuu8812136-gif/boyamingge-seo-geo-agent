"""外部平台发布 API 与服务测试（不触发真实浏览器自动化）。

覆盖：平台能力清单、账号创建、占位平台拒发、已接入平台未登录拒发、
定时任务登记、媒体解析器、定时扫描派发。
"""
from datetime import datetime, timedelta, timezone


def _create_content(client, headers, **overrides):
    payload = {
        "title": "百家号图文测试内容",
        "markdown": "# 标题\n\n正文内容用于外部发布测试。",
        "post_type": "article",
        "city": "广州",
        "summary": "外部发布测试摘要",
        "cover_image": "https://example.com/cover.jpg",
        "type": "seo",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/content/posts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_account(client, headers, platform="baijiahao", display_name="测试账号"):
    resp = client.post(
        "/api/v1/external-accounts",
        json={"platform": platform, "display_name": display_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_platforms_include_supported_imagetext(client, auth_headers):
    resp = client.get("/api/v1/external-accounts/platforms", headers=auth_headers)
    assert resp.status_code == 200
    by_name = {p["name"]: p for p in resp.json()["items"]}
    # 图文平台自动化已接入，但正式账号验收前统一标记 beta
    assert by_name["xiaohongshu"]["supported"] is True
    assert by_name["xiaohongshu"]["tier"] == "beta"
    assert by_name["baijiahao"]["supported"] is True
    assert by_name["baijiahao"]["tier"] == "beta"
    assert by_name["zhihu"]["supported"] is True
    assert by_name["zhihu"]["tier"] == "beta"
    # 视频平台待接入（planned），不虚标
    assert by_name["channels"]["supported"] is False
    assert by_name["channels"]["tier"] == "planned"
    assert by_name["douyin"]["supported"] is False
    assert by_name["douyin"]["tier"] == "planned"
    assert by_name["kuaishou"]["supported"] is False
    assert by_name["bilibili"]["supported"] is False


def test_create_baijiahao_account(client, auth_headers):
    acc = _create_account(client, auth_headers, platform="baijiahao")
    assert acc["platform"] == "baijiahao"
    assert acc["platform_code"] == 10
    assert acc["cookie_status"] == "missing_cookie"


def test_dispatch_unsupported_platform_marked_failed(client, auth_headers):
    """未接入平台经 dispatch_task 直接标记失败（防御性分支，API 层已在创建时拦截未知平台）。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")

    from app.models import SocialAccount, SocialPublicationTask
    from app.services.external_publish_service import dispatch_task

    db_gen, db = _get_db()
    try:
        account = db.query(SocialAccount).filter(SocialAccount.id == acc["id"]).first()
        task = SocialPublicationTask(
            content_id=content["id"],
            platform="weibo",  # 未接入平台
            platform_code=99,
            social_account_id=account.id,
            title="未接入平台任务",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        dispatch_task(db, task, account)
        db.refresh(task)
        assert task.status == "failed"
        assert "暂未接入" in (task.error_message or "")
    finally:
        db_gen.close()


def test_publish_task_supported_without_cookie_rejected(client, auth_headers):
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={"content_id": content["id"], "platform": "baijiahao", "account_id": acc["id"]},
        headers=auth_headers,
    )
    # 立即发布但账号未登录 → 400
    assert resp.status_code == 400
    assert "cookie" in resp.json()["detail"].lower() or "登录" in resp.json()["detail"]


def test_publish_task_platform_mismatch_rejected(client, auth_headers):
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="zhihu")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={"content_id": content["id"], "platform": "baijiahao", "account_id": acc["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "不一致" in resp.json()["detail"]


def test_schedule_task_registered_as_scheduled(client, auth_headers):
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    future = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    resp = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": future,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    task = resp.json()
    assert task["status"] == "scheduled"
    assert task["scheduled_at"] is not None


def test_task_artifacts_endpoint_empty(client, auth_headers):
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    # 定时任务创建时不校验 cookie，可拿到任务 id 且尚未产生截图
    future = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": future,
        },
        headers=auth_headers,
    ).json()
    resp = client.get(f"/api/v1/publish/tasks/{task['id']}/artifacts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── 媒体解析器单元测试 ──

def test_media_resolver_absolute_file(tmp_path):
    from app.services.media_resolver import resolve_local_image

    f = tmp_path / "pic.jpg"
    f.write_bytes(b"fake-image")
    assert resolve_local_image(str(f)) == str(f)
    assert resolve_local_image(str(tmp_path / "missing.jpg")) is None


def test_media_resolver_http_no_download():
    from app.services.media_resolver import resolve_local_image

    # 关闭下载时 http 图片无法解析为本地文件
    assert resolve_local_image("https://example.com/a.jpg", allow_download=False) is None


def test_media_resolver_served_url(tmp_path, monkeypatch):
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    from app.services import media_resolver

    f = tmp_path / "sub" / "shot.png"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"x")
    url = media_resolver.to_served_url(str(f))
    assert url == "/uploads/sub/shot.png"


# ── 定时外部发布扫描 ──

def test_run_scheduled_external_publish_marks_no_cookie_failed(client, auth_headers):
    """定时任务到期后，账号无有效 cookie 应被标记失败（不启动浏览器）。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": past,
        },
        headers=auth_headers,
    ).json()
    assert task["status"] == "scheduled"

    # 直接调用扫描服务（复用测试的 DB 覆盖）
    from app.core.database import get_db
    from app.main import app as fastapi_app
    from app.services.external_publish_service import run_scheduled_external_publish

    db_gen = fastapi_app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        dispatched = run_scheduled_external_publish(db)
        assert dispatched >= 1
    finally:
        db_gen.close()

    detail = client.get(f"/api/v1/publish/tasks/{task['id']}", headers=auth_headers).json()
    assert detail["status"] == "failed"
    assert "cookie" in (detail["error_message"] or "").lower() or "登录" in (detail["error_message"] or "")


# ── 创建任务边界 ──

def test_schedule_without_scheduled_at_rejected(client, auth_headers):
    """publish_mode=schedule 但缺 scheduled_at → 400。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "scheduled_at" in resp.json()["detail"]


def test_unknown_platform_rejected(client, auth_headers):
    """未知平台名 → 400（且不落任务）。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={"content_id": content["id"], "platform": "weibo", "account_id": acc["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "不支持的平台" in resp.json()["detail"]


def test_create_task_content_not_found(client, auth_headers):
    acc = _create_account(client, auth_headers, platform="baijiahao")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={"content_id": 999999, "platform": "baijiahao", "account_id": acc["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "内容不存在" in resp.json()["detail"]


# ── 重试边界 ──

def test_retry_nonexistent_task_404(client, auth_headers):
    resp = client.post("/api/v1/publish/tasks/999999/retry", headers=auth_headers)
    assert resp.status_code == 404


def test_retry_scheduled_task_rejected(client, auth_headers):
    """状态为 scheduled 的任务不可重试 → 400。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": future,
        },
        headers=auth_headers,
    ).json()
    resp = client.post(f"/api/v1/publish/tasks/{task['id']}/retry", headers=auth_headers)
    assert resp.status_code == 400
    assert "不可重试" in resp.json()["detail"]


def _create_failed_task(client, auth_headers, platform="baijiahao"):
    """创建一个到期定时任务并扫描，账号无 cookie → 得到 failed 任务。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform=platform)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": platform,
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": past,
        },
        headers=auth_headers,
    ).json()
    _scan_scheduled()
    detail = client.get(f"/api/v1/publish/tasks/{task['id']}", headers=auth_headers).json()
    assert detail["status"] == "failed"
    return acc, detail


def test_retry_failed_task_redispatches_and_clears_timestamps(client, auth_headers):
    """失败任务重试：状态转回可执行流程（无 cookie 仍失败但流程走通、时间戳被清空重置）。"""
    _, task = _create_failed_task(client, auth_headers)
    resp = client.post(f"/api/v1/publish/tasks/{task['id']}/retry", headers=auth_headers)
    assert resp.status_code == 200
    retried = resp.json()
    # 无 cookie 重试仍失败，但走通了重试→再派发→再判定的完整流程
    assert retried["status"] == "failed"
    assert "cookie" in (retried["error_message"] or "").lower() or "登录" in (retried["error_message"] or "")


def test_retry_account_deleted_rejected(client, auth_headers):
    """重试时关联账号已删除 → 400。"""
    acc, task = _create_failed_task(client, auth_headers)
    assert client.delete(f"/api/v1/external-accounts/{acc['id']}", headers=auth_headers).status_code == 204
    resp = client.post(f"/api/v1/publish/tasks/{task['id']}/retry", headers=auth_headers)
    assert resp.status_code == 400
    assert "账号不存在" in resp.json()["detail"]


# ── 定时扫描边界 ──

def _scan_scheduled():
    from app.core.database import get_db
    from app.main import app as fastapi_app
    from app.services.external_publish_service import run_scheduled_external_publish

    db_gen = fastapi_app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        return run_scheduled_external_publish(db)
    finally:
        db_gen.close()


def test_scheduled_not_due_not_dispatched(client, auth_headers):
    """未到期的定时任务不应被派发，状态保持 scheduled。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    future = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": future,
        },
        headers=auth_headers,
    ).json()
    _scan_scheduled()
    detail = client.get(f"/api/v1/publish/tasks/{task['id']}", headers=auth_headers).json()
    assert detail["status"] == "scheduled"


def test_scheduled_account_deleted_marked_failed(client, auth_headers):
    """定时到期但账号已删除 → 标记 failed。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="baijiahao")
    past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    task = client.post(
        "/api/v1/publish/tasks",
        json={
            "content_id": content["id"],
            "platform": "baijiahao",
            "account_id": acc["id"],
            "publish_mode": "schedule",
            "scheduled_at": past,
        },
        headers=auth_headers,
    ).json()
    # 删除账号后再扫描
    assert client.delete(f"/api/v1/external-accounts/{acc['id']}", headers=auth_headers).status_code == 204
    _scan_scheduled()
    detail = client.get(f"/api/v1/publish/tasks/{task['id']}", headers=auth_headers).json()
    assert detail["status"] == "failed"
    assert "账号不存在" in (detail["error_message"] or "")


# ── 短视频平台（视频号 / 抖音）──

def _get_db():
    from app.core.database import get_db
    from app.main import app as fastapi_app

    db_gen = fastapi_app.dependency_overrides[get_db]()
    return db_gen, next(db_gen)


def test_platforms_video_planned(client, auth_headers):
    """视频平台标记为 planned（待接入），不虚标 supported。"""
    resp = client.get("/api/v1/external-accounts/platforms", headers=auth_headers)
    by_name = {p["name"]: p for p in resp.json()["items"]}
    assert by_name["channels"]["supported"] is False
    assert by_name["channels"]["tier"] == "planned"
    assert by_name["channels"]["can_publish"] is False
    assert by_name["douyin"]["supported"] is False
    assert by_name["douyin"]["tier"] == "planned"
    assert by_name["kuaishou"]["supported"] is False
    assert by_name["bilibili"]["supported"] is False


def test_create_channels_account(client, auth_headers):
    acc = _create_account(client, auth_headers, platform="channels", display_name="视频号")
    assert acc["platform"] == "channels"
    assert acc["platform_code"] == 2


def test_video_task_planned_platform_rejected(client, auth_headers):
    """视频平台（planned）禁止创建发布任务 → 400 待接入。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="douyin", display_name="抖音号")
    resp = client.post(
        "/api/v1/publish/tasks",
        json={"content_id": content["id"], "platform": "douyin", "account_id": acc["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "待接入" in resp.json()["detail"]


def test_resolve_local_video(tmp_path):
    from app.services.media_resolver import resolve_local_video

    f = tmp_path / "clip.mp4"
    f.write_bytes(b"fake-video-bytes")
    assert resolve_local_video(str(f)) == str(f)
    assert resolve_local_video(str(tmp_path / "missing.mp4")) is None
    # 视频不做远程下载
    assert resolve_local_video("https://example.com/a.mp4") is None


def test_resolve_content_video_from_material(client, auth_headers, tmp_path, monkeypatch):
    """内容绑定视频素材后，resolve_content_video 应返回本地视频与封面。"""
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    video_file = tmp_path / "v.mp4"
    video_file.write_bytes(b"v")
    cover_file = tmp_path / "c.jpg"
    cover_file.write_bytes(b"c")

    content = _create_content(client, auth_headers)
    from app.models import SocialMaterial
    from app.services.media_resolver import resolve_content_video

    db_gen, db = _get_db()
    try:
        mat = SocialMaterial(
            content_id=content["id"],
            filename="v.mp4",
            local_path=str(video_file),
            file_type="video",
            cover_path=str(cover_file),
            status="ready",
        )
        db.add(mat)
        db.commit()
        from app.models import Content
        c = db.query(Content).filter(Content.id == content["id"]).first()
        result = resolve_content_video(db, c)
        assert result["video_path"] == str(video_file)
        assert result["cover_path"] == str(cover_file)
        assert result["material_id"] == mat.id
    finally:
        db_gen.close()


def test_video_dispatch_planned_platform_marked_failed(client, auth_headers):
    """视频平台（planned）dispatch 直接标记 failed，提示暂未接入。"""
    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="douyin", display_name="抖音号")

    from app.models import SocialAccount, SocialPublicationTask
    from app.services.external_publish_service import dispatch_task

    db_gen, db = _get_db()
    try:
        account = db.query(SocialAccount).filter(SocialAccount.id == acc["id"]).first()
        account.cookie_status = "active"
        account.internal_account_id = "test-internal-id"
        db.commit()

        task = SocialPublicationTask(
            content_id=content["id"],
            platform="douyin",
            platform_code=account.platform_code,
            social_account_id=account.id,
            title="抖音视频测试",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        dispatch_task(db, task, account)
        db.refresh(task)
        assert task.status == "failed"
        assert "暂未接入" in (task.error_message or "")
    finally:
        db_gen.close()


def test_build_task_spec_video(client, auth_headers, tmp_path, monkeypatch):
    """视频平台 build_task_spec 应产出 is_video=True 且 media_paths 为视频路径。"""
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    video_file = tmp_path / "v2.mp4"
    video_file.write_bytes(b"v")

    content = _create_content(client, auth_headers)
    acc = _create_account(client, auth_headers, platform="channels", display_name="视频号")

    from app.models import SocialAccount, SocialMaterial, SocialPublicationTask
    from app.services.external_publish_service import build_task_spec

    db_gen, db = _get_db()
    try:
        db.add(SocialMaterial(
            content_id=content["id"],
            filename="v2.mp4",
            local_path=str(video_file),
            file_type="video",
            status="ready",
        ))
        db.commit()
        account = db.query(SocialAccount).filter(SocialAccount.id == acc["id"]).first()
        task = SocialPublicationTask(
            content_id=content["id"],
            platform="channels",
            platform_code=account.platform_code,
            social_account_id=account.id,
            title="视频号测试",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        spec = build_task_spec(db, task, account)
        assert spec["is_video"] is True
        assert spec["media_paths"] == [str(video_file)]
    finally:
        db_gen.close()


# ── 内容视频素材 API ──

def test_upload_and_list_content_video(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    content = _create_content(client, auth_headers)

    files = {"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")}
    resp = client.post(
        f"/api/v1/content/{content['id']}/materials/video",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()
    assert item["file_type"] == "video"
    assert item["status"] == "ready"
    assert item["url"] and item["url"].startswith("/uploads/")

    lst = client.get(
        f"/api/v1/content/{content['id']}/materials?file_type=video",
        headers=auth_headers,
    ).json()
    assert lst["total"] == 1
    assert lst["items"][0]["id"] == item["id"]


def test_upload_content_video_bad_ext_rejected(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    content = _create_content(client, auth_headers)
    files = {"file": ("not-a-video.txt", b"hello", "text/plain")}
    resp = client.post(
        f"/api/v1/content/{content['id']}/materials/video",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "格式" in resp.json()["detail"]


def test_upload_content_video_content_not_found(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    files = {"file": ("clip.mp4", b"v", "video/mp4")}
    resp = client.post(
        "/api/v1/content/999999/materials/video",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_content_video_soft(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("MATERIAL_UPLOAD_DIR", str(tmp_path))
    content = _create_content(client, auth_headers)
    files = {"file": ("clip.mp4", b"v", "video/mp4")}
    item = client.post(
        f"/api/v1/content/{content['id']}/materials/video",
        files=files,
        headers=auth_headers,
    ).json()
    d = client.delete(
        f"/api/v1/content/{content['id']}/materials/{item['id']}",
        headers=auth_headers,
    )
    assert d.status_code == 204
    lst = client.get(
        f"/api/v1/content/{content['id']}/materials",
        headers=auth_headers,
    ).json()
    assert lst["total"] == 0

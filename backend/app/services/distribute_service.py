import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Content, Publication
from app.schemas.publish import (
    AssistPackage,
    AssistPackageContent,
    AssistRequest,
    AssistResponse,
    DistributeRequest,
    DistributeResponse,
    DistributeTask,
)

settings = get_settings()

L1_PLATFORMS = {"baijiahao", "zhihu"}
L2_PLATFORMS = {"xiaohongshu", "douyin", "baidu_zhidao"}
L3_PLATFORMS = {"baidu_wenku", "baike", "wukong"}


def _expires_at(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def _is_distribute_demo() -> bool:
    return settings.distribute_mode == "mock" or "example.com" in settings.workbench_base_url


def distribute_l1(db: Session, payload: DistributeRequest) -> DistributeResponse:
    scenario = settings.mock_scenario

    # Scenario: error — 模拟分发服务异常
    if scenario == "error":
        raise RuntimeError("模拟分发服务异常：平台接口不可用")

    # Scenario: timeout — 模拟超时
    if scenario == "timeout":
        import time
        time.sleep(0.1)
        raise TimeoutError("模拟分发服务超时")

    # Scenario: publish_fail — 模拟发布失败
    if scenario == "publish_fail":
        tasks: list[DistributeTask] = []
        for platform in payload.platforms:
            tasks.append(
                DistributeTask(
                    platform=platform,
                    status="failed",
                    confirm_url=None,
                    expires_at=_expires_at(),
                    demo=True,
                )
            )
        return DistributeResponse(tasks=tasks)

    content = db.query(Content).filter(Content.id == payload.content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")

    tasks: list[DistributeTask] = []
    demo = _is_distribute_demo()
    for platform in payload.platforms:
        tier = "L1" if platform in L1_PLATFORMS else "L3" if platform in L3_PLATFORMS else "L1"
        token = secrets.token_urlsafe(8)
        confirm_url = None if demo else f"{settings.workbench_base_url}/confirm/{token}"
        expires = _expires_at()

        publication = Publication(
            content_id=content.id,
            platform=platform,
            tier=tier,
            url=confirm_url or f"demo://confirm/{token}",
            status="pending",
            published_at=None,
            dealer_id=payload.dealer_id,
        )
        db.add(publication)
        tasks.append(
            DistributeTask(
                platform=platform,
                status="pending",
                confirm_url=confirm_url,
                expires_at=expires,
                demo=demo,
            )
        )

    db.commit()
    return DistributeResponse(tasks=tasks)


def assist_l2(db: Session, payload: AssistRequest) -> AssistResponse:
    scenario = settings.mock_scenario

    # Scenario: error — 模拟素材包服务异常
    if scenario == "error":
        raise RuntimeError("模拟素材包服务异常：打包服务不可用")

    # Scenario: timeout — 模拟超时
    if scenario == "timeout":
        import time
        time.sleep(0.1)
        raise TimeoutError("模拟素材包服务超时")

    # Scenario: empty — 返回空素材包
    if scenario == "empty":
        return AssistResponse(packages=[])

    content = db.query(Content).filter(Content.id == payload.content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")

    packages: list[AssistPackage] = []
    title = content.markdown.split("\n")[0].replace("#", "").strip() or f"{content.city}门窗攻略"
    demo = _is_distribute_demo()

    for platform in payload.platforms:
        tier = "L2" if platform in L2_PLATFORMS else "L3"
        download_url = None if demo else f"{settings.packages_base_url}/{content.id}_{platform}.zip"
        body = content.markdown[:150] + "..." if len(content.markdown) > 150 else content.markdown

        publication = Publication(
            content_id=content.id,
            platform=platform,
            tier=tier,
            url=download_url or f"demo://package/{content.id}_{platform}.zip",
            status="package_ready",
            published_at=None,
        )
        db.add(publication)

        packages.append(
            AssistPackage(
                platform=platform,
                download_url=download_url,
                content=AssistPackageContent(
                    title=title,
                    body=body,
                    images=["/media/dealer_upload/img1.jpg"],
                ),
                demo=demo,
            )
        )

    db.commit()
    return AssistResponse(packages=packages)

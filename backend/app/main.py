from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import re
import tempfile
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import ROLE_ADMIN, ROLE_DEALER, ROLE_OPERATOR, get_password_hash
from app.models import AuditLog, City, CityCase, CityFaq, Content, Dealer, KnowledgeDocument, Lead, Material, Publication, Store
from app.models.user import User

settings = get_settings()

HTTP_REQUESTS = Counter(
    "boyamingge_http_requests_total",
    "HTTP requests handled by the API",
    ("method", "route", "status"),
)
HTTP_LATENCY = Histogram(
    "boyamingge_http_request_duration_seconds",
    "HTTP request latency",
    ("method", "route"),
)


def seed_dealers(db: Session) -> None:
    defaults = [
        ("广州经销商", "广州", "020-88880001"),
        ("深圳经销商", "深圳", "0755-88880002"),
        ("北京经销商", "北京", "010-88880003"),
    ]
    for name, city, phone in defaults:
        if not db.query(Dealer).filter(Dealer.city == city).first():
            db.add(Dealer(name=name, city=city, phone=phone, status="active", activation_score=80))
    db.commit()


def seed_users(db: Session) -> None:
    defaults = [
        ("admin", "admin123", ROLE_ADMIN, None),
        ("operator", "operator123", ROLE_OPERATOR, None),
        ("dealer_gz", "dealer123", ROLE_DEALER, "D2026001"),
        ("dealer_sz", "dealer123", ROLE_DEALER, "D2026002"),
        ("dealer_bj", "dealer123", ROLE_DEALER, "D2026003"),
    ]
    for username, password, role, dealer_code in defaults:
        if not db.query(User).filter(User.username == username).first():
            db.add(
                User(
                    username=username,
                    hashed_password=get_password_hash(password),
                    role=role,
                    dealer_code=dealer_code,
                )
            )
    db.commit()


def seed_leads(db: Session) -> None:
    if db.query(Lead).count() > 0:
        return
    defaults = [
        ("王女士", "13812345678", "广州", "防盗门", "website", "new"),
        ("李先生", "13987654321", "深圳", "断桥铝封阳台", "seo", "queued"),
        ("张先生", "13611112222", "北京", "隔音门窗", "website", "contacted"),
        ("陈女士", "13700001111", "广州", "阳台封窗", "seo", "new"),
        ("刘先生", "13822223333", "深圳", "旧窗改造", "website", "contacted"),
        ("赵女士", "13933334444", "北京", "防盗门安装", "seo", "converted"),
        ("孙先生", "13655556666", "广州", "断桥铝门窗", "website", "new"),
        ("周女士", "13777778888", "深圳", "隔音门窗", "seo", "queued"),
    ]
    for name, phone, city, interest, source, status in defaults:
        dealer = db.query(Dealer).filter(Dealer.city == city).first()
        dealer_code = f"D2026{dealer.id:03d}" if dealer else None
        db.add(
            Lead(
                name=name,
                phone=phone,
                city=city,
                interest=interest,
                source=source,
                dealer_id=dealer_code,
                status=status,
            )
        )
    db.commit()


# 经销商工作台 seed 内容 + 发布记录
SEED_CONTENTS = [
    # (city, type, markdown, eeat_score, eeat_breakdown, status, model_used)
    ("广州", "seo", "# 广州防盗门选购全攻略\n\n## 市场概况\n广州气候湿热，防盗门需兼顾防锈与密封。主流价位3000-8000元，具体以门店实测为准。\n\n## 型材与五金参数\n推荐壁厚1.8mm以上钢质门体，配合多点锁闭系统。五金件建议选择进口品牌，耐用性更佳。\n\n## 本地安装案例\n天河区某小区张先生选用博雅敏格甲级防盗门，安装周期2天，业主反馈隔音效果明显。\n\n## 价格区间\n- 入门级：3000-5000元\n- 中端：5000-8000元\n- 高端定制：8000元以上\n\n具体以门店实测为准。", 82, {"experience": 78, "expertise": 85, "authoritativeness": 70, "trustworthiness": 80}, "approved", "deepseek-v4-pro"),
    ("广州", "geo", "# 广州防盗门怎么选？\n\n广州选购防盗门应关注型材壁厚≥1.8mm、进口五金与本地安装团队资质。博雅敏格广州门店提供免费测量，价格以门店实测为准。", 75, {"experience": 70, "expertise": 78, "authoritativeness": 65, "trustworthiness": 75}, "approved", "deepseek-v4-flash"),
    ("广州", "seo", "# 广州阳台封窗注意事项\n\n## 封窗材料选择\n断桥铝为主流选择，兼顾隔热与强度，适合广州湿热气候。\n\n## 施工要点\n注意排水孔设置与密封处理，避免雨季渗漏。推拉窗需关注滑轨质量。\n\n## 物业审批\n多数小区需物业备案，博雅敏格可协助提供合规方案。", 78, {"experience": 72, "expertise": 80, "authoritativeness": 68, "trustworthiness": 78}, "approved", "deepseek-v4-pro"),
    ("深圳", "seo", "# 深圳断桥铝门窗选购指南\n\n## 深圳气候与型材选择\n深圳台风季需关注抗风压性能，推荐壁厚1.4mm以上断桥铝型材。\n\n## 玻璃与五金配置\n5+12A+5中空钢化玻璃可满足多数户型隔音隔热需求。\n\n## 南山封阳台案例\n南山区李女士全屋封阳台，选用博雅敏格70系列断桥铝，工期5天完成。", 80, {"experience": 75, "expertise": 82, "authoritativeness": 72, "trustworthiness": 80}, "approved", "deepseek-v4-pro"),
    ("深圳", "geo", "# 深圳断桥铝门窗价格多少？\n\n深圳断桥铝门窗推荐多腔体型材+中空钢化玻璃，兼顾隔音隔热。博雅敏格深圳门店支持封阳台、旧窗改造一站式服务。", 73, {"experience": 68, "expertise": 75, "authoritativeness": 62, "trustworthiness": 73}, "approved", "deepseek-v4-flash"),
    ("深圳", "seo", "# 深圳旧窗改造全流程\n\n## 评估阶段\n免费上门评估旧窗状况，确认是否需要整体拆除或可保留框架。\n\n## 方案确认\n根据户型与预算推荐方案，工期约3-5天。\n\n## 施工与验收\n专业团队施工，验收开关顺畅度、密封性与锁具功能。", 76, {"experience": 72, "expertise": 78, "authoritativeness": 65, "trustworthiness": 76}, "approved", "deepseek-v4-pro"),
    ("北京", "seo", "# 北京隔音门窗改造攻略\n\n## 北京冬季保温需求\n北京冬季温差大，门窗K值建议≤2.0，密封胶条需耐低温。\n\n## 旧窗改造流程\n免费评估→方案确认→拆除旧窗→安装新窗→验收，全程约3-5天。\n\n## 朝阳区改造案例\n朝阳区王先生老房换窗，选用博雅敏格80系列，冬季室温提升约2℃。", 81, {"experience": 78, "expertise": 83, "authoritativeness": 72, "trustworthiness": 80}, "approved", "deepseek-v4-pro"),
    ("北京", "geo", "# 北京冬季门窗如何保温？\n\n北京冬季保温推荐多腔体断桥铝+Low-E中空玻璃。旧窗改造可保留窗框结构，工期约3-5天，具体以门店实测为准。", 74, {"experience": 70, "expertise": 76, "authoritativeness": 63, "trustworthiness": 74}, "approved", "deepseek-v4-flash"),
    ("北京", "seo", "# 北京防盗门安装流程详解\n\n## 测量与方案\n上门测量洞口尺寸，确认开门方向与锁具配置。\n\n## 安装与验收\n专业团队安装，验收开关顺畅度、密封性与锁具功能。\n\n## 售后质保\n主体产品质保按国家标准及门店政策执行。", 77, {"experience": 73, "expertise": 80, "authoritativeness": 66, "trustworthiness": 77}, "approved", "deepseek-v4-pro"),
]

# 发布记录 seed：(content_idx, platform, tier, status, dealer_code)
SEED_PUBLICATIONS = [
    (0, "website", "L0", "published", None),
    (0, "baijiahao", "L1", "pending", "D2026001"),
    (0, "zhihu", "L1", "pending", "D2026001"),
    (1, "website", "L0", "published", None),
    (2, "website", "L0", "published", None),
    (2, "baijiahao", "L1", "confirmed", "D2026001"),
    (2, "xiaohongshu", "L2", "package_ready", "D2026001"),
    (3, "website", "L0", "published", None),
    (3, "baijiahao", "L1", "pending", "D2026002"),
    (3, "zhihu", "L1", "pending", "D2026002"),
    (4, "website", "L0", "published", None),
    (5, "website", "L0", "published", None),
    (5, "baijiahao", "L1", "confirmed", "D2026002"),
    (5, "douyin", "L2", "package_ready", "D2026002"),
    (6, "website", "L0", "published", None),
    (6, "baijiahao", "L1", "pending", "D2026003"),
    (6, "zhihu", "L1", "rejected", "D2026003"),
    (7, "website", "L0", "published", None),
    (8, "website", "L0", "published", None),
    (8, "baijiahao", "L1", "pending", "D2026003"),
    (8, "baidu_zhidao", "L2", "package_ready", "D2026003"),
]

SEED_MATERIALS = [
    ("D2026001", "image", "/uploads/demo_gz_case1.jpg", "yes", "2026-06-15 10:30"),
    ("D2026001", "image", "/uploads/demo_gz_case2.jpg", "yes", "2026-06-15 10:32"),
    ("D2026001", "image", "/uploads/demo_gz_door.jpg", "yes", "2026-06-16 14:20"),
    ("D2026002", "image", "/uploads/demo_sz_balcony.jpg", "yes", "2026-06-14 09:15"),
    ("D2026002", "image", "/uploads/demo_sz_window.jpg", "yes", "2026-06-14 09:18"),
    ("D2026003", "image", "/uploads/demo_bj_insulation.jpg", "yes", "2026-06-13 16:40"),
    ("D2026003", "image", "/uploads/demo_bj_door.jpg", "yes", "2026-06-13 16:45"),
]


def seed_contents_and_publications(db: Session) -> None:
    if db.query(Content).count() > 0:
        return
    content_ids = []
    for city, ctype, markdown, eeat, breakdown, status, model in SEED_CONTENTS:
        title_line = next((line for line in markdown.splitlines() if line.strip()), "演示内容")
        title = re.sub(r"^#{1,6}\s*", "", title_line).strip()[:500]
        content = Content(
            city=city,
            type=ctype,
            title=title,
            markdown=markdown,
            eeat_score=eeat,
            eeat_breakdown=breakdown,
            status="published",
            model_used=model,
            published_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
        )
        db.add(content)
        db.flush()
        content.slug = f"post-{content.id}"
        content_ids.append(content.id)
    db.commit()

    for content_idx, platform, tier, status, dealer_code in SEED_PUBLICATIONS:
        pub = Publication(
            content_id=content_ids[content_idx],
            platform=platform,
            tier=tier,
            url=f"https://example.com/p/{content_idx}" if status == "published" else None,
            status=status,
            published_at="2026-06-16T10:00:00Z" if status == "published" else None,
            dealer_id=dealer_code,
        )
        db.add(pub)
    db.commit()

    seed_materials(db)


def seed_materials(db: Session) -> None:
    if db.query(Material).count() > 0:
        return
    for dealer_code, mtype, url, copyright_declared, uploaded_at in SEED_MATERIALS:
        db.add(Material(
            dealer_id=dealer_code,
            type=mtype,
            oss_url=url,
            copyright_declared=copyright_declared,
            uploaded_at=uploaded_at,
        ))
    db.commit()


def seed_cities(db: Session) -> None:
    cities_data = [
        # ── 已有门店的 5 个城市 ──
        City(name="广州", slug="guangzhou", province="广东", lat=23.1291, lng=113.2644, is_active=True, has_store=True, content_status="published", subdomain="guangzhou",
             seo_title="广州门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格广州门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="广州门窗安装与旧窗改造", hero_subtitle="天河、越秀、海珠、番禺、白云、黄埔等区域可预约上门测量"),
        City(name="深圳", slug="shenzhen", province="广东", lat=22.5431, lng=114.0579, is_active=True, has_store=True, content_status="published", subdomain="shenzhen",
             seo_title="深圳门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格深圳门店提供阳台封窗、抗风压门窗、隔音窗、旧窗改造等专业服务，支持预约上门测量。",
             hero_title="深圳门窗安装与旧窗改造", hero_subtitle="南山、福田、宝安、龙岗、龙华等区域可预约上门测量"),
        City(name="北京", slug="beijing", province="北京", lat=39.9042, lng=116.4074, is_active=True, has_store=True, content_status="published", subdomain="beijing",
             seo_title="北京门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格北京门店提供保温隔音窗、旧窗改造、断桥铝门窗等专业服务，支持预约上门测量。",
             hero_title="北京门窗安装与旧窗改造", hero_subtitle="朝阳、海淀、丰台、通州、昌平等区域可预约上门测量"),
        City(name="佛山", slug="foshan", province="广东", lat=23.0218, lng=113.1218, is_active=True, has_store=True, content_status="published", subdomain="foshan",
             seo_title="佛山门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格佛山门店提供阳台封窗、隔音门窗、旧窗改造等专业服务，支持预约上门测量。",
             hero_title="佛山门窗安装与旧窗改造", hero_subtitle="禅城、南海、顺德等区域可预约上门测量"),
        City(name="东莞", slug="dongguan", province="广东", lat=23.0208, lng=113.7518, is_active=True, has_store=True, content_status="published", subdomain="dongguan",
             seo_title="东莞门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格东莞门店提供阳台封窗、隔音门窗、旧窗改造等专业服务，支持预约上门测量。",
             hero_title="东莞门窗安装与旧窗改造", hero_subtitle="南城、东城、万江、莞城等区域可预约上门测量"),
        # ── 全国省会城市（含直辖市）──
        City(name="石家庄", slug="shijiazhuang", province="河北", lat=38.0428, lng=114.5149, is_active=True, has_store=False,
             seo_title="石家庄门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格石家庄门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="石家庄门窗安装与旧窗改造", hero_subtitle="石家庄全市区域可预约上门测量。"),
        City(name="太原", slug="taiyuan", province="山西", lat=37.8706, lng=112.5489, is_active=True, has_store=False,
             seo_title="太原门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格太原门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="太原门窗安装与旧窗改造", hero_subtitle="太原全市区域可预约上门测量。"),
        City(name="呼和浩特", slug="huhehaote", province="内蒙古", lat=40.8424, lng=111.7490, is_active=True, has_store=False,
             seo_title="呼和浩特门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格呼和浩特门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="呼和浩特门窗安装与旧窗改造", hero_subtitle="呼和浩特全市区域可预约上门测量。"),
        City(name="沈阳", slug="shenyang", province="辽宁", lat=41.8057, lng=123.4315, is_active=True, has_store=False,
             seo_title="沈阳门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格沈阳门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="沈阳门窗安装与旧窗改造", hero_subtitle="沈阳全市区域可预约上门测量。"),
        City(name="长春", slug="changchun", province="吉林", lat=43.8171, lng=125.3235, is_active=True, has_store=False,
             seo_title="长春门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格长春门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="长春门窗安装与旧窗改造", hero_subtitle="长春全市区域可预约上门测量。"),
        City(name="哈尔滨", slug="haerbin", province="黑龙江", lat=45.8038, lng=126.5350, is_active=True, has_store=False,
             seo_title="哈尔滨门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格哈尔滨门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="哈尔滨门窗安装与旧窗改造", hero_subtitle="哈尔滨全市区域可预约上门测量。"),
        City(name="上海", slug="shanghai", province="上海", lat=31.2304, lng=121.4737, is_active=True, has_store=False,
             seo_title="上海门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格上海门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="上海门窗安装与旧窗改造", hero_subtitle="上海全市区域可预约上门测量。"),
        City(name="南京", slug="nanjing", province="江苏", lat=32.0603, lng=118.7969, is_active=True, has_store=False,
             seo_title="南京门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格南京门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="南京门窗安装与旧窗改造", hero_subtitle="南京全市区域可预约上门测量。"),
        City(name="杭州", slug="hangzhou", province="浙江", lat=30.2741, lng=120.1551, is_active=True, has_store=False,
             seo_title="杭州门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格杭州门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="杭州门窗安装与旧窗改造", hero_subtitle="杭州全市区域可预约上门测量。"),
        City(name="合肥", slug="hefei", province="安徽", lat=31.8206, lng=117.2272, is_active=True, has_store=False,
             seo_title="合肥门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格合肥门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="合肥门窗安装与旧窗改造", hero_subtitle="合肥全市区域可预约上门测量。"),
        City(name="福州", slug="fuzhou", province="福建", lat=26.0745, lng=119.2965, is_active=True, has_store=False,
             seo_title="福州门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格福州门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="福州门窗安装与旧窗改造", hero_subtitle="福州全市区域可预约上门测量。"),
        City(name="南昌", slug="nanchang", province="江西", lat=28.6820, lng=115.8579, is_active=True, has_store=False,
             seo_title="南昌门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格南昌门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="南昌门窗安装与旧窗改造", hero_subtitle="南昌全市区域可预约上门测量。"),
        City(name="济南", slug="jinan", province="山东", lat=36.6512, lng=116.9972, is_active=True, has_store=False,
             seo_title="济南门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格济南门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="济南门窗安装与旧窗改造", hero_subtitle="济南全市区域可预约上门测量。"),
        City(name="郑州", slug="zhengzhou", province="河南", lat=34.7466, lng=113.6254, is_active=True, has_store=False,
             seo_title="郑州门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格郑州门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="郑州门窗安装与旧窗改造", hero_subtitle="郑州全市区域可预约上门测量。"),
        City(name="武汉", slug="wuhan", province="湖北", lat=30.5928, lng=114.3055, is_active=True, has_store=False,
             seo_title="武汉门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格武汉门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="武汉门窗安装与旧窗改造", hero_subtitle="武汉全市区域可预约上门测量。"),
        City(name="长沙", slug="changsha", province="湖南", lat=28.2282, lng=112.9388, is_active=True, has_store=False,
             seo_title="长沙门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格长沙门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="长沙门窗安装与旧窗改造", hero_subtitle="长沙全市区域可预约上门测量。"),
        City(name="海口", slug="haikou", province="海南", lat=20.0440, lng=110.3520, is_active=True, has_store=False,
             seo_title="海口门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格海口门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="海口门窗安装与旧窗改造", hero_subtitle="海口全市区域可预约上门测量。"),
        City(name="成都", slug="chengdu", province="四川", lat=30.5728, lng=104.0668, is_active=True, has_store=False,
             seo_title="成都门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格成都门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="成都门窗安装与旧窗改造", hero_subtitle="成都全市区域可预约上门测量。"),
        City(name="贵阳", slug="guiyang", province="贵州", lat=26.6470, lng=106.6302, is_active=True, has_store=False,
             seo_title="贵阳门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格贵阳门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="贵阳门窗安装与旧窗改造", hero_subtitle="贵阳全市区域可预约上门测量。"),
        City(name="昆明", slug="kunming", province="云南", lat=25.0389, lng=102.7183, is_active=True, has_store=False,
             seo_title="昆明门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格昆明门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="昆明门窗安装与旧窗改造", hero_subtitle="昆明全市区域可预约上门测量。"),
        City(name="拉萨", slug="lasa", province="西藏", lat=29.6500, lng=91.1000, is_active=True, has_store=False,
             seo_title="拉萨门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格拉萨门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="拉萨门窗安装与旧窗改造", hero_subtitle="拉萨全市区域可预约上门测量。"),
        City(name="西安", slug="xian", province="陕西", lat=34.3416, lng=108.9398, is_active=True, has_store=False,
             seo_title="西安门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格西安门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="西安门窗安装与旧窗改造", hero_subtitle="西安全市区域可预约上门测量。"),
        City(name="兰州", slug="lanzhou", province="甘肃", lat=36.0611, lng=103.8343, is_active=True, has_store=False,
             seo_title="兰州门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格兰州门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="兰州门窗安装与旧窗改造", hero_subtitle="兰州全市区域可预约上门测量。"),
        City(name="西宁", slug="xining", province="青海", lat=36.6171, lng=101.7782, is_active=True, has_store=False,
             seo_title="西宁门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格西宁门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="西宁门窗安装与旧窗改造", hero_subtitle="西宁全市区域可预约上门测量。"),
        City(name="银川", slug="yinchuan", province="宁夏", lat=38.4872, lng=106.2309, is_active=True, has_store=False,
             seo_title="银川门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格银川门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="银川门窗安装与旧窗改造", hero_subtitle="银川全市区域可预约上门测量。"),
        City(name="乌鲁木齐", slug="wulumuqi", province="新疆", lat=43.8256, lng=87.6168, is_active=True, has_store=False,
             seo_title="乌鲁木齐门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格乌鲁木齐门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="乌鲁木齐门窗安装与旧窗改造", hero_subtitle="乌鲁木齐全市区域可预约上门测量。"),
        City(name="天津", slug="tianjin", province="天津", lat=39.0842, lng=117.2009, is_active=True, has_store=False,
             seo_title="天津门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格天津门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="天津门窗安装与旧窗改造", hero_subtitle="天津全市区域可预约上门测量。"),
        City(name="重庆", slug="chongqing", province="重庆", lat=29.5630, lng=106.5516, is_active=True, has_store=False,
             seo_title="重庆门窗安装与旧窗改造_博雅敏格门窗", seo_description="博雅敏格重庆门店提供阳台封窗、隔音门窗、旧窗改造、防盗门等专业服务，支持预约上门测量。",
             hero_title="重庆门窗安装与旧窗改造", hero_subtitle="重庆全市区域可预约上门测量。"),
    ]
    for city in cities_data:
        if not db.query(City).filter(City.slug == city.slug).first():
            db.add(city)
    db.commit()


def seed_stores(db: Session) -> None:
    # Get city IDs
    gz = db.query(City).filter(City.slug == "guangzhou").first()
    sz = db.query(City).filter(City.slug == "shenzhen").first()
    bj = db.query(City).filter(City.slug == "beijing").first()
    fs = db.query(City).filter(City.slug == "foshan").first()
    dg = db.query(City).filter(City.slug == "dongguan").first()

    stores_data = [
        # 广州 3 家门店
        Store(city_id=gz.id, store_name="博雅敏格天河体验中心", province="广东", city="广州", district="天河区",
               address="广州市天河区体育西路103号", lat=23.1361, lng=113.3310, phone="020-88880001",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","隔音门窗","旧窗改造","防盗门","断桥铝门窗"],
               cover_image="/images/stores/gz-tianhe.jpg", is_active=True, sort_order=1),
        Store(city_id=gz.id, store_name="博雅敏格海珠旗舰店", province="广东", city="广州", district="海珠区",
               address="广州市海珠区江南大道中168号", lat=23.0833, lng=113.3175, phone="020-88880002",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","隔音门窗","旧窗改造","防盗门"],
               cover_image="/images/stores/gz-haizhu.jpg", is_active=True, sort_order=2),
        Store(city_id=gz.id, store_name="博雅敏格番禺体验店", province="广东", city="广州", district="番禺区",
               address="广州市番禺区市桥街道大北路88号", lat=22.9372, lng=113.3640, phone="020-88880003",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","旧窗改造","断桥铝门窗"],
               cover_image="/images/stores/gz-panyu.jpg", is_active=True, sort_order=3),
        # 深圳 2 家门店
        Store(city_id=sz.id, store_name="博雅敏格南山体验中心", province="广东", city="深圳", district="南山区",
               address="深圳市南山区科技园南路18号", lat=22.5333, lng=113.9300, phone="0755-88880001",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","抗风压门窗","隔音窗","旧窗改造","防盗门","断桥铝"],
               cover_image="/images/stores/sz-nanshan.jpg", is_active=True, sort_order=1),
        Store(city_id=sz.id, store_name="博雅敏格福田旗舰店", province="广东", city="深圳", district="福田区",
               address="深圳市福田区深南中路1028号", lat=22.5362, lng=114.0579, phone="0755-88880002",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","隔音窗","旧窗改造","防盗门"],
               cover_image="/images/stores/sz-futian.jpg", is_active=True, sort_order=2),
        # 北京 2 家门店
        Store(city_id=bj.id, store_name="博雅敏格朝阳体验中心", province="北京", city="北京", district="朝阳区",
               address="北京市朝阳区建国路88号", lat=39.9087, lng=116.4600, phone="010-88880001",
               opening_hours="周一至周日 9:00-20:00", services=["保温隔音窗","旧窗改造","断桥铝","防盗门","封阳台","全屋更换"],
               cover_image="/images/stores/bj-chaoyang.jpg", is_active=True, sort_order=1),
        Store(city_id=bj.id, store_name="博雅敏格海淀旗舰店", province="北京", city="北京", district="海淀区",
               address="北京市海淀区中关村大街28号", lat=39.9816, lng=116.3100, phone="010-88880002",
               opening_hours="周一至周日 9:00-20:00", services=["保温隔音窗","旧窗改造","断桥铝","防盗门"],
               cover_image="/images/stores/bj-haidian.jpg", is_active=True, sort_order=2),
        # 佛山 1 家门店
        Store(city_id=fs.id, store_name="博雅敏格禅城体验中心", province="广东", city="佛山", district="禅城区",
               address="佛山市禅城区祖庙路33号", lat=23.0218, lng=113.1218, phone="0757-88880001",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","隔音门窗","旧窗改造","断桥铝门窗","防盗门"],
               cover_image="/images/stores/fs-chancheng.jpg", is_active=True, sort_order=1),
        # 东莞 1 家门店
        Store(city_id=dg.id, store_name="博雅敏格南城体验中心", province="广东", city="东莞", district="南城区",
               address="东莞市南城区鸿福路108号", lat=23.0208, lng=113.7518, phone="0769-88880001",
               opening_hours="周一至周日 9:00-20:00", services=["阳台封窗","隔音门窗","旧窗改造","断桥铝门窗","防盗门"],
               cover_image="/images/stores/dg-nancheng.jpg", is_active=True, sort_order=1),
    ]
    for store in stores_data:
        if not db.query(Store).filter(Store.store_name == store.store_name, Store.city == store.city).first():
            db.add(store)
    db.commit()


def seed_city_cases(db: Session) -> None:
    gz = db.query(City).filter(City.slug == "guangzhou").first()
    sz = db.query(City).filter(City.slug == "shenzhen").first()
    bj = db.query(City).filter(City.slug == "beijing").first()
    fs = db.query(City).filter(City.slug == "foshan").first()
    dg = db.query(City).filter(City.slug == "dongguan").first()

    cases_data = [
        # 广州案例
        CityCase(city_id=gz.id, title="天河区某花园客厅阳台封窗", service_type="封阳台",
                  content="业主三室两厅户型，客厅连通阳台，希望封窗并改善隔热。选用70系列断桥铝平开窗，5+12A+5中空玻璃，工期5天。交付后业主确认开关顺畅、雨天未发现渗水。", images=["/images/cases/balcony-window.jpg"]),
        CityCase(city_id=gz.id, title="海珠区入户防盗门更换", service_type="防盗门",
                  content="业主两室一厅，入户门老旧需更换甲级防盗门。选用1.8mm钢质门体+多点锁闭，当天完成安装。通过业主验收，旧门由安装队清运。", images=["/images/cases/old-window-room.jpg"]),
        CityCase(city_id=gz.id, title="番禺区全屋旧窗更换", service_type="旧窗改造",
                  content="业主四室两厅，全屋旧窗漏风，统一更换断桥铝系列，加强密封胶条配置。按房间分批施工，4天完成，减少对生活影响。", images=["/images/cases/large-window-room.jpg"]),
        # 深圳案例
        CityCase(city_id=sz.id, title="南山区高层封阳台抗风压", service_type="封阳台",
                  content="业主两室一厅，高层需封阳台担心台风天摇摆。选用加强型断桥铝，钢化玻璃+防风排水设计，工期6天。交付后经历雨季未发现渗漏。", images=["/images/cases/balcony-window.jpg"]),
        CityCase(city_id=sz.id, title="福田区卧室隔音窗改造", service_type="隔音窗",
                  content="业主三室一厅，卧室靠高架夜间噪音明显。选用三玻两腔玻璃配置+优质密封，工期2天。业主反馈睡眠环境改善。", images=["/images/cases/old-window-room.jpg"]),
        # 北京案例
        CityCase(city_id=bj.id, title="朝阳区冬季旧窗改造", service_type="旧窗改造",
                  content="业主两室一厅，冬季窗框漏风燃气费偏高。选用80系列断桥铝+Low-E中空玻璃整窗更换，工期3天。业主反馈冬季体感温度提升。", images=["/images/cases/old-window-room.jpg"]),
        CityCase(city_id=bj.id, title="海淀区卧室隔音窗升级", service_type="隔音窗",
                  content="业主三室两厅，靠近主路需要卧室隔音。选用加厚中空+密封升级，保留原洞口尺寸，工期2天。验收时开关与密封均达标。", images=["/images/cases/large-window-room.jpg"]),
        # 佛山案例
        CityCase(city_id=fs.id, title="禅城区断桥铝推拉窗防潮密封", service_type="断桥铝",
                  content="业主三室两厅，原推拉窗密封差雨季渗水。选用断桥铝推拉窗+防潮密封条，工期3天。雨季复查未发现渗水。", images=["/images/cases/balcony-window.jpg"]),
        CityCase(city_id=fs.id, title="南海区卧室隔音窗更换", service_type="隔音窗",
                  content="业主两室一厅，卧室临街噪音大。选用中空隔音玻璃+优质密封，工期2天。业主反馈噪音明显降低。", images=["/images/cases/old-window-room.jpg"]),
        # 东莞案例
        CityCase(city_id=dg.id, title="南城区全屋断桥铝门窗更换", service_type="旧窗改造",
                  content="业主三室两厅，全屋旧窗更换断桥铝门窗。按房间功能分配置，工期4天。分批安装减少生活影响。", images=["/images/cases/large-window-room.jpg"]),
        CityCase(city_id=dg.id, title="东城区封阳台+隔音窗组合方案", service_type="封阳台",
                  content="业主两室一厅，阳台封窗+卧室隔音组合方案。工期3天完成，业主对隔音效果满意。", images=["/images/cases/balcony-window.jpg"]),
    ]
    for case in cases_data:
        if not db.query(CityCase).filter(CityCase.title == case.title, CityCase.city_id == case.city_id).first():
            db.add(case)
    db.commit()


def seed_city_faqs(db: Session) -> None:
    gz = db.query(City).filter(City.slug == "guangzhou").first()
    sz = db.query(City).filter(City.slug == "shenzhen").first()
    bj = db.query(City).filter(City.slug == "beijing").first()
    fs = db.query(City).filter(City.slug == "foshan").first()
    dg = db.query(City).filter(City.slug == "dongguan").first()

    faqs_data = [
        # 广州 FAQ
        CityFaq(city_id=gz.id, question="广州梅雨季窗户容易渗水怎么办？", answer="重点检查排水孔、外侧打胶与框体坡度。老窗建议整体评估密封条与玻璃压线，必要时整窗更换。"),
        CityFaq(city_id=gz.id, question="广州门店多久能上门测量？", answer="一般留资后1-2个工作日内联系预约，高峰时段可能顺延。"),
        CityFaq(city_id=gz.id, question="番禺、黄埔等外围区域是否服务？", answer="上述区域均在服务范围内，远郊具体以门店调度为准。"),
        # 深圳 FAQ
        CityFaq(city_id=sz.id, question="深圳高层封阳台有什么要求？", answer="需符合物业与本地管理要求，测量阶段会确认开启方式与型材强度，避免超重玻璃方案。"),
        CityFaq(city_id=sz.id, question="宝安、龙岗距离较远是否额外收费？", answer="市内常规区域测量不另收费，特殊远郊地址以门店说明为准。"),
        CityFaq(city_id=sz.id, question="隔音窗能否解决高架噪音？", answer="可显著改善，但效果与楼层、距离、玻璃配置有关，建议现场评估后选方案。"),
        # 北京 FAQ
        CityFaq(city_id=bj.id, question="北京旧窗改造会不会影响供暖？", answer="施工期间会短暂打开洞口，建议选择非极端寒潮时段，安装完成后密封恢复。"),
        CityFaq(city_id=bj.id, question="Low-E玻璃是否值得上？", answer="对保温有一定帮助，是否采用取决于朝向与预算，测量时会给出对比方案。"),
        CityFaq(city_id=bj.id, question="通州、昌平能否当天测量？", answer="需提前预约，门店按路线排期，一般1-2日内可安排。"),
        # 佛山 FAQ
        CityFaq(city_id=fs.id, question="佛山气候潮湿，门窗怎么选？", answer="建议关注型材表面处理与排水设计，密封胶条需耐老化，断桥铝适合多数户型。"),
        CityFaq(city_id=fs.id, question="禅城、南海区域是否支持上门测量？", answer="禅城、南海、顺德均在服务范围内，可预约上门测量。"),
        CityFaq(city_id=fs.id, question="旧窗改造工期多久？", answer="一般2-5天，视窗户数量和现场条件而定，测量时会给出具体工期。"),
        # 东莞 FAQ
        CityFaq(city_id=dg.id, question="东莞门窗安装有什么注意事项？", answer="建议关注防潮防水和隔音效果，选择适合本地气候的型材和玻璃配置。"),
        CityFaq(city_id=dg.id, question="南城、东城区域是否支持上门测量？", answer="南城、东城、万江、莞城均在服务范围内，可预约上门测量。"),
        CityFaq(city_id=dg.id, question="门窗质保多久？", answer="主体产品质保按国家标准及门店政策执行，具体以合同约定为准。"),
    ]
    for faq in faqs_data:
        if not db.query(CityFaq).filter(CityFaq.question == faq.question, CityFaq.city_id == faq.city_id).first():
            db.add(faq)
    db.commit()


def seed_knowledge(db: Session) -> None:
    knowledge_data = [
        KnowledgeDocument(title="博雅敏格甲级防盗门产品参数", doc_type="product", city=None, category="防盗门",
                          tags=["防盗门","甲级","产品参数"], source="产品手册",
                          content="博雅敏格甲级防盗门参数：\n门体壁厚≥1.8mm钢质门体，配合多点锁闭系统。门扇厚度90mm，内填充蜂窝纸/岩棉。铰链采用不锈钢材质，锁具为C级防盗锁芯。表面处理：静电喷涂/转印木纹。适用场景：入户门、别墅大门。安装周期1天，需提前测量洞口尺寸。"),
        KnowledgeDocument(title="断桥铝门窗型材参数与选型指南", doc_type="product", city=None, category="断桥铝",
                          tags=["断桥铝","型材","参数","选型"], source="技术文档",
                          content="断桥铝门窗选型指南：\n型材壁厚：1.4mm（国标最低）- 2.0mm（高端）\n系列：60/70/80系列，数字越大隔热条越宽\n玻璃配置：5+12A+5中空钢化（标配）；5+9A+5+9A+5三玻两腔（升级）\n五金：进口品牌（好博、诺托）寿命≥10万次开合\n密封胶条：三元乙丙（EPDM），耐候性优异\n隔热条：PA66GF25尼龙条，宽度24mm-36mm"),
        KnowledgeDocument(title="门窗安装标准流程", doc_type="policy", city=None, category="安装流程",
                          tags=["安装","流程","标准"], source="施工规范",
                          content="博雅敏格门窗安装标准流程：\n1. 上门测量：记录洞口尺寸、墙体条件、开启方向\n2. 方案确认：根据户型与预算推荐方案，确认型材、玻璃、五金配置\n3. 工厂生产：按订单尺寸定制，生产周期7-15天\n4. 拆除旧窗：保护性拆除，清理洞口\n5. 安装新窗：水平校准、膨胀螺栓固定、发泡剂填充\n6. 密封处理：内外打胶、安装压条\n7. 验收：开关顺畅度、密封性、锁具功能逐项检查\n8. 清洁交付：清理现场，交付使用说明"),
        KnowledgeDocument(title="广州防盗门安装案例", doc_type="case", city="广州", category="防盗门",
                          tags=["广州","防盗门","案例"], source="门店记录",
                          content="广州天河区某小区张先生选用博雅敏格甲级防盗门，门体壁厚1.8mm，配合多点锁闭系统。安装周期1天，业主反馈隔音效果明显。旧门由安装队清运。价格区间3000-8000元，具体以门店实测为准。"),
        KnowledgeDocument(title="深圳断桥铝封阳台案例", doc_type="case", city="深圳", category="封阳台",
                          tags=["深圳","封阳台","断桥铝","案例"], source="门店记录",
                          content="深圳南山区李女士全屋封阳台，选用博雅敏格70系列断桥铝，5+12A+5中空钢化玻璃。高层加强型材配置，防风排水设计。工期5天完成，经历雨季未发现渗漏。"),
        KnowledgeDocument(title="北京旧窗改造保温案例", doc_type="case", city="北京", category="旧窗改造",
                          tags=["北京","旧窗改造","保温","案例"], source="门店记录",
                          content="北京朝阳区王先生老房换窗，选用博雅敏格80系列断桥铝+Low-E中空玻璃。冬季室温提升约2℃，燃气费下降。工期3天，按房间分批施工减少影响。"),
        KnowledgeDocument(title="卧室隔音窗选购指南", doc_type="faq", city=None, category="隔音窗",
                          tags=["隔音窗","卧室","选购"], source="知识库",
                          content="卧室隔音窗选购要点：\n1. 玻璃配置：中空钢化起步，临街建议三玻两腔或夹胶玻璃\n2. 型材：断桥铝多腔体型材，密封胶条选三元乙丙\n3. 开启方式：平开窗隔音优于推拉窗\n4. 安装工艺：发泡剂填充饱满、内外打胶密封\n5. 常见误区：玻璃越厚隔音越好？不一定，中空层厚度和密封性更关键"),
        KnowledgeDocument(title="封阳台注意事项与物业审批", doc_type="faq", city=None, category="封阳台",
                          tags=["封阳台","物业","审批","注意事项"], source="知识库",
                          content="封阳台注意事项：\n1. 物业审批：多数小区需物业备案，确认允许封阳台\n2. 承重确认：测量时确认阳台承重与结构\n3. 开启方式：推拉vs平开，各有利弊\n4. 排水设计：排水孔位置与坡度\n5. 密封处理：内外打胶、防水处理\n6. 玻璃选择：钢化玻璃为标配，高层建议加厚\n7. 工期：一般3-7天，视面积而定"),
    ]
    for doc in knowledge_data:
        if not db.query(KnowledgeDocument).filter(KnowledgeDocument.title == doc.title).first():
            db.add(doc)
    db.commit()

    # Also create knowledge chunks for search to work
    from app.services.content_service import _chunk_text, _keywords_for_chunk
    from app.models import KnowledgeChunk
    for doc in db.query(KnowledgeDocument).all():
        if db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).count() > 0:
            continue
        chunks = _chunk_text(doc.content)
        tags = doc.tags if isinstance(doc.tags, list) else []
        for index, chunk_content in enumerate(chunks):
            db.add(KnowledgeChunk(
                document_id=doc.id,
                chunk_index=index,
                content=chunk_content,
                keywords=_keywords_for_chunk(doc, chunk_content),
                tags=tags,
            ))
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_users(db)
            seed_dealers(db)
            seed_cities(db)
            seed_stores(db)
            seed_city_cases(db)
            seed_city_faqs(db)
            seed_knowledge(db)
            seed_leads(db)
            seed_contents_and_publications(db)
            seed_materials(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    # 生产环境关闭 /docs /redoc /openapi.json 暴露
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router)


@app.middleware("http")
async def persist_audit_log(request: Request, call_next):
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        username = None
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            try:
                import jwt
                payload = jwt.decode(authorization[7:], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
                username = payload.get("sub")
            except Exception:
                username = None
        db = SessionLocal()
        try:
            db.add(AuditLog(
                username=username,
                method=request.method,
                path=request.url.path[:512],
                status_code=response.status_code,
                client_ip=request.client.host[:64] if request.client else None,
                user_agent=(request.headers.get("user-agent") or "")[:500] or None,
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    return response


@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
    HTTP_LATENCY.labels(request.method, route_path).observe(perf_counter() - started)
    return response

# 静态文件：经销商上传的素材
_upload_dir = os.environ.get("MATERIAL_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))
os.makedirs(_upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    checks: dict[str, dict[str, object]] = {}
    ready = True
    db = SessionLocal()
    try:
        db.execute(sql_text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as exc:
        ready = False
        checks["database"] = {"ok": False, "error": str(exc)}
    finally:
        db.close()

    try:
        from app.core.redis_client import get_redis
        get_redis().ping()
        checks["redis"] = {"ok": True}
    except Exception as exc:
        if settings.is_production:
            ready = False
        checks["redis"] = {"ok": False, "required": settings.is_production, "error": str(exc)}

    try:
        with tempfile.NamedTemporaryFile(dir=_upload_dir, prefix=".ready-", delete=True):
            pass
        checks["uploads"] = {"ok": True}
    except Exception as exc:
        ready = False
        checks["uploads"] = {"ok": False, "error": str(exc)}

    from app.integrations.synapse_engine.utils.playwright_provider import browser_executable_available
    publish_runtime = browser_executable_available()
    if settings.is_production and not publish_runtime:
        ready = False
    checks["publish_runtime"] = {"ok": publish_runtime, "required": settings.is_production}
    return JSONResponse({"status": "ready" if ready else "not_ready", "checks": checks}, status_code=200 if ready else 503)


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "status": "ok",
        "message": "这是 API 服务，不是官网页面。官网请访问 Nginx 入口。",
        "links": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "articles": "/api/v1/articles",
            "leads": "/api/v1/leads",
            "metrics": "/api/v1/metrics?city=广州",
        },
        "website": settings.site_base_url,
        "admin": f"{settings.site_base_url.rstrip('/')}/admin",
    }

# ── 定时发布后台扫描线程 ──────────────────────────────
import threading
import time as _time
from app.core.database import SessionLocal


def _scheduled_publish_loop() -> None:
    """每 60 秒扫描一次到时间的定时发布任务（站内内容 + 外部平台）。"""
    from app.services.post_service import run_scheduled_publish
    from app.services.external_publish_service import run_scheduled_external_publish
    while True:
        try:
            db = SessionLocal()
            try:
                n = run_scheduled_publish(db)
                if n:
                    print(f"[scheduled-publish] 发布 {n} 篇定时内容")
                m = run_scheduled_external_publish(db)
                if m:
                    print(f"[scheduled-publish] 派发 {m} 个定时外部发布任务")
            finally:
                db.close()
        except Exception as e:
            print(f"[scheduled-publish] 扫描失败: {e}")
        _time.sleep(60)


def _start_scheduled_publish_thread() -> None:
    t = threading.Thread(target=_scheduled_publish_loop, name="scheduled-publish", daemon=True)
    t.start()


# 测试环境（pytest）下不启动后台定时线程：测试直接调用扫描服务，
# 避免后台线程用真实 SessionLocal 轮询与用例引擎产生时序竞争。
import sys as _sys

if "pytest" not in _sys.modules:
    _start_scheduled_publish_thread()

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

JSONField = JSON().with_variant(JSONB(), "postgresql")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=True, index=True)
    method = Column(String(16), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=False)
    client_ip = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Intent(Base):
    __tablename__ = "intent"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(128), nullable=False, index=True)
    intent_type = Column(String(32), nullable=False)
    city_list = Column(JSONField, nullable=False, default=list)
    keyword_json = Column(JSONField, nullable=False, default=list)
    hotness_score = Column(Integer, nullable=False, default=0)
    difficulty_score = Column(Integer, nullable=False, default=0)
    priority = Column(String(8), nullable=False, default="P2")


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(Integer, nullable=True, index=True)
    city = Column(String(64), nullable=False, index=True)
    type = Column(String(16), nullable=False)  # seo|geo|schema（AI 生成类型）
    post_type = Column(String(16), nullable=False, default="article", index=True)  # article|case|knowledge|seo_page
    title = Column(String(500), nullable=True)
    slug = Column(String(300), nullable=True, index=True)
    summary = Column(String(1000), nullable=True)
    markdown = Column(Text, nullable=False)
    cover_image = Column(String(512), nullable=True)
    cover_image_alt = Column(String(255), nullable=True)
    eeat_score = Column(Integer, nullable=True)
    eeat_breakdown = Column(JSONField, nullable=True)
    status = Column(String(32), nullable=False, default="draft", index=True)  # draft|approved|published|offline|rejected
    model_used = Column(String(64), nullable=True)
    schema_jsonld = Column(Text, nullable=True)
    # ── SEO 扩展 ──
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(String(500), nullable=True)
    canonical = Column(String(512), nullable=True)
    keywords = Column(JSONField, nullable=False, default=list)
    # ── 归属扩展 ──
    store_id = Column(Integer, nullable=True, index=True)
    author_id = Column(Integer, nullable=True)  # 创建者 user_id
    # ── 发布调度 ──
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    offline_at = Column(DateTime(timezone=True), nullable=True)
    # ── 时间戳 ──
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    doc_type = Column(String(32), nullable=False, default="general", index=True)
    city = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)
    tags = Column(JSONField, nullable=False, default=list)
    source = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    keywords = Column(JSONField, nullable=False, default=list)
    tags = Column(JSONField, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ContentTemplate(Base):
    __tablename__ = "content_template"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)
    template_body = Column(Text, nullable=False)
    similarity_threshold = Column(Float, nullable=False, default=0.70)


class Publication(Base):
    __tablename__ = "publication"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(64), nullable=False)  # website|baijiahao|zhihu|xiaohongshu|douyin|...
    tier = Column(String(4), nullable=False)  # L0(website)|L1|L2|L3
    url = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending|published|failed|offline|confirmed|rejected|package_ready
    publish_mode = Column(String(16), nullable=False, default="direct")  # direct|schedule
    published_at = Column(String(64), nullable=True)
    dealer_id = Column(String(32), nullable=True)
    operator_id = Column(Integer, nullable=True)  # 操作人 user_id
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Dealer(Base):
    __tablename__ = "dealer"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    city = Column(String(64), nullable=False, index=True)
    phone = Column(String(64), nullable=False)
    baijiahao_account = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    activation_score = Column(Integer, nullable=False, default=0)


class Lead(Base):
    __tablename__ = "lead"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    phone = Column(String(32), nullable=False)
    city = Column(String(64), nullable=False, index=True)
    interest = Column(String(128), nullable=False)
    source = Column(String(32), nullable=False)
    utm = Column(String(512), nullable=True)
    dealer_id = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # ── 二级域名归因扩展 ──
    city_id = Column(Integer, nullable=True, index=True)
    store_id = Column(Integer, nullable=True, index=True)
    host = Column(String(255), nullable=True)
    source_path = Column(String(512), nullable=True)
    landing_url = Column(String(512), nullable=True)
    utm_json = Column(JSONField, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)


class CallRecord(Base):
    __tablename__ = "call_record"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, nullable=False, index=True)
    call_id = Column(String(64), nullable=False, unique=True)
    duration_sec = Column(Integer, nullable=True)
    result = Column(String(64), nullable=True)
    recording_url = Column(String(512), nullable=True)


class Material(Base):
    __tablename__ = "material"

    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(String(32), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    oss_url = Column(String(512), nullable=False)
    copyright_declared = Column(String(8), nullable=False, default="yes")
    uploaded_at = Column(String(64), nullable=True)


class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    province = Column(String(32), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    has_store = Column(Boolean, nullable=False, default=False)
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(String(500), nullable=True)
    hero_title = Column(String(200), nullable=True)
    hero_subtitle = Column(String(500), nullable=True)
    # ── 二级域名 / SEO 扩展 ──
    subdomain = Column(String(64), nullable=True, unique=True, index=True)
    custom_domain = Column(String(255), nullable=True, unique=True)
    canonical_url = Column(String(255), nullable=True)
    seo_keywords = Column(JSONField, nullable=False, default=list)
    seo_indexable = Column(Boolean, nullable=False, default=True)
    robots_policy = Column(String(32), nullable=False, default="index_follow")
    hero_image = Column(String(512), nullable=True)
    service_area_json = Column(JSONField, nullable=False, default=list)
    service_tags = Column(JSONField, nullable=False, default=list)
    content_status = Column(String(32), nullable=False, default="draft")  # draft|ready|published|archived
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, nullable=False, index=True)
    store_name = Column(String(128), nullable=False)
    province = Column(String(32), nullable=False)
    city = Column(String(64), nullable=False)
    district = Column(String(64), nullable=False)
    address = Column(String(256), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    phone = Column(String(32), nullable=False)
    opening_hours = Column(String(128), nullable=True)
    services = Column(JSONField, nullable=False, default=list)
    cover_image = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    # ── 门店扩展 ──
    store_code = Column(String(64), nullable=True, unique=True, index=True)
    manager_user_id = Column(Integer, nullable=True, index=True)
    dealer_code = Column(String(32), nullable=True, index=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    booking_url = Column(String(512), nullable=True)
    wechat_qr = Column(String(512), nullable=True)
    gallery = Column(JSONField, nullable=False, default=list)
    service_radius = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active|hidden|closed


class CityCase(Base):
    __tablename__ = "city_case"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    service_type = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)
    images = Column(JSONField, nullable=False, default=list)


class CityFaq(Base):
    __tablename__ = "city_faq"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, nullable=False, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)


# ── 社媒发布/采集（Synapse + MediaCrawler 内嵌）───────────────────────────

class SocialAccount(Base):
    """社媒账号（小红书/视频号/抖音/快手/B站）。"""
    __tablename__ = "social_account"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)  # xiaohongshu|channels|douyin|kuaishou|bilibili
    platform_code = Column(Integer, nullable=False)  # 1/2/3/4/5
    display_name = Column(String(128), nullable=False)
    internal_account_id = Column(String(128), nullable=True, index=True)  # 内部 account_id（同 Synapse）
    user_id = Column(String(128), nullable=True)  # 平台 user_id
    avatar = Column(String(512), nullable=True)
    cookie_status = Column(String(32), nullable=False, default="missing_cookie")  # active|expired|missing_cookie|disabled
    cookie_path = Column(String(512), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active|disabled
    city = Column(String(64), nullable=True, index=True)
    dealer_id = Column(String(32), nullable=True, index=True)
    note = Column(Text, nullable=True)
    raw = Column(JSONField, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialMaterial(Base):
    """社媒素材（视频/封面图），与 Content 绑定。"""
    __tablename__ = "social_material"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, nullable=True, index=True)
    dealer_id = Column(String(32), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    local_path = Column(String(512), nullable=False)
    internal_file_id = Column(String(128), nullable=True, index=True)  # 内部 file_id
    file_type = Column(String(16), nullable=False)  # video|image|cover
    size_mb = Column(Float, nullable=True)
    duration_sec = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    cover_path = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending|ready|invalid|deleted
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialPublicationTask(Base):
    """社媒发布任务（关联 Publication）。"""
    __tablename__ = "social_publication_task"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, nullable=False, index=True)
    publication_id = Column(Integer, nullable=True, index=True)  # 关联 Publication
    platform = Column(String(32), nullable=False, index=True)
    platform_code = Column(Integer, nullable=False)
    social_account_id = Column(Integer, nullable=False, index=True)
    social_material_id = Column(Integer, nullable=True)
    internal_file_id = Column(String(128), nullable=True)
    worker_task_id = Column(String(128), nullable=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    topics = Column(JSONField, nullable=False, default=list)
    cover_path = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending|scheduled|running|success|failed|cancelled
    error_message = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    raw_response = Column(JSONField, nullable=True)
    allow_duplicate = Column(Boolean, nullable=False, default=False)
    interval_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialPublishLog(Base):
    """社媒发布日志（worker 执行轨迹）。"""
    __tablename__ = "social_publish_log"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    level = Column(String(16), nullable=False, default="info")  # info|warn|error
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PublishArtifact(Base):
    """外部发布制品（截图 / HTML / 错误快照），用于留痕与排错。"""
    __tablename__ = "publish_artifact"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)  # SocialPublicationTask.id
    artifact_type = Column(String(32), nullable=False, default="screenshot")  # screenshot|error_screenshot|html
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)  # 服务器本地绝对/相对路径
    url = Column(String(512), nullable=True)  # 可访问 URL（/uploads/...）
    note = Column(String(255), nullable=True)  # 步骤标记（before_publish/after_publish/...）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialCrawlerJob(Base):
    """社媒数据采集任务。"""
    __tablename__ = "social_crawler_job"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)  # xhs|dy|ks|bili|wb|tieba|zhihu
    crawler_type = Column(String(16), nullable=False, default="search")  # search|detail|creator
    keyword = Column(String(255), nullable=True)
    account_ref = Column(String(255), nullable=True)  # creator_id 列表，逗号分隔
    city = Column(String(64), nullable=True, index=True)
    login_type = Column(String(16), nullable=False, default="cookie")  # qrcode|phone|cookie
    cookies = Column(Text, nullable=True)
    save_option = Column(String(16), nullable=False, default="jsonl")  # csv|json|jsonl|excel|db
    max_notes_count = Column(Integer, nullable=False, default=20)
    headless = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending|running|success|failed|stopped
    save_path = Column(String(512), nullable=True)
    pid = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialCrawlerItem(Base):
    """社媒采集结果条目。"""
    __tablename__ = "social_crawler_item"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    source_keyword = Column(String(255), nullable=True, index=True)
    note_id = Column(String(128), nullable=True)
    author = Column(String(128), nullable=True)
    author_id = Column(String(128), nullable=True)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(512), nullable=True)
    publish_time = Column(String(64), nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    collects = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    city = Column(String(64), nullable=True, index=True)
    tag_list = Column(JSONField, nullable=True)
    raw = Column(JSONField, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialCrawlerImportLog(Base):
    """采集数据导入日志。"""
    __tablename__ = "social_crawler_import_log"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=True, index=True)
    file_path = Column(String(512), nullable=False)
    platform = Column(String(32), nullable=True)
    imported_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="success")  # success|failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

import warnings
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {
    "change-me-in-production",
    "boyamingge-secret",
}


def _is_placeholder(value: str) -> bool:
    normalized = (value or "").strip().upper()
    return not normalized or any(
        marker in normalized
        for marker in ("REPLACE_WITH", "YOUR_", "EXAMPLE.COM", "REDIS_HOST", "DB_HOST", ":PASSWORD@")
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"            # development|production
    app_name: str = "博雅敏格 SEO-GEO 双引擎智能体"
    debug: bool = False
    seed_demo_data: bool = False
    allow_mock_providers_in_production: bool = False

    database_url: str = "postgresql://postgres:change-me-local-db@postgres:5432/boyamingge"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    oauth2_client_id: str = "boyamingge-client"
    oauth2_client_secret: str = "boyamingge-secret"

    llm_mock_mode: bool = True
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    ollama_base_url: str = "http://localhost:11434"

    # 外部服务：mock=本地演示（默认）；live=接真实 API（需配置下方密钥）
    metrics_provider: str = "mock"
    hotline_provider: str = "mock"
    distribute_mode: str = "mock"
    baidu_tongji_token: str = ""
    baidu_tongji_site_id: str = ""           # 百度统计站点ID（live 模式必填）
    baidu_tongji_api_base: str = "https://openapi.baidu.com/rest/2.0/tongji"
    tianrun_api_key: str = ""
    tianrun_api_base: str = ""
    tianrun_agent_id: str = ""               # 天润融通座席号（live 模式必填）
    tianrun_ext_id: str = ""                 # 天润融通分机号（绑定外呼号码）

    # 统一 Provider 配置
    llm_provider: str = "mock"          # LLM_PROVIDER
    geo_provider: str = "mock"           # GEO_PROVIDER
    map_provider: str = "mock"           # MAP_PROVIDER
    embedding_provider: str = "mock"     # EMBEDDING_PROVIDER
    analytics_provider: str = "mock"     # ANALYTICS_PROVIDER
    notify_provider: str = "mock"        # NOTIFY_PROVIDER

    # Mock 场景控制
    mock_scenario: str = "empty"         # MOCK_SCENARIO: normal|timeout|error|empty|no_store|content_violation|publish_fail|notify_fail

    eeat_threshold: int = 70
    publish_daily_limit: int = 3
    publish_weekly_limit: int = 15
    template_similarity_limit: float = 0.70
    new_site_page_limit: int = 20
    intent_cache_ttl_seconds: int = 7 * 24 * 3600

    site_base_url: str = "https://example.com"
    workbench_base_url: str = "https://workbench.example.com"
    packages_base_url: str = "https://example.com/packages"

    # ── 二级域名多城市 ──
    root_domain: str = "boyamingge.com"            # 根域名，用于生成城市 canonical_url
    enable_city_path_redirect: bool = False        # 生产稳定后开启 /{city} -> 子域名 301

    # CORS 白名单：逗号分隔；生产环境必须改为具体域名
    cors_origins: str = "*"

    # 上传文件大小限制（字节），默认 20MB
    upload_max_size: int = 20 * 1024 * 1024

    # ── Synapse 内嵌发布引擎 ──
    synapse_cookie_dir: str = "data/synapse_cookies"   # Playwright storage_state 落盘目录
    synapse_playwright_headless: bool = True            # Playwright 是否无头模式
    synapse_local_chrome_path: str = ""                 # 本地 Chrome 可执行文件路径（留空用 Playwright 自带）

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def docs_enabled(self) -> bool:
        """生产环境禁用 /docs /redoc /openapi.json 暴露"""
        return not self.is_production


def _validate_production_settings(settings: Settings) -> None:
    """生产环境启动前强制校验关键凭证"""
    if not settings.is_production:
        return

    problems: list[str] = []

    if (
        settings.jwt_secret_key in _INSECURE_DEFAULTS
        or len(settings.jwt_secret_key) < 32
        or _is_placeholder(settings.jwt_secret_key)
    ):
        problems.append("JWT_SECRET_KEY 必须修改为长度≥32的安全随机字符串")

    if settings.oauth2_client_secret in _INSECURE_DEFAULTS or _is_placeholder(settings.oauth2_client_secret):
        problems.append("OAUTH2_CLIENT_SECRET 必须修改为非默认值")

    if settings.cors_origins.strip() in {"*", ""}:
        problems.append("CORS_ORIGINS 不能为 *，必须指定具体域名白名单")

    if not settings.site_base_url.startswith("https://") or "example.com" in settings.site_base_url:
        problems.append("SITE_BASE_URL 必须使用实际 HTTPS 域名")

    if (
        settings.database_url.startswith("sqlite")
        or _is_placeholder(settings.database_url)
        or "postgres:postgres@" in settings.database_url
    ):
        problems.append("DATABASE_URL 必须指向正式 PostgreSQL，不能使用 SQLite 或占位值")

    if _is_placeholder(settings.redis_url):
        problems.append("REDIS_URL 必须填写真实 Redis 地址")

    if not settings.allow_mock_providers_in_production:
        if settings.llm_mock_mode or settings.llm_provider == "mock":
            problems.append("生产环境必须配置真实 LLM（LLM_MOCK_MODE=false、LLM_PROVIDER 非 mock）")
        if _is_placeholder(settings.deepseek_api_key):
            problems.append("DEEPSEEK_API_KEY 必须填写真实密钥")
        if settings.metrics_provider != "live":
            problems.append("METRICS_PROVIDER 必须为 live")
        if _is_placeholder(settings.baidu_tongji_token) or _is_placeholder(settings.baidu_tongji_site_id):
            problems.append("百度统计 live 模式必须填写 TOKEN 与 SITE_ID")
        if settings.hotline_provider != "live":
            problems.append("HOTLINE_PROVIDER 必须为 live")
        if any(
            _is_placeholder(value)
            for value in (
                settings.tianrun_api_key,
                settings.tianrun_api_base,
                settings.tianrun_agent_id,
                settings.tianrun_ext_id,
            )
        ):
            problems.append("热线 live 模式必须填写天润 API、座席号和分机号")
        if settings.distribute_mode != "live":
            problems.append("DISTRIBUTE_MODE 必须为 live")
        if _is_placeholder(settings.workbench_base_url) or _is_placeholder(settings.packages_base_url):
            problems.append("渠道分发 live 模式必须填写真实 WORKBENCH_BASE_URL 与 PACKAGES_BASE_URL")

    if problems:
        raise RuntimeError(
            "生产环境配置校验失败，请修正以下问题后再启动：\n  - " + "\n  - ".join(problems)
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        _validate_production_settings(settings)
    elif settings.jwt_secret_key == "change-me-in-production":
        warnings.warn("JWT_SECRET_KEY 未修改，请在 .env 中设置安全的密钥！", stacklevel=2)
    return settings

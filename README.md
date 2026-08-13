# 博雅敏格 SEO-GEO 双引擎智能体

基于《开发文档.md》与《PRD.md》实现的 MVP 工程，覆盖 3 城（广州/深圳/北京）单链路验证。

## 架构

- **backend/**：FastAPI 业务服务（意图挖掘、内容生成、分发、热线、监测、文章、线索）
- **frontend/**：Next.js 官网分站 + 运营后台 `/admin`
- **nginx/**：反向代理（API → FastAPI，页面 → Next.js）
- **docker-compose.yml**：一键启动 nginx + fastapi + postgres + redis + nextjs

## 快速启动

### 1. 准备环境

- Docker Desktop（或 Docker Engine + Compose）
- 可选：Python 3.11+、Node.js 20+（本地开发）

### 2. 配置环境变量

```bash
cp .env.example .env
```

默认 `LLM_MOCK_MODE=true`，无需配置 DeepSeek/Ollama API Key 即可运行。

### 3. Docker Compose 启动（推荐）

```bash
docker-compose up --build
```

启动后访问：

| 服务 | 地址 |
|---|---|
| 官网首页 | http://localhost |
| 广州分站 | http://localhost/guangzhou |
| 深圳分站 | http://localhost/shenzhen |
| 北京分站 | http://localhost/beijing |
| 攻略文章 | http://localhost/articles |
| 运营后台 | http://localhost/admin |
| sitemap | http://localhost/sitemap.xml |
| robots | http://localhost/robots.txt |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost/health |

### 4. 运营后台登录

访问 http://localhost/admin ，使用以下账号登录：

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| operator | operator123 | 运营 |

后台可演示完整运营闭环：意图挖掘 → 内容生成 → EEAT 审核 → 发布/分发 → 线索查看 → 指标看板。

### 5. API 调用示例

```bash
# 获取 JWT Token
curl -X POST http://localhost/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

TOKEN=<access_token>

# 意图挖掘
curl -X POST http://localhost/api/v1/intents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"search_terms":["门窗 安装"],"cities":["广州"],"top_k":10}'

# 内容生成
curl -X POST http://localhost/api/v1/content/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"intent":"防盗门","city":"广州","type":"seo","priority":"P0"}'

# 公开留资（无需登录）
curl -X POST http://localhost/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","phone":"13800138000","city":"广州","interest":"防盗门"}'

# 文章列表（公开）
curl http://localhost/api/v1/articles

# 线索列表（需登录）
curl http://localhost/api/v1/leads -H "Authorization: Bearer $TOKEN"
```

## 本地开发（免 Docker）

### 后端

```powershell
cd backend
mkdir data -Force
py -3 -m pip install -r requirements-local.txt
$env:DATABASE_URL = "sqlite:///./data/boyamingge.db"
$env:LLM_MOCK_MODE = "true"
py -3 -m uvicorn app.main:app --reload --port 8000
```

### 前端

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

访问 http://localhost:3000

Write-Host ""
Write-Host "=== 测试 ===" -ForegroundColor Cyan
Write-Host "后端: cd backend && py -3 -m pytest -v" -ForegroundColor Gray
Write-Host "冒烟: .\scripts\smoke-test.ps1" -ForegroundColor Gray

## 已实现能力

### 官网（可演示获客站）

- 品牌首屏：博雅敏格门窗、SEO/GEO 双引擎、400 热线 CTA
- 三城入口：广州、深圳、北京
- 服务模块：防盗门、断桥铝、阳台封窗、隔音门窗、旧窗改造
- 案例/优势/FAQ/在线留资表单
- 城市落地页：本地门店、案例、FAQ、SEO 文案、Schema JSON-LD
- 文章中心：`/articles` 列表 + `/articles/[slug]` 详情（含 GEO 摘要、FAQ、CTA、Schema）
- SEO 基础设施：sitemap.xml、robots.txt、页面 metadata / canonical

### 运营后台 `/admin`

- 登录鉴权（admin/admin123）
- 意图挖掘、内容生成、EEAT 审核（分数条/breakdown/通过拒绝）
- L0 发布、L1 半自动分发、L2 辅助内容包
- 线索列表（手机脱敏）
- 运营指标卡片 + 数据表格（非 JSON 直出）

### 后端 API

- 原有 8 个 REST API + 新增：
  - `GET /api/v1/articles` — 文章列表（公开）
  - `GET /api/v1/articles/{slug}` — 文章详情（公开）
  - `POST /api/v1/leads` — 公开留资
  - `GET /api/v1/leads` — 线索列表（运营）
  - `GET /api/v1/content` — 内容列表（运营）
  - `GET /api/v1/content/{id}` — 内容详情（运营）
  - `GET /api/v1/metrics` — 增强版含 summary 汇总

## Mock / 暂未真实对接项

| 模块 | 当前状态 | 原因 |
|---|---|---|
| LLM（DeepSeek/Qwen） | `LLM_MOCK_MODE=true` 模板生成 | 无 API Key，保留 provider 接口 |
| 5118 / 百度指数 | metrics 为 seed 数据 | 需付费数据源 |
| 百度统计 / GA | 未接入 | 需站点授权 |
| 天润融通 400 热线 | 队列模拟 | 需商务开通云呼叫中心 |
| Strapi CMS | 未部署 | MVP 用 seed + FastAPI 内容表 |
| ClickHouse / Metabase | 未部署 | metrics 用内存 mock |
| 百家号/知乎自动发布 | L1 返回确认链接 mock | 平台无开放 API |
| 百度搜索资源平台提交 | 仅保留 sitemap/说明 | 需站长验证 |

## 目录结构

```
.
├── backend/          # FastAPI 后端
├── frontend/         # Next.js 前端（官网 + /admin）
├── nginx/            # Nginx 配置
├── docker-compose.yml
├── .env.example
├── 开发文档.md
└── PRD.md
```

## SEO 后续接入说明

1. 在百度搜索资源平台验证站点所有权
2. 提交 `http://<域名>/sitemap.xml`
3. 配置百度统计 JS 或 API 对接 `metrics_service`
4. 真实收录与排名数据替换 mock metrics

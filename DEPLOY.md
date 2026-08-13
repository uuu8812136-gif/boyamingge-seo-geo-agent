# 博雅敏格 SEO-GEO 双引擎智能体 — 生产部署指南

本文档描述将本项目从开发环境部署到生产服务器的完整流程。

## 一、系统要求

- Linux 服务器（Ubuntu 22.04 / Debian 12 推荐）
- Docker 24+ 与 Docker Compose v2
- 2 核 CPU / 4GB 内存 / 40GB 磁盘（最低）
- 已备案域名 + HTTPS 证书（Let's Encrypt 免费）

## 二、目录结构

```
博雅敏格_SEO_GEO_双引擎智能体/
├── backend/             # FastAPI 后端
├── frontend/            # Next.js 15 前端
├── miniprogram/         # 微信小程序
├── nginx/               # Nginx 配置
│   ├── nginx.conf
│   └── snippets/common-server.conf
├── docker-compose.yml
├── .env.production.example # 生产环境变量模板
├── DEPLOY.md            # 本文档
├── scripts/backup.sh    # 数据库备份脚本
└── scripts/restore.sh   # 带校验与安全备份的恢复脚本
```

## 三、首次部署步骤

### 1. 上传代码到服务器

```bash
# 在服务器上
git clone <repo-url> /opt/boyamingge
cd /opt/boyamingge
```

### 2. 配置环境变量

```bash
cp .env.production.example .env.production
vi .env.production
```

**生产环境必改项（⚠️ 标记）：**

| 变量 | 说明 | 示例 |
|---|---|---|
| `APP_ENV` | 必须为 `production` | `production` |
| `JWT_SECRET_KEY` | ≥32 字符随机串 | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | 数据库密码 | 强密码 |
| `OAUTH2_CLIENT_SECRET` | OAuth2 客户端密钥 | 强密码 |
| `CORS_ORIGINS` | 允许的前端域名 | `https://www.boyamingge.com` |
| `SITE_BASE_URL` | 站点实际域名 | `https://www.boyamingge.com` |
| `NEXT_PUBLIC_SITE_URL` | 前端站点 URL | `https://www.boyamingge.com` |
| `NEXT_PUBLIC_API_URL` | 前端调用的 API URL | `https://www.boyamingge.com` |
| `INITIAL_ADMIN_USERNAME` | 首个总部管理员账号 | 非默认用户名 |
| `INITIAL_ADMIN_PASSWORD` | 首个总部管理员密码 | 至少 12 位强密码 |
| `REDIS_URL` | 后端 Redis | 实际 Redis 地址 |
| `CUSTOMER_SERVICE_REDIS_URL` | 客服会话 Redis | 建议使用独立 DB |

**第三方对接（生产默认要求全部使用 live）：**

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_MOCK_MODE` | `false` | 填 `DEEPSEEK_API_KEY` 启用真实 LLM 生成 |
| `METRICS_PROVIDER` | `live` | 填百度统计 Token 与 Site ID |
| `HOTLINE_PROVIDER` | `live` | 填完整天润融通配置 |
| `DISTRIBUTE_MODE` | `live` | 填真实工作台和下载地址 |

**mock → live 切换检查清单（生产前必读）：**

> mock 仅用于本地演示。`APP_ENV=production` 时默认拒绝 mock、占位密钥和占位地址；只有显式设置
> `ALLOW_MOCK_PROVIDERS_IN_PRODUCTION=true` 才能绕过，该开关不属于正式上线标准。

1. **LLM 内容生成**（`LLM_MOCK_MODE`）
   - mock=true：用本地模板生成文章，不调用外部 API
   - 切 live：设 `LLM_MOCK_MODE=false` 并填 `DEEPSEEK_API_KEY`
   - 验证：后台新建文章时日志出现 `deepseek` 调用，非 `mock_llm`

2. **运营指标**（`METRICS_PROVIDER`）
   - mock：返回演示数据，后台 dashboard 数字非真实
   - 切 live：设 `METRICS_PROVIDER=live` 并填 `BAIDU_TONGJI_TOKEN` + `BAIDU_TONGJI_SITE_ID`
   - 验证：后台 dashboard 数字与百度统计后台一致

3. **热线外呼**（`HOTLINE_PROVIDER`）
   - mock：线索仅入库排队，不触发真实外呼
   - 切 live：设 `HOTLINE_PROVIDER=live` 并填 `TIANRUN_API_KEY` + `TIANRUN_API_BASE` + `TIANRUN_AGENT_ID` + `TIANRUN_EXT_ID`
   - 验证：新线索提交后，天润融通座席收到外呼任务

4. **渠道分发**（`DISTRIBUTE_MODE`）
   - mock：不生成外链，线索只入本地库
   - 切 live：设 `DISTRIBUTE_MODE=live`，并确认 `WORKBENCH_BASE_URL` / `PACKAGES_BASE_URL` 已改为真实地址
   - 验证：线索详情页出现"分发到工作台"链接，点击跳转真实工作台

**⚠️ 切换 mock → live 时，必须同步检查对应 API Key 是否已填写，否则后端启动会因校验失败而拒绝服务。**

### 3. 配置 HTTPS 证书

将证书放置到 `nginx/certs/` 目录：

```bash
mkdir -p nginx/certs
# 上传 fullchain.pem 和 privkey.pem 到 nginx/certs/
```

编辑 `docker-compose.yml`，取消 nginx 服务的 HTTPS 端口和证书挂载注释：

```yaml
nginx:
  ports:
    - "80:80"
    - "443:443"   # 取消注释
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/snippets:/etc/nginx/snippets:ro
    - ./nginx/certs:/etc/nginx/certs:ro   # 取消注释
```

编辑 `nginx/nginx.conf`，按文件内注释启用 HTTPS server 块、移除 HTTP→HTTPS 跳转注释。

### 4. 构建并启动

```bash
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
```

启动后所有服务会自动 `restart: unless-stopped`，PostgreSQL 就绪后自动执行 `alembic upgrade head` 数据库迁移。

### 5. 验证部署

```bash
# 查看所有服务健康状态
docker compose ps

# 验证健康检查端点
curl http://localhost/health
# 期望：{"status":"ok"}

curl http://localhost/ready
# 期望：数据库、Redis、上传目录、发布浏览器全部 ok

# 验证 API
curl http://localhost/api/v1/cities | head

# 运行冒烟测试
SMOKE_ADMIN_PASSWORD='<后台管理员密码>' python scripts/smoke_test.py --site-base http://localhost --expect-empty
# 期望：TOTAL: 33 | PASSED: 33 | FAILED: 0
```

### 6. 配置微信小程序

1. 登录微信公众平台，将小程序后端域名加入 request 合法域名（必须 HTTPS）
2. 域名格式：`https://www.boyamingge.com`
3. 修改小程序 `miniprogram/config.js` 中的 `BASE_URL` 为生产域名

## 四、生产环境配置模板

项目根目录提供 `.env.production.example` 作为生产环境配置模板，包含全部环境变量与 mock/live 切换说明。

### 1. 创建生产配置文件

```bash
cp .env.production.example .env.production
vi .env.production
```

> ⚠️ `.env.production` 含真实密钥，**绝不要提交到仓库**（已在 `.gitignore` 中忽略）。

### 2. 必须填写的真实值清单

以下变量在 `.env.production.example` 中为占位符，部署前**必须**替换为真实值：

| 变量 | 说明 | 生成方式 |
|---|---|---|
| `JWT_SECRET_KEY` | JWT 签名密钥，≥32 字符 | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL 连接串，部署时从密钥管理器注入 | `postgresql://USER:change-me-password@DB_HOST:5432/boyamingge` |
| `POSTGRES_PASSWORD` | PostgreSQL 超级用户密码 | 强密码 |
| `CORS_ORIGINS` | 允许的前端域名白名单（逗号分隔，**不能用 `*`**） | `https://www.boyamingge.com,https://admin.boyamingge.com` |
| `SITE_BASE_URL` | 站点正式域名 | `https://www.boyamingge.com` |

> 以上任一项未修改，后端会在 `APP_ENV=production` 时因校验失败而**拒绝启动**。

### 3. mock → live 切换（4 项）

以下四项默认走 mock 模式，仅用于演示，不会发生真实调用。上线后按业务需要逐项切换：

| 配置项 | mock 行为 | 切 live 方法 | 验证方法 |
|---|---|---|---|
| **LLM 内容生成**（`LLM_MOCK_MODE`） | 用本地模板生成文章，不调用外部 API | 设 `LLM_MOCK_MODE=false` 并填 `DEEPSEEK_API_KEY` | 后台新建文章时日志出现 `deepseek` 调用，非 `mock_llm` |
| **运营指标**（`METRICS_PROVIDER`） | 返回演示数据，dashboard 数字非真实 | 设 `METRICS_PROVIDER=live` 并填 `BAIDU_TONGJI_TOKEN` + `BAIDU_TONGJI_SITE_ID` | 后台 dashboard 数字与百度统计后台一致 |
| **热线外呼**（`HOTLINE_PROVIDER`） | 线索仅入库排队，不触发真实外呼 | 设 `HOTLINE_PROVIDER=live` 并填 `TIANRUN_API_KEY` + `TIANRUN_API_BASE` + `TIANRUN_AGENT_ID` + `TIANRUN_EXT_ID` | 新线索提交后，天润融通座席收到外呼任务 |
| **渠道分发**（`DISTRIBUTE_MODE`） | 不生成外链，线索只入本地库 | 设 `DISTRIBUTE_MODE=live`，并确认 `WORKBENCH_BASE_URL` / `PACKAGES_BASE_URL` 为真实地址 | 线索详情页出现"分发到工作台"链接，点击跳转真实工作台 |

> ⚠️ 正式生产默认必须全部切到 live 并填写真实值，否则后端启动会拒绝服务。

### 4. 城市二级域名模式

通过 `NEXT_PUBLIC_CITY_DOMAIN_MODE` 控制多城市 URL 结构：

| 模式 | 值 | URL 形态 | 示例 |
|---|---|---|---|
| 子域名模式（推荐） | `subdomain` | `{city}.{root_domain}` | `guangzhou.boyamingge.com` |
| 路径模式 | `path` | `www.{root_domain}/{city}` | `www.boyamingge.com/guangzhou` |

**路径 → 子域名 301 跳转**

当 `ENABLE_CITY_PATH_REDIRECT=true` 且城市域名模式为 `subdomain` 时，访问路径形式的城市 URL 会自动 301 跳转到对应子域名：

```
请求：GET https://www.boyamingge.com/guangzhou
响应：301 → https://guangzhou.boyamingge.com
```

> 该跳转用于在切换到子域名模式后，保留旧路径链接的 SEO 权重。生产环境稳定后建议开启。

## 五、运维操作

### 日常运维命令

```bash
# 查看日志
docker compose --env-file .env.production logs -f fastapi
docker compose --env-file .env.production logs -f nginx --tail=100

# 重启单个服务
docker compose --env-file .env.production restart fastapi

# 重新构建（代码更新后）
docker compose --env-file .env.production build fastapi && docker compose --env-file .env.production up -d fastapi

# 进入容器排查
docker compose --env-file .env.production exec fastapi sh
docker compose --env-file .env.production exec postgres psql -U postgres boyamingge
```

### 数据库备份

```bash
# 手动备份
bash scripts/backup.sh

# 定时备份（crontab -e 添加）
0 3 * * * cd /opt/boyamingge && bash scripts/backup.sh >> /var/log/backup.log 2>&1
```

备份文件存放在 `./backups/` 目录，默认保留 7 天；脚本同时执行 gzip 完整性检查并生成 SHA-256 校验文件。

### 数据库恢复

```bash
# 必须显式确认。脚本会校验备份、先做恢复前安全备份、停止写入、恢复并执行迁移。
bash scripts/restore.sh backups/boyamingge_20260715_030001.sql.gz --yes
```

### 升级流程

```bash
# 1. 拉取新代码
git pull

# 2. 备份当前数据库
bash scripts/backup.sh

# 3. 重建并启动
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d

# 4. 验证
SMOKE_ADMIN_PASSWORD='<后台管理员密码>' python scripts/smoke_test.py --site-base http://localhost --expect-empty
curl http://localhost/health
```

## 六、安全加固清单

部署到生产前请逐项确认：

- [ ] `APP_ENV=production`
- [ ] `JWT_SECRET_KEY` 已替换为 ≥32 字符随机串
- [ ] `POSTGRES_PASSWORD` 已替换为强密码
- [ ] `OAUTH2_CLIENT_SECRET` 已替换为强密码
- [ ] `CORS_ORIGINS` 已改为具体域名（非 `*`）
- [ ] `SITE_BASE_URL` 已改为实际域名
- [ ] 已创建非默认首个管理员，且 `INITIAL_ADMIN_PASSWORD` 已从部署环境移除
- [ ] DeepSeek、百度统计、天润融通和分发地址均为 live 真实配置
- [ ] 客服 Redis 健康检查返回 `storage=redis`
- [ ] 外部发布所需 Chromium 就绪，`/ready` 的 `publish_runtime.ok=true`
- [ ] HTTPS 证书已配置，HTTP 自动跳转 HTTPS
- [ ] `/docs` `/redoc` `/openapi.json` 已在生产环境关闭（APP_ENV=production 自动关闭）
- [ ] 防火墙仅开放 80/443 端口，PostgreSQL/Redis/Backend 端口不对外
- [ ] `docker-compose.yml` 中 `127.0.0.1:` 端口前缀已保留（或移除调试端口映射）
- [ ] 服务器 SSH 仅允许密钥登录

## 七、服务端口与依赖

| 服务 | 容器内端口 | 宿主机映射 | 说明 |
|---|---|---|---|
| nginx | 80 / 443 | 80 / 443 | 入口，对外暴露 |
| fastapi | 8000 | 127.0.0.1:8000 | 仅本地调试，生产走 nginx |
| nextjs | 3000 | 127.0.0.1:3002 | 仅本地调试 |
| postgres | 5432 | 127.0.0.1:5433 | 仅本地调试 |
| redis | 6379 | 127.0.0.1:6379 | 仅本地调试 |
| Prometheus | 9090 | 127.0.0.1:9090 | `monitoring` profile |
| Alertmanager | 9093 | 127.0.0.1:9093 | `monitoring` profile |
| Grafana | 3000 | 127.0.0.1:3101 | `monitoring` profile，必须改密码 |

## 八、健康检查与监控

- **存活检查**：`GET /health` 返回 `{"status":"ok"}`
- **生产就绪检查**：`GET /ready` 校验数据库、Redis、上传目录和发布浏览器
- **指标端点**：`GET /metrics` 输出 Prometheus 指标
- **监控栈**：`docker compose --env-file .env.production --profile monitoring up -d`
- **Docker HEALTHCHECK**：所有服务均配置健康检查，`docker compose ps` 可查看状态
- **日志轮转**：所有服务 `json-file` 驱动，单文件 10MB，保留 3 份
- **应用日志**：通过 `docker compose logs` 查看

建议生产环境额外接入：
- Sentry / 自建日志系统（应用错误监控）
- Uptime Kuma（HTTP 探活告警）
- 将 Alertmanager 接入企业微信、邮件或 PagerDuty 告警接收器

## 九、常见问题排查

### 容器启动失败：`RuntimeError: 生产环境配置校验失败`

`config.py` 在 `APP_ENV=production` 时强制校验密钥/CORS/域名，失败则拒绝启动。按报错信息修改 `.env`。

### 数据库迁移失败

```bash
# 查看迁移状态
docker compose --env-file .env.production exec fastapi alembic current
docker compose --env-file .env.production exec fastapi alembic history

# 手动执行迁移
docker compose --env-file .env.production exec fastapi alembic upgrade head

# 回滚到上一版本
docker compose --env-file .env.production exec fastapi alembic downgrade -1
```

### 前端构建失败

```bash
# 清理缓存重建
docker compose --env-file .env.production build --no-cache nextjs
```

### Nginx 502 Bad Gateway

```bash
# 检查后端是否健康
docker compose --env-file .env.production ps fastapi
docker compose --env-file .env.production logs --tail=50 fastapi
```

### 小程序请求失败

1. 确认后端域名已加入小程序合法域名
2. 确认域名使用 HTTPS
3. 确认 `miniprogram/config.js` 的 `BASE_URL` 配置正确

## 十、回滚方案

```bash
# 1. 使用校验过的备份恢复数据库（脚本会控制应用写入）
bash scripts/restore.sh backups/boyamingge_YYYYMMDD_030001.sql.gz --yes

# 2. 切换到上一个版本代码
git checkout <previous-tag>

# 3. 重建并启动
docker compose --env-file .env.production build && docker compose --env-file .env.production up -d
```

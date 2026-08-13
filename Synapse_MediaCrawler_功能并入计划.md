# 博雅敏格 SEO/GEO 双引擎智能体：SynapseAutomation + MediaCrawler 源码内嵌计划

## 结论

可以直接搬进本项目，但要搬“功能引擎”，不是搬两个独立后台。

本项目是 SEO/GEO 内容生产、官网发布、经销商线索和内容分发系统。SynapseAutomation 应迁成社媒发布执行模块，MediaCrawler 应迁成社媒数据采集模块。用户只在博雅敏格后台操作，不打开 SynapseAutomation 或 MediaCrawler。

不走外部服务调用，不保留 `127.0.0.1:7000`、`127.0.0.1:18080` 这种运行依赖。后端直接 import 迁入的内部模块，浏览器自动化和爬虫任务由本项目自己的 worker 执行。

## 项目落点

主项目：

`C:\Users\uu\Desktop\归档\博雅敏格_SEO_GEO_双引擎智能体`

现有关键文件：

- 后端发布服务：`backend/app/services/publish_service.py`
- 后端分发服务：`backend/app/services/distribute_service.py`
- 后端指标服务：`backend/app/services/metrics_service.py`
- 后端模型：`backend/app/models/__init__.py`
- 后端发布 schema：`backend/app/schemas/publish.py`
- 后端 API 路由：`backend/app/api/v1/router.py`
- 前端后台入口：`frontend/app/admin/page.tsx`
- 前端后台布局：`frontend/app/admin/layout.tsx`
- 前端后台侧栏：`frontend/components/admin/AdminSidebar.tsx`
- 前端 API 工具：`frontend/lib/api.ts`

源项目：

- SynapseAutomation：`D:\social-auto-stack\SYNAPSEAUTOMATION`
- MediaCrawler：`D:\social-auto-stack\MediaCrawler`

不要改 `.next`、`node_modules`、构建缓存。

## 迁入目录建议

在博雅敏格后端新增：

```text
backend/app/integrations/
  synapse_engine/
    accounts/
    files/
    publish/
    platforms/
    workers/
    utils/
  mediacrawler_engine/
    crawlers/
    platforms/
    stores/
    workers/
    utils/
```

新增业务服务：

```text
backend/app/services/
  social_publish_service.py
  embedded_synapse_service.py
  embedded_mediacrawler_service.py
  social_data_service.py

backend/app/workers/
  social_publish_worker.py
  crawler_worker.py
```

## Synapse 迁入范围

优先迁入：

- 扫码登录
- Cookie 管理和账号状态
- 视频素材上传和文件记录
- 平台标题、描述、话题适配
- 批量发布、定时发布、间隔发布
- 发布任务队列
- Playwright 浏览器发布 worker
- 平台发布器：小红书、视频号、抖音、快手、B站

重点源代码位置：

- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\app_new\platforms`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\fastapi_app\api\v1\files`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\fastapi_app\api\v1\publish`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\fastapi_app\schemas`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\myUtils\cookie_manager.py`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\myUtils\platform_metadata_adapter.py`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\myUtils\task_queue_manager.py`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\playwright_worker`
- `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend\utils\playwright_provider.py`

平台编码保留：

```text
1 = xiaohongshu
2 = channels
3 = douyin
4 = kuaishou
5 = bilibili
```

重要限制：

本项目内容多是 Markdown/SEO 文章，而 Synapse 更偏视频发布。第一版要增加“社媒素材化”步骤：

- 从文章生成社媒标题、描述、话题
- 选择或上传视频素材
- 必要时生成短视频脚本
- 如果平台发布器不支持图文，前端必须提示需要视频素材

## MediaCrawler 迁入范围

第一版只迁 MediaCrawler，不迁 XHS-Downloader 和 Douyin_TikTok_Download_API。

优先迁入：

- 平台采集器
- 关键词/账号采集
- 采集状态和日志
- 数据落盘
- `.jsonl/.json/.csv/.xlsx` 解析
- 数据导入指标体系

重点源代码位置：

- `D:\social-auto-stack\MediaCrawler\base`
- `D:\social-auto-stack\MediaCrawler\media_platform`
- `D:\social-auto-stack\MediaCrawler\model`
- `D:\social-auto-stack\MediaCrawler\store`
- `D:\social-auto-stack\MediaCrawler\tools`
- `D:\social-auto-stack\MediaCrawler\config`
- `D:\social-auto-stack\MediaCrawler\api\routers\crawler.py`
- `D:\social-auto-stack\MediaCrawler\api\routers\data.py`
- `D:\social-auto-stack\MediaCrawler\tools\app_runner.py`

MediaCrawler 原 WebUI API 只作为参考，不作为最终运行方式。

## 后端改造计划

### 1. 配置项

在 `backend/app/core/config.py` 增加项目内嵌配置，字段名按当前项目风格调整：

```python
social_publish_mode: str = "synapse_embedded"
synapse_embedded_enabled: bool = True
synapse_storage_dir: str = "data/synapse"
synapse_browser_profile_dir: str = "data/browser_profiles"
synapse_playwright_headless: bool = False

crawler_provider: str = "mediacrawler_embedded"
mediacrawler_data_dir: str = "data/mediacrawler"
mediacrawler_default_save_format: str = "jsonl"
```

不要新增 `synapse_base_url`、`mediacrawler_base_url`。

### 2. 新增社媒发布服务

新增：

`backend/app/services/social_publish_service.py`

职责：

1. 读取 `Content`。
2. 从 Markdown 生成社媒标题、描述、话题。
3. 检查或创建 `SocialMaterial`。
4. 创建内部文件记录。
5. 创建 `Publication` 和发布任务。
6. 投递本项目 worker。
7. 同步状态和失败原因。

`publish_service.py` 继续负责官网发布，不要把官网发布和社媒发布混成一个函数。

### 3. 嵌入 Synapse 引擎

新增：

`backend/app/services/embedded_synapse_service.py`

职责：

- 管理账号 Cookie
- 管理素材文件
- 生成内部 `file_id`
- 准备平台发布参数
- 调用迁入后的平台发布器
- 给 worker 提供执行入口

这里不写外部 HTTP 客户端。

### 4. 后台 worker

Playwright 任务必须进入后台 worker，不要在普通 API 请求里直接跑。

新增：

- `backend/app/workers/social_publish_worker.py`
- `backend/app/workers/crawler_worker.py`

如果项目已有任务队列，复用现有队列；没有的话，先提供独立 worker 命令。

### 5. 数据表

建议新增：

`SocialAccount`

- `id`
- `platform`
- `platform_code`
- `display_name`
- `internal_account_id`
- `cookie_status`
- `cookie_path`
- `last_login_at`
- `status`
- `raw`

`SocialMaterial`

- `id`
- `content_id`
- `filename`
- `local_path`
- `internal_file_id`
- `file_type`
- `size_mb`
- `status`
- `created_at`

扩展 `Publication` 或新增 `SocialPublicationTask`：

- `content_id`
- `publication_id`
- `platform`
- `platform_code`
- `social_account_id`
- `internal_file_id`
- `worker_task_id`
- `status`
- `error_message`
- `scheduled_at`
- `started_at`
- `finished_at`
- `raw_response`

MediaCrawler 数据表：

`SocialCrawlerJob`

- `id`
- `platform`
- `keyword`
- `account_ref`
- `city`
- `status`
- `save_path`
- `error_message`
- `created_at`
- `finished_at`

`SocialCrawlerItem`

- `id`
- `job_id`
- `platform`
- `author`
- `title`
- `content`
- `url`
- `publish_time`
- `likes`
- `comments`
- `collects`
- `shares`
- `city`
- `raw`

### 6. API 路由

在 `backend/app/api/v1/router.py` 接入新接口，或拆成新文件：

- `backend/app/api/v1/social.py`
- `backend/app/api/v1/crawler.py`

建议接口：

- `GET /social/accounts`
- `POST /social/accounts/login/start`
- `GET /social/accounts/login/status`
- `POST /social/accounts/sync`
- `POST /social/materials`
- `POST /social/publish`
- `GET /social/publications`
- `POST /social/publications/{id}/sync`
- `POST /social/publications/{id}/retry`
- `POST /crawler/jobs`
- `POST /crawler/jobs/{id}/stop`
- `GET /crawler/jobs/{id}`
- `GET /crawler/data/files`
- `POST /crawler/data/import`

所有接口都由本项目提供，内部走迁入模块。

## 前端改造计划

修改：

- `frontend/components/admin/AdminSidebar.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/lib/api.ts`

新增后台 tab 或页面：

- 社媒账号
- 社媒素材
- 社媒发布
- 数据采集

内容页新增按钮：

- `生成社媒稿`
- `上传/选择视频素材`
- `发布到社媒`
- `查看发布任务`

社媒发布弹窗字段：

- 平台
- 账号
- 素材
- 标题
- 描述
- 话题
- 定时发布时间
- 间隔发布
- 去重开关

数据采集页字段：

- 平台
- 关键词
- 账号链接
- 城市
- 启动采集
- 停止采集
- 日志
- 数据文件
- 导入数据

指标页增加：

- 社媒发布数
- 发布成功率
- 失败任务
- 各平台互动数据
- 城市维度热度
- 竞品/关键词采集结果

## 推荐工作流

```text
内容生成
  -> 生成社媒稿
  -> 选择或上传视频素材
  -> 选择平台和账号
  -> 创建本项目内部发布任务
  -> worker 执行迁入后的 Synapse 发布器
  -> Publication 写入状态
  -> 迁入后的 MediaCrawler 拉取数据
  -> 回写指标和内容策略
```

## 不要做的事

- 不要通过 `127.0.0.1:7000` 调 Synapse。
- 不要通过 `127.0.0.1:18080` 调 MediaCrawler。
- 不要把 Synapse 前端 iframe 到后台。
- 不要把 MediaCrawler WebUI iframe 到后台。
- 不要把官网发布和社媒发布混成一个函数。
- 不要把 Markdown 文章直接当视频发布。
- 不要第一版迁 XHS-Downloader 和 Douyin_TikTok_Download_API。
- 不要改 `.next`、`node_modules`、构建缓存。

## 实施阶段

### 阶段 1：社媒发布最小闭环

目标：不启动 Synapse 原服务，从博雅敏格后台创建本项目内部发布任务。

任务：

1. 迁入 Synapse 文件、账号、平台发布器、队列核心代码。
2. 新建 `embedded_synapse_service.py`。
3. 新建 `social_publish_service.py`。
4. 新增 `SocialAccount`、`SocialMaterial`、`SocialPublicationTask`。
5. 新增社媒发布 API。
6. 后台内容页加发布按钮和弹窗。
7. 新增发布 worker。

验收：

- 用户只打开博雅敏格后台。
- 不启动 Synapse 原前端和原后端。
- 能创建发布任务并写入 `Publication`。

### 阶段 2：扫码登录源码迁入

目标：在本项目后台完成账号登录。

任务：

1. 迁入登录和 Cookie 管理模块。
2. 新增社媒账号页。
3. 增加二维码弹窗。
4. 登录成功后同步账号状态。

验收：

- 后台账号页完成扫码登录。
- Cookie 状态可见。

### 阶段 3：MediaCrawler 源码迁入

目标：本项目后台能启动采集并导入结果。

任务：

1. 迁入 MediaCrawler crawler、platform、store、tools。
2. 新建 `embedded_mediacrawler_service.py`。
3. 新建 crawler worker。
4. 后台新增数据采集页。
5. 支持 `.jsonl/.json/.csv` 导入。

验收：

- 不启动 MediaCrawler 原服务。
- 后台能启动采集任务。
- 导入后指标页出现社媒数据。

### 阶段 4：状态同步和看板

目标：发布和采集数据完整回流。

任务：

1. Publication 状态同步。
2. 失败任务展示原因。
3. 支持重试。
4. 指标页展示社媒数据。

验收：

- 社媒发布、账号、素材、采集、指标都在本项目闭环。

## 交给下一个会话的执行提示

按源码内嵌做，不要写外部 HTTP 客户端。第一步只做“内容 -> 社媒素材 -> 内部发布任务 -> worker 执行迁入后的 Synapse 发布器 -> 写 Publication”。跑通后再做扫码登录和 MediaCrawler。

## 完整功能清单

最终用户只在博雅敏格后台操作，不看到 Synapse 或 MediaCrawler 独立页面。

### 社媒账号

- 平台账号列表：小红书、视频号、抖音、快手、B站。
- 扫码登录。
- Cookie 状态。
- 重新登录。
- 账号启用/停用。
- 账号绑定业务城市/门店/经销商。
- 账号发布能力提示。

### 社媒素材

- 给文章选择视频素材。
- 上传视频素材。
- 上传封面图。
- 检测素材格式。
- 生成首帧封面。
- 显示内部 `file_id`。
- 素材和 `Content` 绑定。

### 社媒稿生成

- 从 Markdown 生成短标题。
- 从 Markdown 生成平台描述。
- 生成话题。
- 生成短视频脚本。
- 保留人工编辑。
- 不同平台可单独改标题、描述、话题。

### 社媒发布

- 从内容详情点击 `发布到社媒`。
- 选择平台。
- 选择账号。
- 选择素材。
- 选择定时发布时间。
- 设置间隔发布。
- 设置去重。
- 创建发布任务。
- 写入 `Publication`。

### 发布任务

- 任务列表。
- 批次列表。
- 任务状态。
- 失败原因。
- 重试。
- 取消。
- 日志。
- 关联内容、城市、门店、经销商。

### 数据采集

- 按关键词采集。
- 按账号采集。
- 按城市/业务标签采集。
- 查看任务日志。
- 查看采集文件。
- 导入采集数据。
- 采集结果进入指标服务和内容策略。

### 指标看板

- 社媒发布量。
- 发布成功率。
- 失败任务数。
- 平台互动数据。
- 城市维度热度。
- 关键词热度。
- 竞品内容表现。

## 源码迁移明细

### Synapse 必迁模块

从 `D:\social-auto-stack\SYNAPSEAUTOMATION\syn_backend` 迁入并改包名：

- `app_new/platforms/*`：平台登录和发布器。
- `utils/playwright_provider.py`
- `utils/playwright_bootstrap.py`
- `utils/video_probe.py`
- `utils/video_frames.py`
- `myUtils/cookie_manager.py`
- `myUtils/platform_metadata_adapter.py`
- `myUtils/task_queue_manager.py`
- `playwright_worker/*`
- `fastapi_app/api/v1/files/services.py` 作为文件服务参考。
- `fastapi_app/api/v1/publish/services.py` 作为发布策略参考。
- `fastapi_app/schemas/publish.py`、`fastapi_app/schemas/account.py` 作为请求结构参考。

迁入目录：

```text
backend/app/integrations/synapse_engine/
```

适配要求：

- import 改成本项目路径。
- 原 DB 访问改成本项目 SQLAlchemy 模型。
- 文件目录改到 `data/synapse`。
- 浏览器 profile 改到 `data/browser_profiles`。
- 日志改成本项目 logger。
- 配置改成本项目 settings。
- 原 FastAPI router 不直接迁，只迁 service/engine 逻辑。

### MediaCrawler 必迁模块

从 `D:\social-auto-stack\MediaCrawler` 迁入：

- `base/*`
- `media_platform/*`
- `model/*`
- `store/*`
- `tools/*`
- `config/*`
- `tools/app_runner.py`
- `api/routers/crawler.py` 作为采集任务参考。
- `api/routers/data.py` 作为数据文件参考。

迁入目录：

```text
backend/app/integrations/mediacrawler_engine/
```

适配要求：

- 原命令行启动改成 service/worker。
- 数据目录改到 `data/mediacrawler`。
- 采集结果写入本项目数据库。
- 支持 `.jsonl/.json/.csv/.xlsx`。
- 不依赖 MediaCrawler 原 WebUI。

## 数据库迁移清单

新增模型建议：

```text
SocialAccount
SocialMaterial
SocialPublicationTask
SocialPublishLog
SocialCrawlerJob
SocialCrawlerItem
SocialCrawlerImportLog
```

扩展或关联现有模型：

- `Content`：关联社媒素材和发布任务。
- `Publication`：记录社媒发布结果。
- `City`：采集数据可绑定城市。
- `Dealer`：账号或任务可绑定经销商。

状态枚举建议：

```text
account: active / expired / missing_cookie / disabled
material: pending / ready / invalid / deleted
publication_task: pending / scheduled / running / success / failed / cancelled
crawler_job: pending / running / success / failed / stopped
```

## 前端页面和按钮落点

### `frontend/components/admin/AdminSidebar.tsx`

新增后台入口：

- 社媒账号
- 社媒素材
- 社媒发布
- 数据采集

### `frontend/app/admin/page.tsx`

如果当前后台是 tab 工作台，在这里新增 tab：

- `social-accounts`
- `social-materials`
- `social-publish`
- `social-crawler`

### `frontend/lib/api.ts`

新增 API 方法：

- `listSocialAccounts`
- `startSocialLogin`
- `getSocialLoginStatus`
- `syncSocialAccounts`
- `uploadSocialMaterial`
- `generateSocialDraft`
- `publishToSocial`
- `listSocialPublications`
- `retrySocialPublication`
- `startCrawlerJob`
- `stopCrawlerJob`
- `listCrawlerJobs`
- `importCrawlerData`

### 内容管理区域

新增按钮：

- `生成社媒稿`
- `选择素材`
- `发布到社媒`
- `查看发布任务`

发布弹窗字段：

- 平台。
- 账号。
- 素材。
- 标题。
- 描述。
- 话题。
- 定时发布时间。
- 间隔发布。
- 去重。

### 社媒账号页面

包含：

- 平台筛选。
- 账号列表。
- Cookie 状态。
- 扫码登录弹窗。
- 重新登录。
- 绑定城市/门店/经销商。

### 社媒素材页面

包含：

- 上传素材。
- 选择已有素材。
- 素材格式检测。
- 封面生成。
- 绑定内容。

### 社媒发布页面

包含：

- 批次列表。
- 任务列表。
- 状态筛选。
- 失败原因。
- 重试。
- 日志。

### 数据采集页面

包含：

- 平台选择。
- 关键词输入。
- 账号链接输入。
- 城市选择。
- 启动采集。
- 停止采集。
- 日志。
- 数据文件。
- 导入数据。

## 依赖处理计划

执行前比对：

- 本项目 `backend/requirements.txt`
- Synapse `syn_backend/requirements.txt`
- MediaCrawler `pyproject.toml`

重点合并：

- `playwright`
- `celery` 或本项目已有任务队列
- `redis`
- `aiofiles`
- `pandas`
- `openpyxl`
- `ffmpeg-python` 或系统 `ffmpeg`
- `httpx`
- `pydantic`
- `sqlalchemy`

注意：

- 不要整包覆盖依赖。
- Playwright 浏览器安装要写入部署说明。
- FFmpeg 可能需要单独安装。

## 完整执行顺序

1. 新建 `backend/app/integrations/synapse_engine`。
2. 新建 `backend/app/integrations/mediacrawler_engine`。
3. 迁入 Synapse 平台发布器和工具模块。
4. 修正 import、配置、日志、路径。
5. 新增社媒账号、素材、发布任务模型。
6. 新增 `embedded_synapse_service.py`。
7. 新增 `social_publish_service.py`。
8. 新增发布 worker。
9. 新增社媒 API。
10. 后台内容区加社媒稿和发布按钮。
11. 后台新增社媒账号页。
12. 后台新增社媒素材页。
13. 后台新增社媒发布页。
14. 迁入 MediaCrawler 核心模块。
15. 新增采集模型。
16. 新增 `embedded_mediacrawler_service.py`。
17. 新增采集 worker。
18. 后台新增数据采集页。
19. 指标页接社媒发布和采集数据。
20. 端到端验收。

## 验收标准

必须满足：

- 不启动 Synapse 原后端。
- 不启动 Synapse 原前端。
- 不启动 MediaCrawler 原 WebUI。
- 博雅敏格后台能扫码登录社媒账号。
- 博雅敏格后台能上传或选择社媒素材。
- 博雅敏格后台能从文章生成社媒稿。
- 博雅敏格后台能创建发布任务。
- 发布结果写入 `Publication`。
- 后台能看到任务状态和失败原因。
- 后台能启动采集任务。
- 采集结果能进入指标页。

## 风险点

- 文章内容不能直接等同视频素材，需要社媒素材化。
- 平台页面变化会导致发布器失效。
- Cookie 可能失效或触发风控。
- Playwright 不能放在普通 API 请求里执行。
- 采集频率过高可能被限制。
- 源项目依赖要逐项合并，不能覆盖。

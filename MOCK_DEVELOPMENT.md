# 博雅敏格 SEO-GEO 双引擎智能体 — Mock 开发文档

## 1. 如何开启 Mock Provider

项目默认所有外部 Provider 均为 `mock` 模式，无需任何额外配置即可启动全流程演示。

在 `.env` 文件或环境变量中控制：

```bash
# .env 默认值（无需修改即可使用 mock）
LLM_MOCK_MODE=true
METRICS_PROVIDER=mock
HOTLINE_PROVIDER=mock
DISTRIBUTE_MODE=mock
```

如果 `.env` 中未设置，代码中的默认值也是 `mock`，开箱即用。

---

## 2. 每个 Provider 模拟什么

| Provider | 环境变量 | Mock 行为 | 对应文件 |
|----------|----------|-----------|----------|
| **LLM** | `LLM_MOCK_MODE=true` | 根据城市+意图生成模板化 SEO 长文 / GEO 摘要，包含本地案例、气候特点、选购要点 | `backend/app/services/llm.py` |
| **运营指标** | `METRICS_PROVIDER=mock` | 返回广州/深圳/北京 7 天趋势数据（UV、排名、线索量、CPL），叠加数据库真实线索数 | `backend/app/services/metrics_service.py` |
| **热线外呼** | `HOTLINE_PROVIDER=mock` | 仅入库排队，生成 `CALL-YYYYMMDD-NNN` 格式的 call_id，不拨打真实电话 | `backend/app/services/hotline_service.py` |
| **渠道分发** | `DISTRIBUTE_MODE=mock` | 生成 `demo://confirm/TOKEN` 格式的确认链接，不创建真实外链 | `backend/app/services/distribute_service.py` |

### LLM Mock 内容说明

- **SEO 长文**：根据城市气候、服务类型、本地案例生成完整 Markdown，包含标题、案例、参数、价格参考
- **GEO 摘要**：1-2 段城市定制化摘要，包含气候特点、推荐产品、案例引用
- **Schema 页面**：通过模板生成 JSON-LD 结构化数据（Organization + LocalBusiness + FAQPage）
- 内容自动通过 EEAT 评分，≥70 分自动 approved，否则 rejected

---

## 3. 如何切换真实 Provider

### 切换 LLM（DeepSeek）

```bash
# .env
LLM_MOCK_MODE=false
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
```

切换后 SEO P0/P1 内容调用 DeepSeek V3，GEO 内容调用 Ollama qwen2.5:7b。

### 切换运营指标（百度统计 / ClickHouse）

```bash
METRICS_PROVIDER=live
BAIDU_TONGJI_TOKEN=your_token_here
```

> 注意：`_fetch_live_metrics()` 函数目前为预留接口，需在此函数内实现百度统计或 ClickHouse 的 HTTP 调用。

### 切换热线外呼（天润融通）

```bash
HOTLINE_PROVIDER=live
TIANRUN_API_KEY=your_key
TIANRUN_API_BASE=https://api.tianrun.com/v1
```

> 注意：`_push_hotline_live()` 函数目前为预留接口，需实现天润融通 HTTP 调用。

### 切换渠道分发

```bash
DISTRIBUTE_MODE=live
WORKBENCH_BASE_URL=https://workbench.yourdomain.com
PACKAGES_BASE_URL=https://packages.yourdomain.com
```

切换后 L1 分发生成真实确认链接，L2 辅助包生成真实下载链接。

---

## 4. Seed 数据有哪些

应用启动时（`lifespan`）自动执行 seed，已有数据则跳过。

| 数据 | 数量 | 说明 |
|------|------|------|
| 用户 | 5 | admin / operator / dealer_gz / dealer_sz / dealer_bj |
| 经销商 | 3 | 广州、深圳、北京各 1 个 |
| 城市 | 5 | 广州、深圳、北京、佛山、东莞 |
| 门店 | 9 | 广州3家、深圳2家、北京2家、佛山1家、东莞1家 |
| 城市案例 | 11 | 每个城市 2-3 个安装案例 |
| 城市 FAQ | 15 | 每个城市 3 个常见问题 |
| 知识库文档 | 8 | 产品参数、选型指南、安装流程、城市案例、选购指南 |
| 线索 | 8 | 覆盖 new / queued / contacted / converted 状态 |
| 内容 | 9 | SEO 长文 6 篇 + GEO 摘要 3 篇 |
| 发布记录 | 19 | 覆盖 L0/L1/L2 三层分发 |
| 素材 | 7 | 经销商上传的案例图片 |

---

## 5. 测试脚本怎么跑

### 冒烟测试

```bash
# 确保后端已启动
python scripts/smoke_test.py --api-base http://localhost:8000
```

测试覆盖 15 个检查点：健康检查、登录、知识库 CRUD、城市定位、门店列表、线索提交、内容生成、权限验证等。

### 单元测试

```bash
cd backend
pytest tests/ -v
```

### 一键重置

```bash
cd backend
python -m scripts.reset_dev_data
```

---

## 6. 当前哪些是假数据、哪些是真数据库数据

### 真数据库数据（PostgreSQL）

- 用户账号与密码哈希
- 经销商信息
- 城市与门店
- 知识库文档与分块（KnowledgeDocument + KnowledgeChunk）
- 线索（Lead）
- 内容与发布记录（Content + Publication）
- 素材（Material）
- 通话记录（CallRecord）

### 假数据（Mock Provider 生成）

- LLM 生成的文章内容（mock 模式下为模板生成，非真实 AI 输出）
- 运营指标趋势数据（硬编码在 `MOCK_METRICS` 字典中）
- 热线外呼结果（仅入库，无真实拨打）
- 渠道分发链接（`demo://` 协议，非真实 URL）
- EEAT 评分（基于规则引擎打分，非 AI 评审）

---

## 7. 后续接真实 API 要替换哪些文件

| Provider | 需修改文件 | 说明 |
|----------|-----------|------|
| LLM | `backend/app/services/llm.py` | `_call_deepseek()` 和 `_call_ollama()` 已实现，设置 `LLM_MOCK_MODE=false` + API Key 即可 |
| 运营指标 | `backend/app/services/metrics_service.py` | 在 `_fetch_live_metrics()` 中实现百度统计 / ClickHouse 调用 |
| 热线外呼 | `backend/app/services/hotline_service.py` | 在 `_push_hotline_live()` 中实现天润融通 HTTP 调用 |
| 渠道分发 | `backend/app/services/distribute_service.py` | 设置 `WORKBENCH_BASE_URL` 和 `PACKAGES_BASE_URL` 为真实域名 |
| EEAT 评分 | `backend/app/services/eeat.py` | 当前为规则引擎，可替换为 AI 评审 |

---

## 8. 测试账号和权限

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| `admin` | `admin123` | 管理员 | 全部权限：知识库管理、内容生成、线索管理、指标查看、用户管理 |
| `operator` | `operator123` | 运营 | 知识库管理、内容生成、线索管理、指标查看 |
| `dealer_gz` | `dealer123` | 经销商 | 仅查看本城市线索、上传素材、确认分发任务 |
| `dealer_sz` | `dealer123` | 经销商 | 仅查看深圳相关数据 |
| `dealer_bj` | `dealer123` | 经销商 | 仅查看北京相关数据 |

### 权限规则

- 经销商角色无法访问知识库管理接口（返回 403）
- 经销商只能查看所属城市的线索
- 内容生成和发布仅 admin / operator 可操作

---

## 9. 业务状态机

### 线索流程

```
new → assigned → contacted → measured → deal → lost
 │                                    ↑        ↑
 └── queued（热线外呼排队）────────────┘        │
 └── converted（已成交）────────────────────────┘
```

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `new` | 新线索 | 用户网站留资 |
| `queued` | 排队中 | 热线外呼系统入队 |
| `assigned` | 已分配 | 系统按城市+激活分数分配经销商 |
| `contacted` | 已联系 | 经销商确认已联系客户 |
| `measured` | 已测量 | 上门测量完成 |
| `deal` | 已成交 | 签约成功 |
| `converted` | 已转化 | 成交并完成安装 |
| `lost` | 已流失 | 客户放弃或超时未联系 |

### 内容流程

```
draft → generated → approved → published
                 └→ rejected → (修改后重新提交)
```

| 状态 | 含义 |
|------|------|
| `draft` | 草稿 |
| `approved` | EEAT ≥ 70 分，自动通过 |
| `rejected` | EEAT < 70 分，需修改 |

### 分发流程

```
pending → confirmed → published
       └→ rejected（经销商拒绝）
       └→ package_ready（L2 辅助包已就绪）
```

---

## 10. Mock 场景控制

通过 `MOCK_SCENARIO` 环境变量控制 Mock Provider 的行为：

```bash
MOCK_SCENARIO=normal    # 默认，正常返回
MOCK_SCENARIO=timeout   # 模拟超时
MOCK_SCENARIO=error     # 模拟错误返回
MOCK_SCENARIO=empty     # 返回空数据
MOCK_SCENARIO=no_store  # 无门店匹配
MOCK_SCENARIO=content_violation  # 内容违规
MOCK_SCENARIO=publish_fail       # 发布失败
MOCK_SCENARIO=notify_fail        # 通知失败
```

> 注意：SEO-GEO 项目的 `MOCK_SCENARIO` 目前主要在配置中预留，具体场景逻辑需在各 Provider 中实现。

---

## 11. 一键重置脚本

```bash
cd backend
python -m scripts.reset_dev_data
```

该脚本会：
1. 删除所有数据（按依赖反序）
2. 重新执行所有 seed 函数
3. 输出测试账号信息

重置后数据与首次启动一致。

---

## 12. 数据导入导出

### 导出

```bash
# 导出 PostgreSQL 数据
pg_dump -h localhost -U postgres boyamingge > backup.sql
```

### 导入

```bash
psql -h localhost -U postgres boyamingge < backup.sql
```

### 知识库单独导入

通过 API 批量创建知识库文档：

```bash
curl -X POST http://localhost:8000/api/v1/knowledge \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "doc_type": "product", "content": "...", "tags": [...]}'
```

---

## 13. Mock Provider 日志

所有 Mock Provider 的关键操作均通过 Python logging 输出：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

| Provider | 日志前缀 | 关键信息 |
|----------|----------|----------|
| LLM | 无独立 logger | 生成内容时打印 model、city、intent |
| 运营指标 | 无独立 logger | 查询时返回 `data_source` 字段标识 mock/live |
| 热线外呼 | 无独立 logger | call_id 和 assigned_dealer 在响应中返回 |
| 渠道分发 | 无独立 logger | `demo=True` 标识在响应中返回 |

---

## 14. 未完成事项和风险点

### 未完成

1. **运营指标 live 模式**：`_fetch_live_metrics()` 为预留接口，需实现百度统计 / ClickHouse 调用
2. **热线外呼 live 模式**：`_push_hotline_live()` 为预留接口，需实现天润融通调用
3. **MOCK_SCENARIO 场景实现**：各 Provider 尚未完整实现 timeout / error / empty 等场景的分支逻辑
4. **知识库向量检索**：当前使用关键词匹配 + 评分排序，未接入向量数据库（如 Milvus / pgvector）
5. **EEAT AI 评审**：当前为规则引擎打分，未接入 AI 评审模型
6. **内容缓存失效**：Redis 缓存无 TTL 自动过期，修改知识库后需手动清理

### 风险点

1. **Seed 数据幂等性**：seed 函数通过 `count() > 0` 判断是否跳过，新增 seed 数据需手动重置
2. **经销商编码硬编码**：`dealer_code` 格式为 `D2026{id:03d}`，依赖数据库自增 ID，重置后 ID 可能变化
3. **Mock 内容质量**：模板生成的内容仅用于演示，切换真实 LLM 后内容质量会有显著差异
4. **并发安全**：`reset_dev_data.py` 直接删除所有数据，生产环境禁止使用
5. **JWT Secret**：默认 `change-me-in-production`，必须在生产环境修改

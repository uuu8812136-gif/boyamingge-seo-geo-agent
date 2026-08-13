# 博雅敏格官网 · 前端 UI/UX 设计规范 Prompt

> 复制以下整段作为 Cursor / AI 设计迭代的系统提示，用于保持全站视觉与交互一致。

---

## 品牌与定位

- **品牌**：博雅敏格门窗 — 系统门窗 · 本地安装
- **业务**：广州 / 深圳 / 北京三城门店，上门测量、旧窗改造、封阳台、防盗门等
- **气质**：专业、可信、本地服务感；现代 SaaS 级信息层次，但不过度「科技冷」
- **禁忌**：假 3D 窗扇装饰、廉价渐变、纯 scale 按钮、低对比度文字、弹窗被顶栏遮挡

## 设计 Token（globals.css :root）

| Token | 值 | 用途 |
|-------|-----|------|
| `--accent` | `#c45c26` | 主色、CTA、强调 |
| `--accent-dark` | `#9a4520` | 标题强调、hover 深态 |
| `--accent-soft` | `#fdf0e8` | 浅底标签（**勿**在深色 Hero 内直接用作卡片底） |
| `--paper` | `#f7f5f2` | 页面背景 |
| `--surface` | `#ffffff` | 卡片、表单 |
| `--surface-alt` | `#f0ece6` | 交替区块 |
| `--ink` / `--ink-soft` / `--ink-muted` | 深灰阶 | 正文三级 |
| `--dark` | `#1c1916` | Hero、深色区块 |
| `--container` | `1200px` | 主容器 |
| `--header-height` | `76px` | 固定顶栏高度 |
| `--radius` / `--radius-sm` | `16px` / `10px` | 圆角 |
| `--shadow` / `--shadow-sm` | 柔和投影 | 卡片浮层 |
| `--ease-spring` | `cubic-bezier(0.22, 1, 0.36, 1)` | 动效曲线 |

## 布局节奏

1. **Hero（全宽）** → **Trust / Stats 条（-52px 叠入 Hero）** → **内容区块**
2. 区块间距：`section` 72px；紧凑区 `section-compact` 56px
3. 双栏：`grid-template-columns: repeat(2, minmax(0, 1fr))`；≤1100px 单列
4. 案例区：3 列 `case-showcase`；≤1100px 两列；≤640px 单列
5. 容器：`container`（1200px）/ `container-narrow`（760px 文章）

## 页面模板

### 首页
- `Header variant="overlay"` + `hero-banner` + `TrustBar` + Bento 服务 + 流程 + 案例 + 深色配置区 + 城市门店 + FAQ + CTA

### 城市分站（/guangzhou 等）
- `main.city-page`
- `page-hero page-hero--city`：左文案 + 右 `info-panel`（白底门店信息）
- `CityStatsBar`：四格数据条（区域数 / 服务数 / 案例数 / 热线）
- `city-split`：服务区域 + 服务项目 chip 卡
- 案例 3 列、`guide-split` 选窗建议、FAQ、`section-cta city-cta`

### 攻略列表 / 详情
- 列表：`page-hero--compact` + 分类筛选 + `article-grid`
- 详情：深色 `article-detail-head`；**阅读要点卡** 必须用白底 + `--ink` 文字（不可继承 Hero 白字）

### 运营后台
- 独立 `admin.css` 设计系统，勿与官网 globals 混用

## 组件规范

| 组件 | 要点 |
|------|------|
| `Header` | 固定顶栏；`overlay` 模式透明白字，滚动后 solid |
| `BookingButton` | 弹窗 **Portal 到 body**，z-index 200 |
| `ScrollReveal` | 滚动入场，尊重 `prefers-reduced-motion` |
| `SectionHead` | eyebrow + title + desc；城市内嵌块可 `reveal={false}` |
| `CaseCard` | 真实图片、标签、hover 微抬升 |
| `LeadForm` | 白底表单，focus 环 `--accent` |
| `TrustBar` / `CityStatsBar` | 四格 stats，叠入 Hero |

## 按钮与交互

- Primary：`btn btn-primary` — 橙渐变，hover 亮度 + 微 translateY
- Ghost（Hero 上）：`btn btn-ghost` — 半透明白边
- **禁止**纯 `transform: scale()` 作为唯一反馈
- Chip：`chip` / `chip-accent`；hover 微抬升 + 边框 accent

## 深色 Hero 内文字规则

- 标题、副标题：白色 / 半透明白
- **信息卡片**：必须 `background: rgba(255,255,255,0.97)` + `color: var(--ink)`
- 左侧 accent 边线 4px；标题用 `--accent-dark`
- `info-panel`、`article-summary-box` 均遵循此规则

## 动效

- 入场：opacity + translateY(24px)，stagger delay 60–90ms
- 卡片 hover：translateY(-2px ~ -4px) + shadow 加深
- Hero：可选视差 / 窗扇主题（`HeroMotion`），不干扰可读性

## SEO / 功能约束（前端）

- 不删城市页、文章内容、schema JSON-LD
- 不破坏 `LeadForm` / `BookingButton` API 与 defaultCity 传参
- `generateStaticParams` / metadata / sitemap / robots 保持有效
- 图片用 Next `Image`，真实路径 `/images/...`

## 响应式断点

- `1100px`：双栏 → 单列；城市 stats 条 2×2
- `1024px`：导航折叠
- `640px`：案例单列；表单单列

## 验收清单

- [ ] 首页 / 三城 / 攻略列表 / 攻略详情 / 后台 均可访问
- [ ] Hero 上顶栏 overlay 可读，滚动后 solid
- [ ] 弹窗不被 TrustBar / 顶栏遮挡
- [ ] 深色 Hero 内卡片文字对比度 ≥ WCAG AA
- [ ] `npm run build` 通过
- [ ] Docker：`docker compose build nextjs && docker compose up -d nextjs`

## 一句话 Prompt（精简版）

> 为博雅敏格门窗官网做 UI：暖纸色底 `#f7f5f2`、橙强调 `#c45c26`、容器 1200px。首页/城市/攻略采用「全宽 Hero → 四格 stats 叠层 → 白卡片内容区」节奏。深色 Hero 上的信息卡必须白底深字。按钮用 spring 微抬升，弹窗 Portal 到 body。保持 SEO 内容与 LeadForm/BookingButton 功能不变，风格专业可信、现代 SaaS 信息层次，禁止低对比度文字和假窗装饰。

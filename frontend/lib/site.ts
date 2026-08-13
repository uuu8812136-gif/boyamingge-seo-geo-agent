export const SITE = {
  brand: '博雅敏格',
  brandFull: '博雅敏格门窗',
  hotline: '400-888-6688',
  hotlineDisplay: '400-888-6688',
  description:
    '博雅敏格门窗提供防盗门、断桥铝、阳台封窗、隔音窗与旧窗改造咨询、测量、安装与售后服务。',
};

export const HERO = {
  title: '系统门窗安装与旧窗改造，先测量再定方案',
  subtitle: '封阳台、卧室隔音窗、防盗门、断桥铝和全屋门窗，需要结合现场条件确认配置与工期。',
};

export const HERO_IMAGE = '/images/cases/large-window-room.webp';

export const AI_SEARCH_PAIN_POINTS = [
  {
    pain: 'AI 搜索里没有可信身份',
    detail: '官网、门店、案例和联系方式分散，AI 很难确认哪个答案应该引用品牌。',
  },
  {
    pain: '城市词有流量但承接弱',
    detail: '用户搜索“本地 + 产品/需求”时，需要有城市页承接服务区域、门店和案例。',
  },
  {
    pain: '内容做了但证据不足',
    detail: '文章、FAQ 和案例如果没有本地实体信息，容易被识别成泛内容。',
  },
  {
    pain: '推荐后找不到转化入口',
    detail: 'AI 提到品牌之后，还要能稳定展示电话、门店和预约入口。',
  },
];

export const AI_CITY_STATION_VALUES = [
  {
    title: '城市分站承接本地搜索',
    desc: '每个城市独立沉淀服务范围、门店、案例、FAQ 和文章，覆盖“城市 + 门窗需求”的长尾词。',
  },
  {
    title: '统一管理，批量上线',
    desc: '总部维护品牌口径和页面结构，城市/门店只补本地素材，降低多站点运营成本。',
  },
  {
    title: '让品牌成为可引用答案',
    desc: '页面把企业身份、服务能力、联系方式和案例证据结构化呈现，便于搜索引擎和 AI 摘要读取。',
  },
  {
    title: '从曝光接到预约',
    desc: '城市页统一配置电话、表单和门店分配，让搜索流量直接进入咨询与上门测量流程。',
  },
];

export const AI_ENTITY_SIGNALS = [
  '品牌名称',
  '城市分站',
  '门店地址',
  '服务区域',
  '本地案例',
  '常见问答',
  '联系电话',
  '预约入口',
];

export const NEED_ENTRIES = [
  {
    id: 'balcony',
    name: '阳台封窗',
    pain: '想扩大使用面积，又担心台风天渗漏、物业审批问题。',
    href: '#services',
  },
  {
    id: 'sound',
    name: '卧室隔音窗',
    pain: '临街或高架旁，夜间噪音影响休息，想换玻璃配置。',
    href: '#services',
  },
  {
    id: 'renovate',
    name: '旧窗改造',
    pain: '老房窗户漏风、结露，想不动墙体结构整体换新。',
    href: '#services',
  },
  {
    id: 'door',
    name: '防盗门安装',
    pain: '入户门老旧或防盗等级不够，需要测量洞口后定制。',
    href: '#services',
  },
  {
    id: 'bridge',
    name: '断桥铝门窗',
    pain: '关注隔热保温，希望按楼层、朝向选型材与玻璃。',
    href: '#services',
  },
  {
    id: 'whole',
    name: '全屋门窗定制',
    pain: '新房或二次装修，需要统一测量、统一交付与验收。',
    href: '#services',
  },
];

export const PROCESS_STEPS = [
  { step: '01', title: '预约咨询', desc: '电话或在线留资，说明城市、户型与主要需求。' },
  { step: '02', title: '上门测量', desc: '安排工程师上门，记录洞口尺寸与现场条件。' },
  { step: '03', title: '方案报价', desc: '给出型材、玻璃、五金配置与工期，价格以实测为准。' },
  { step: '04', title: '安装施工', desc: '按约定时间进场，拆旧、安装、打胶、调试。' },
  { step: '05', title: '售后质保', desc: '验收后登记质保，使用中问题可联系 400 或门店。' },
];

export type CaseItem = {
  id: string;
  city: string;
  district: string;
  layout: string;
  image: string;
  need: string;
  solution: string;
  duration: string;
  result: string;
  tag: string;
};

export const PRODUCT_SPECS = [
  { name: '型材', desc: '断桥铝多腔体，壁厚按楼层与洞口尺寸选型，常用 1.4–1.8mm。' },
  { name: '玻璃', desc: '中空钢化为主；隔音需求可选三玻两腔；Low-E 用于保温场景。' },
  { name: '五金', desc: '执手、合页、锁点按开启方式配置，进口/国产品牌均可按预算选。' },
  { name: '密封', desc: '三元乙丙胶条 + 打胶工艺，重点关注转角与排水孔位置。' },
  { name: '安装', desc: '膨胀螺栓固定、水平垂直校正、开启调试，完成后现场验收。' },
  { name: '售后', desc: '按国标及门店政策质保；五金松动、密封老化可预约检修。' },
];

export const HOME_FAQS = [
  {
    question: '上门测量收费吗？',
    answer: '是否收费会根据所在城市、服务距离和现场条件确认，具体以预约时客服说明为准。',
  },
  {
    question: '为什么报价要实测后才给？',
    answer: '洞口尺寸、墙体条件、楼层、玻璃与五金配置都会影响价格，实测后方案更准确，避免后期增项纠纷。',
  },
  {
    question: '旧窗拆除会不会破坏墙面？',
    answer: '标准工序会尽量保护洞口周边，如有特殊墙体情况，测量时会提前说明处理方式。',
  },
  {
    question: '封阳台一般要多久？',
    answer: '测量确认后通常 5–10 个工作日可安排安装，视型材到货与物业施工时间而定。',
  },
  {
    question: '隔音窗真的有效吗？',
    answer: '需结合玻璃配置、密封与安装质量综合判断，临街户型一般会有明显改善，具体效果因环境而异。',
  },
];

export const ARTICLE_CATEGORIES = [
  { id: 'guide', label: '选购指南' },
  { id: 'install', label: '安装避坑' },
  { id: 'case', label: '本地案例' },
  { id: 'price', label: '价格说明' },
] as const;

export const ARTICLE_CATEGORY_MAP: Record<string, (typeof ARTICLE_CATEGORIES)[number]['id']> = {
  'guangzhou-fangdao-men-guide': 'guide',
  'shenzhen-duanqiao-lv-window': 'guide',
  'beijing-window-insulation': 'guide',
  'guangzhou-balcony-sealing': 'install',
  'beijing-security-door-install': 'install',
};

const TAG_CATEGORY_RULES: Array<{ keywords: string[]; category: (typeof ARTICLE_CATEGORIES)[number]['id'] }> = [
  { keywords: ['案例', '小区', '业主'], category: 'case' },
  { keywords: ['价格', '价位', '报价'], category: 'price' },
  { keywords: ['安装', '流程', '验收', '施工'], category: 'install' },
  { keywords: ['选购', '指南', '攻略', '怎么选'], category: 'guide' },
];

/** 优先用 slug 映射，新发布文章从 tags 推断分类 */
export function resolveArticleCategory(slug: string, tags: string[] = []): (typeof ARTICLE_CATEGORIES)[number]['id'] {
  if (ARTICLE_CATEGORY_MAP[slug]) return ARTICLE_CATEGORY_MAP[slug];
  const haystack = tags.join(' ');
  for (const rule of TAG_CATEGORY_RULES) {
    if (rule.keywords.some((word) => haystack.includes(word))) return rule.category;
  }
  return 'guide';
}

/** 将后台可能返回的 Markdown 转成适合网页展示的纯文本。 */
export function formatArticleText(value: string | null | undefined, title = ''): string {
  let text = (value || '')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}(?:>|[-*+]\s+|\d+[.)]\s+)/gm, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[`*_~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  const cleanTitle = title.trim();
  if (cleanTitle && text.startsWith(cleanTitle)) {
    text = text.slice(cleanTitle.length).replace(/^[\s：:，,。.!！?？-]+/, '').trim();
  }

  return text;
}

/** 将纯文本限制为适合卡片或元数据展示的摘要长度。 */
export function formatArticleExcerpt(value: string | null | undefined, title = '', maxLength = 140): string {
  const text = formatArticleText(value, title);

  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trimEnd()}…`;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/** 服务端 SSR/ISR 用 Docker 内网地址，浏览器仍走 NEXT_PUBLIC_API_URL */
export function getServerApiBase(): string {
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://fastapi:8000';
}

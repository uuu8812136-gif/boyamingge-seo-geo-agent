'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import AdminLoadingBar from '@/components/admin/AdminLoadingBar';
import AdminMetricCard from '@/components/admin/AdminMetricCard';
import AdminSidebar, { type AdminTabItem } from '@/components/admin/AdminSidebar';
import ContentPublishPanel from '@/components/admin/ContentPublishPanel';
import CustomerServicePanel from '@/components/admin/CustomerServicePanel';
import ExternalDistributionPanel from '@/components/admin/ExternalDistributionPanel';
import AdminStatusPill from '@/components/admin/AdminStatusPill';
import AdminTabPanel from '@/components/admin/AdminTabPanel';
import AdminTable from '@/components/admin/AdminTable';
import AdminToast from '@/components/admin/AdminToast';
import CityManagerPanel from '@/components/admin/CityManagerPanel';
import StoreManagerPanel from '@/components/admin/StoreManagerPanel';
import CitySeoPanel from '@/components/admin/CitySeoPanel';
import UserScopePanel from '@/components/admin/UserScopePanel';
import DomainStatusPanel from '@/components/admin/DomainStatusPanel';
import AccountSettingsPanel from '@/components/admin/AccountSettingsPanel';
import CityContentPanel from '@/components/admin/CityContentPanel';
import AuditLogPanel from '@/components/admin/AuditLogPanel';
import { adminFetch, adminGetMe, adminLogin, type AdminCurrentUser } from '@/lib/api';

type Tab = 'overview' | 'intents' | 'content' | 'knowledge' | 'eeat' | 'publish' | 'leads' | 'service' | 'metrics' | 'cities' | 'stores' | 'cityContent' | 'citySeo' | 'users' | 'domains' | 'audit' | 'security';

type AdminRole = 'admin' | 'operator' | 'city_manager' | 'store_manager' | 'dealer';

type IntentRow = {
  label: string;
  intent_type: string;
  keywords: string[];
  hotness_score: number;
  difficulty_score: number;
  priority: string;
};

type GeneratedContent = {
  content_id: number;
  markdown: string;
  metadata: {
    eeat_score: number;
    eeat_breakdown: Record<string, number>;
    model_used: string;
    references?: KnowledgeReference[];
  };
};

type KnowledgeReference = {
  document_id: number;
  chunk_id: number;
  title: string;
  source: string | null;
  excerpt: string;
  score: number;
};

type EaatResult = {
  eeat_score: number;
  passed: boolean;
  breakdown: Record<string, number>;
  suggestions: string[];
};

type MetricsData = {
  data_source?: string;
  summary?: {
    total_uv: number;
    total_leads: number;
    avg_cpl: number;
    latest_rank_top50: number;
    uv_trend: string;
    lead_trend: string;
  };
  metrics: Array<{
    date: string;
    rank_top50_cnt?: number;
    uv?: number;
    lead_cnt?: number;
    cpl?: number;
  }>;
};

// 线索状态：API 值 -> 中文显示
const LEAD_STATUS_LABELS: Record<string, string> = {
  new: '新线索',
  queued: '待跟进',
  contacted: '已联系',
  converted: '已成交',
};
const LEAD_STATUS_OPTIONS = Object.entries(LEAD_STATUS_LABELS).map(([value, label]) => ({ value, label }));

type LeadRow = {
  lead_id: number;
  name: string;
  phone_masked: string;
  city: string;
  interest: string;
  source: string;
  status: string;
};

type ContentLibraryRow = {
  content_id: number;
  city: string;
  type: string;
  status: string;
  eeat_score: number | null;
  title: string;
  published_url: string | null;
};

type KnowledgeDocumentRow = {
  id: number;
  title: string;
  doc_type: string;
  city: string | null;
  category: string | null;
  tags: string[];
  source: string | null;
  status: string;
  chunk_count: number;
};

type KnowledgeSearchHit = {
  chunk_id: number;
  document_id: number;
  title: string;
  doc_type: string;
  city: string | null;
  category: string | null;
  source: string | null;
  chunk_index: number;
  content: string;
  keywords: string[];
  tags: string[];
  score: number;
};

type OverviewCityDetail = {
  id: number;
  name: string;
  slug: string;
  stores: Array<{ id: number; store_name: string; address: string; phone: string; is_primary: boolean }>;
  cases: Array<{ id: number }>;
  primary_store: { id: number; store_name: string; address: string; phone: string } | null;
};

type NoticeKind = 'success' | 'error' | 'info';

const TABS: AdminTabItem[] = [
  { id: 'overview', label: '今日概览', hint: '门店与线索' },
  { id: 'intents', label: '意图挖掘', hint: '选题建议' },
  { id: 'content', label: '内容生成', hint: '稿件产出' },
  { id: 'knowledge', label: '知识库', hint: '资料与检索' },
  { id: 'eeat', label: '内容审核', hint: '质量评分' },
  { id: 'publish', label: '发布分发', hint: '官网与渠道' },
  { id: 'leads', label: '线索管理', hint: '留资跟进' },
  { id: 'service', label: '人工客服', hint: '总站会话' },
  { id: 'metrics', label: '运营指标', hint: 'UV / 线索' },
  { id: 'cities', label: '城市站管理', hint: '分站列表/发布' },
  { id: 'stores', label: '门店管理', hint: '门店与主店' },
  { id: 'cityContent', label: '城市案例/FAQ', hint: '本地内容维护' },
  { id: 'citySeo', label: '城市 SEO', hint: '标题/子域名' },
  { id: 'domains', label: '域名/二级域名', hint: '域名状态总览' },
  { id: 'users', label: '权限账号', hint: '城市/门店权限' },
  { id: 'audit', label: '操作审计', hint: '后台写操作记录' },
  { id: 'security', label: '账号设置', hint: '资料 / 密码' },
];

const ROLE_TABS: Record<AdminRole, Tab[]> = {
  admin: ['overview', 'intents', 'content', 'knowledge', 'eeat', 'publish', 'leads', 'service', 'metrics', 'cities', 'stores', 'cityContent', 'citySeo', 'domains', 'users', 'audit', 'security'],
  operator: ['overview', 'intents', 'content', 'knowledge', 'eeat', 'publish', 'leads', 'service', 'metrics', 'cities', 'stores', 'cityContent', 'citySeo', 'domains', 'audit', 'security'],
  city_manager: ['overview', 'publish', 'leads', 'metrics', 'cities', 'stores', 'cityContent', 'citySeo', 'domains', 'security'],
  store_manager: ['overview', 'publish', 'leads', 'stores', 'security'],
  dealer: [],
};

const ROLE_LABELS: Record<string, string> = {
  admin: '总部管理员',
  operator: '总部运营',
  city_manager: '城市管理员',
  store_manager: '门店管理员',
  dealer: '经销商',
};

function getTabsForRole(role?: string | null) {
  const ids = ROLE_TABS[(role || 'admin') as AdminRole] || [];
  return TABS.filter((item) => ids.includes(item.id as Tab));
}

function isHeadquarterRole(role?: string | null) {
  return role === 'admin' || role === 'operator';
}

function canViewMetricsForRole(role?: string | null) {
  return role === 'admin' || role === 'operator' || role === 'city_manager';
}

const DEFAULT_CITY_OPTIONS = ['广州', '深圳', '北京'];
const EEAT_LABELS: Record<string, string> = {
  experience: '经验',
  expertise: '专业性',
  authoritativeness: '权威性',
  trustworthiness: '可信度',
};
const WORKFLOW: Array<{ label: string; tab: Tab; desc: string }> = [
  { label: '挖词选题', tab: 'intents', desc: '输入关键词，发现高价值选题' },
  { label: '生成内容', tab: 'content', desc: '基于选题自动生成 SEO/GEO 稿件' },
  { label: '审核评分', tab: 'eeat', desc: 'EEAT 质量评分，确保内容合规' },
  { label: '发布分发', tab: 'publish', desc: '发布到官网，分发到各渠道' },
  { label: '线索与指标', tab: 'leads', desc: '查看留资线索和运营指标' },
];

const WORKFLOW_STEP_INDEX: Record<Tab, number> = {
  overview: -1,
  intents: 0,
  content: 1,
  eeat: 2,
  publish: 3,
  leads: 4,
  service: -1,
  knowledge: -1,
  metrics: 4,
  cities: -1,
  stores: -1,
  cityContent: -1,
  citySeo: -1,
  users: -1,
  domains: -1,
  security: -1,
  audit: -1,
};

export default function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<AdminCurrentUser | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [tab, setTab] = useState<Tab>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [noticeKind, setNoticeKind] = useState<NoticeKind>('info');

  const [searchTerms, setSearchTerms] = useState('');
  const [intentCity, setIntentCity] = useState('广州');
  const [intents, setIntents] = useState<IntentRow[]>([]);

  const [contentIntent, setContentIntent] = useState('');
  const [contentCity, setContentCity] = useState('广州');
  const [contentType, setContentType] = useState('seo');
  const [contentPriority, setContentPriority] = useState('P0');
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);

  const [knowledgeList, setKnowledgeList] = useState<KnowledgeDocumentRow[]>([]);
  const [knowledgeTitle, setKnowledgeTitle] = useState('');
  const [knowledgeDocType, setKnowledgeDocType] = useState('case');
  const [knowledgeCity, setKnowledgeCity] = useState('广州');
  const [knowledgeCategory, setKnowledgeCategory] = useState('');
  const [knowledgeTags, setKnowledgeTags] = useState('');
  const [knowledgeSource, setKnowledgeSource] = useState('');
  const [knowledgeContent, setKnowledgeContent] = useState('');
  const [knowledgeSearchQuery, setKnowledgeSearchQuery] = useState('');
  const [knowledgeSearchCity, setKnowledgeSearchCity] = useState('广州');
  const [knowledgeSearchResults, setKnowledgeSearchResults] = useState<KnowledgeSearchHit[]>([]);

  const [eeatContentId, setEeatContentId] = useState('');
  const [eeatMarkdown, setEeatMarkdown] = useState('');
  const [eeatResult, setEeatResult] = useState<EaatResult | null>(null);

  const [publishContentId, setPublishContentId] = useState('');
  const [publishResult, setPublishResult] = useState<{ status: string; url?: string } | null>(null);
  const [distributePlatforms, setDistributePlatforms] = useState('baijiahao,zhihu');
  const [assistPlatforms, setAssistPlatforms] = useState('xiaohongshu,douyin');
  const [distributionTasks, setDistributionTasks] = useState<Array<{ platform: string; status: string; confirm_url?: string | null; demo?: boolean }>>([]);
  const [assistPackages, setAssistPackages] = useState<Array<{ platform: string; download_url?: string | null; demo?: boolean; content?: { title?: string } }>>([]);

  const [metricsCity, setMetricsCity] = useState('广州');
  const [metricsData, setMetricsData] = useState<MetricsData | null>(null);
  const [leads, setLeads] = useState<LeadRow[]>([]);
  const [leadsCity, setLeadsCity] = useState('全部');
  const [contentLibrary, setContentLibrary] = useState<ContentLibraryRow[]>([]);
  const [libraryCity, setLibraryCity] = useState('全部');
  const [hotlineName, setHotlineName] = useState('');
  const [hotlinePhone, setHotlinePhone] = useState('');
  const [hotlineCity, setHotlineCity] = useState('广州');
  const [hotlineInterest, setHotlineInterest] = useState('');
  const [hotlineResult, setHotlineResult] = useState<{ call_id: string; assigned_dealer: string } | null>(null);
  const [cityOptions, setCityOptions] = useState<string[]>(DEFAULT_CITY_OPTIONS);
  const [overviewCities, setOverviewCities] = useState<OverviewCityDetail[]>([]);

  const role = currentUser?.role;
  const isHeadquarter = isHeadquarterRole(role);
  const canViewMetrics = canViewMetricsForRole(role);
  const allowedTabs = useMemo(() => getTabsForRole(role), [role]);
  const allowedTabIds = useMemo(() => new Set(allowedTabs.map((item) => item.id as Tab)), [allowedTabs]);
  const visibleWorkflow = useMemo(() => WORKFLOW.filter((step) => allowedTabIds.has(step.tab)), [allowedTabIds]);
  const activeTab = allowedTabs.find((item) => item.id === tab) || allowedTabs[0] || TABS.find((item) => item.id === tab);


  const showNotice = useCallback((message: string, kind: NoticeKind = 'info') => {
    setNotice(message);
    setNoticeKind(kind);
  }, []);

  const loadCurrentUser = useCallback(async (tk: string) => {
    const me = await adminGetMe(tk);
    setCurrentUser(me);
    return me;
  }, []);

  const loadCityOptions = useCallback(async (tk: string) => {
    try {
      const data = await adminFetch<{ items: { name: string }[]; total: number }>(`/api/v1/admin/cities`, tk);
      if (data.items && data.items.length > 0) {
        setCityOptions(data.items.map((c) => c.name));
      }
    } catch {
      // 降级使用默认城市
    }
  }, []);

  useEffect(() => {
    const saved = sessionStorage.getItem('admin_token');
    if (saved) {
      setToken(saved);
      loadCurrentUser(saved).catch(() => {
        sessionStorage.removeItem('admin_token');
        setToken(null);
        setCurrentUser(null);
      });
      loadCityOptions(saved);
    }
  }, [loadCityOptions, loadCurrentUser]);

  useEffect(() => {
    const updateToken = (event: Event) => setToken((event as CustomEvent<string>).detail);
    window.addEventListener('admin-token-refreshed', updateToken);
    return () => window.removeEventListener('admin-token-refreshed', updateToken);
  }, []);

  const loadOverviewCities = useCallback(async (tk: string) => {
    try {
      const list = await adminFetch<{
        items: Array<{ id: number; is_active: boolean; has_store: boolean; content_status: string }>;
      }>('/api/v1/admin/cities', tk);
      const overviewItems = (list.items || []).filter(
        (city) => city.is_active && (city.has_store || city.content_status === 'published'),
      );
      const details = await Promise.all(
        overviewItems.map((city) => adminFetch<OverviewCityDetail>(`/api/v1/admin/cities/${city.id}`, tk)),
      );
      setOverviewCities(details);
    } catch {
      setOverviewCities([]);
    }
  }, []);

  useEffect(() => {
    if (!token || allowedTabs.length === 0) return;
    if (!allowedTabIds.has(tab)) {
      setTab(allowedTabs[0].id as Tab);
    }
  }, [allowedTabIds, allowedTabs, tab, token]);

  const overview = useMemo(() => {
    const lowEeat = generatedContent && generatedContent.metadata.eeat_score < 70 ? 1 : 0;
    const cityLeadCounts = cityOptions.reduce<Record<string, number>>((acc, city) => {
      acc[city] = leads.filter((lead) => lead.city === city).length;
      return acc;
    }, {});
    return {
      intents: intents.length,
      generated: generatedContent ? 1 : 0,
      pendingPublish: publishContentId ? 1 : 0,
      leads: leads.length,
      lowEeat,
      top50: metricsData?.summary?.latest_rank_top50 ?? 0,
      cityLeadCounts,
    };
  }, [generatedContent, intents.length, leads, metricsData?.summary?.latest_rank_top50, publishContentId, cityOptions]);

  const scopedCityCards = useMemo(() => {
    return overviewCities.map((detail) => {
      const store = detail.primary_store || detail.stores[0] || null;
      return {
      slug: detail.slug,
      city: {
        name: detail.name,
        hotline: store?.phone || '',
        address: store?.address || '暂未配置门店地址',
        subtitle: store ? `${store.store_name} · 共 ${detail.stores.length} 家门店` : '请在门店管理中录入真实信息',
        cases: detail.cases || [],
      },
    };
    });
  }, [overviewCities]);

  const filteredLeads = leads;

  const selectContent = (row: ContentLibraryRow) => {
    setEeatContentId(String(row.content_id));
    setPublishContentId(String(row.content_id));
    showNotice(`已选用内容 ${row.content_id}`, 'info');
  };

  const selectContentForReview = (row: ContentLibraryRow) => {
    setEeatContentId(String(row.content_id));
    setPublishContentId(String(row.content_id));
    setTab('eeat');
    showNotice(`已选用内容 ${row.content_id}，正在加载正文…`, 'success');
    run(async () => {
      const data = await adminFetch<{ markdown: string; content_id: number }>(`/api/v1/content/${row.content_id}`, token!);
      setEeatMarkdown(data.markdown || '');
    });
  };

  const run = useCallback(async (fn: () => Promise<void>) => {
    setLoading(true);
    setNotice('');
    try {
      await fn();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '操作失败';
      showNotice(msg, 'error');
      if (msg.includes('登录已过期')) {
        setToken(null);
      }
    } finally {
      setLoading(false);
    }
  }, [showNotice]);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoginError('');
    try {
      const nextToken = await adminLogin(username, password);
      setToken(nextToken);
      sessionStorage.setItem('admin_token', nextToken);
      await loadCurrentUser(nextToken);
      loadCityOptions(nextToken);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : '登录失败');
    }
  };

  const handleLogout = () => {
    setToken(null);
    setCurrentUser(null);
    sessionStorage.removeItem('admin_token');
    sessionStorage.removeItem('admin_refresh_token');
  };

  const loadIntents = () => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ intents: IntentRow[] }>('/api/v1/intents', token, {
      method: 'POST',
      body: JSON.stringify({
        search_terms: searchTerms.split(',').map((item) => item.trim()).filter(Boolean),
        cities: [intentCity],
        top_k: 10,
      }),
    });
    setIntents(data.intents);
    showNotice(`已生成 ${data.intents.length} 条选题建议`, 'success');
  });

  const generateContent = () => run(async () => {
    if (!token) return;
    if (!contentIntent.trim()) { showNotice('请输入主题', 'error'); return; }
    const data = await adminFetch<GeneratedContent>('/api/v1/content/generate', token, {
      method: 'POST',
      body: JSON.stringify({
        intent: contentIntent,
        city: contentCity,
        type: contentType,
        priority: contentPriority,
        use_cache: false,
      }),
    });
    setGeneratedContent(data);
    setEeatContentId(String(data.content_id));
    setEeatMarkdown(data.markdown);
    setPublishContentId(String(data.content_id));
    await loadContentLibrary();
    showNotice(`内容 ${data.content_id} 已生成，正在跳转到审核评分…`, 'success');
    // Auto-advance to EEAT review
    setTimeout(() => setTab('eeat'), 1200);
  });

  const scoreContent = () => run(async () => {
    if (!token) return;
    if (!eeatContentId.trim()) { showNotice('请输入内容 ID', 'error'); return; }
    if (!eeatMarkdown.trim()) { showNotice('请输入正文内容', 'error'); return; }
    const data = await adminFetch<EaatResult & { content_id: number }>('/api/v1/content/eeat-score', token, {
      method: 'POST',
      body: JSON.stringify({ content_id: Number(eeatContentId), markdown: eeatMarkdown }),
    });
    setEeatResult(data);
    if (data.passed) {
      showNotice('审核通过！正在跳转到发布分发…', 'success');
      setTimeout(() => setTab('publish'), 1200);
    } else {
      showNotice('内容需要修改后再发布，请查看下方建议', 'error');
    }
  });

  const publishContent = () => run(async () => {
    if (!token) return;
    if (!publishContentId.trim()) { showNotice('请输入内容 ID', 'error'); return; }
    const data = await adminFetch<{ status: string; url?: string }>('/api/v1/publish', token, {
      method: 'POST',
      body: JSON.stringify({ content_id: Number(publishContentId), target: 'website' }),
    });
    setPublishResult(data);
    showNotice('官网发布成功，可继续下方分发操作', 'success');
  });

  const createDistribution = () => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ tasks: Array<{ platform: string; status: string; confirm_url?: string }> }>('/api/v1/distribute', token, {
      method: 'POST',
      body: JSON.stringify({
        content_id: Number(publishContentId),
        platforms: distributePlatforms.split(',').map((item) => item.trim()).filter(Boolean),
        dealer_id: 'D2026001',
      }),
    });
    setDistributionTasks(data.tasks);
    showNotice(`已生成 ${data.tasks.length} 个确认任务`, 'success');
  });

  const createAssistPackages = () => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ packages: Array<{ platform: string; download_url?: string; content?: { title?: string } }> }>('/api/v1/distribute/assist', token, {
      method: 'POST',
      body: JSON.stringify({
        content_id: Number(publishContentId),
        platforms: assistPlatforms.split(',').map((item) => item.trim()).filter(Boolean),
      }),
    });
    setAssistPackages(data.packages);
    showNotice(`已生成 ${data.packages.length} 个素材包`, 'success');
  });

  const loadKnowledgeList = useCallback(() => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ items: KnowledgeDocumentRow[] }>('/api/v1/knowledge', token);
    setKnowledgeList(data.items);
  }), [run, token]);

  const createKnowledgeDocument = () => run(async () => {
    if (!token) return;
    const data = await adminFetch<KnowledgeDocumentRow>('/api/v1/knowledge', token, {
      method: 'POST',
      body: JSON.stringify({
        title: knowledgeTitle,
        doc_type: knowledgeDocType,
        city: knowledgeCity === '通用' ? null : knowledgeCity,
        category: knowledgeCategory || null,
        tags: knowledgeTags.split(',').map((item) => item.trim()).filter(Boolean),
        source: knowledgeSource || null,
        content: knowledgeContent,
        status: 'active',
      }),
    });
    await loadKnowledgeList();
    showNotice(`资料 ${data.id} 已入库并切片`, 'success');
  });

  const rebuildKnowledgeDocument = (documentId: number) => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ chunk_count: number }>(`/api/v1/knowledge/${documentId}/rebuild`, token, {
      method: 'POST',
    });
    await loadKnowledgeList();
    showNotice(`已重建 ${data.chunk_count} 个片段`, 'success');
  });

  const deleteKnowledgeDocument = (documentId: number, title?: string) => run(async () => {
    if (!token) return;
    const confirmed = window.confirm(`确认删除资料「${title || documentId}」？此操作不可撤销。`);
    if (!confirmed) return;
    await adminFetch<void>(`/api/v1/knowledge/${documentId}`, token, { method: 'DELETE' });
    await loadKnowledgeList();
    showNotice('资料已删除', 'success');
  });

  const updateLeadStatus = (leadId: number, newStatus: string) => run(async () => {
    if (!token) return;
    await adminFetch<{ lead_id: number; status: string; message: string }>(`/api/v1/leads/${leadId}/status`, token, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    await loadLeads();
    showNotice(`线索状态已更新为：${LEAD_STATUS_LABELS[newStatus] || newStatus}`, 'success');
  });

  const testKnowledgeSearch = () => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ items: KnowledgeSearchHit[] }>('/api/v1/knowledge/search', token, {
      method: 'POST',
      body: JSON.stringify({
        query: knowledgeSearchQuery,
        city: knowledgeSearchCity === '全部' ? null : knowledgeSearchCity,
        limit: 5,
      }),
    });
    setKnowledgeSearchResults(data.items);
    showNotice(`检索到 ${data.items.length} 条片段`, data.items.length ? 'success' : 'info');
  });

  const loadContentLibrary = useCallback(() => run(async () => {
    if (!token) return;
    const params = new URLSearchParams();
    if (libraryCity !== '全部') params.set('city', libraryCity);
    const query = params.toString() ? `?${params}` : '';
    const data = await adminFetch<{ items: ContentLibraryRow[] }>(`/api/v1/content${query}`, token);
    setContentLibrary(data.items);
  }), [libraryCity, run, token]);

  const loadContentDetail = (contentId: number) => run(async () => {
    if (!token) return;
    const data = await adminFetch<{ markdown: string; content_id: number }>(`/api/v1/content/${contentId}`, token);
    setEeatMarkdown(data.markdown);
    setEeatContentId(String(data.content_id));
    setPublishContentId(String(data.content_id));
    showNotice(`已加载内容 ${contentId} 正文`, 'success');
  });

  const loadLeads = useCallback(() => run(async () => {
    if (!token) return;
    const params = new URLSearchParams();
    if (leadsCity !== '全部') params.set('city', leadsCity);
    const query = params.toString() ? `?${params}` : '';
    const data = await adminFetch<{ items: LeadRow[] }>(`/api/v1/leads${query}`, token);
    setLeads(data.items);
  }), [leadsCity, run, token]);

  const pushHotline = () => run(async () => {
    if (!token) return;
    if (!/^1\d{10}$/.test(hotlinePhone)) {
      showNotice('请输入有效的 11 位手机号', 'error');
      return;
    }
    const data = await adminFetch<{ call_id: string; assigned_dealer: string; status: string }>(
      '/api/v1/hotline/push',
      token,
      {
        method: 'POST',
        body: JSON.stringify({
          lead: {
            name: hotlineName,
            phone: hotlinePhone,
            city: hotlineCity,
            interest: hotlineInterest,
            source: 'admin',
          },
        }),
      },
    );
    setHotlineResult({ call_id: data.call_id, assigned_dealer: data.assigned_dealer });
    showNotice(`热线已排队：${data.call_id}`, 'success');
    loadLeads();
  });

  const openCityMetrics = (city: string) => {
    setMetricsCity(city);
    setTab('metrics');
  };

  const openCityLeads = (city: string) => {
    setLeadsCity(city);
    setTab('leads');
  };

  const loadMetrics = useCallback(() => run(async () => {
    if (!token) return;
    const data = await adminFetch<MetricsData>(`/api/v1/metrics?city=${metricsCity}`, token);
    setMetricsData(data);
  }), [metricsCity, run, token]);

  useEffect(() => {
    if (!token || !currentUser) return;
    if (allowedTabIds.has('leads')) loadLeads();
    if ((tab === 'metrics' || tab === 'overview') && canViewMetrics) loadMetrics();
    if ((tab === 'content' || tab === 'eeat') && isHeadquarter) loadContentLibrary();
    if (tab === 'knowledge' && isHeadquarter) loadKnowledgeList();
    if (tab === 'overview') loadOverviewCities(token);
  }, [allowedTabIds, canViewMetrics, currentUser, isHeadquarter, loadContentLibrary, loadKnowledgeList, loadLeads, loadMetrics, loadOverviewCities, tab, token]);

  useEffect(() => {
    if (!token || !currentUser || !isHeadquarter || (tab !== 'content' && tab !== 'eeat')) return;
    loadContentLibrary();
  }, [currentUser, isHeadquarter, libraryCity, loadContentLibrary, tab, token]);

  useEffect(() => {
    if (!token || !currentUser || tab !== 'leads' || !allowedTabIds.has('leads')) return;
    loadLeads();
  }, [allowedTabIds, currentUser, leadsCity, loadLeads, tab, token]);

  if (!token) {
    return (
      <main className="admin-app admin-login-page">
        <form className="admin-login-card admin-form" onSubmit={handleLogin}>
          <span className="admin-login-badge">运营后台</span>
          <h1>博雅敏格门窗</h1>
          <p>登录后管理选题、内容、发布、线索与基础指标。</p>
          <label>用户名<input value={username} onChange={(event) => setUsername(event.target.value)} /></label>
          <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <p className="admin-login-hint">请输入已分配的运营账号。</p>
          {loginError && <p className="form-message error">{loginError}</p>}
          <button className="btn btn-primary btn-block" type="submit">登录</button>
        </form>
      </main>
    );
  }

  if (!currentUser) {
    return (
      <main className="admin-app admin-login-page">
        <div className="admin-login-card admin-form">
          <span className="admin-login-badge">加载权限</span>
          <h1>正在进入后台</h1>
          <p>正在校验账号角色和可见模块，请稍候。</p>
        </div>
      </main>
    );
  }

  if (currentUser && allowedTabs.length === 0) {
    return (
      <main className="admin-app admin-login-page">
        <div className="admin-login-card admin-form">
          <span className="admin-login-badge">无后台权限</span>
          <h1>{currentUser.username}</h1>
          <p>当前账号角色为 {currentUser.role}，不能进入运营后台。请使用总部、城市或门店管理员账号登录。</p>
          <button className="btn btn-primary btn-block" type="button" onClick={handleLogout}>退出登录</button>
        </div>
      </main>
    );
  }

  return (
    <main className="admin-app">
      <AdminSidebar
        tabs={allowedTabs}
        active={tab}
        onChange={(id) => setTab(id as Tab)}
        onLogout={handleLogout}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        account={currentUser}
      />

      <section className="admin-main">
        <AdminLoadingBar active={loading} />
        <AdminToast message={notice} kind={noticeKind} onDismiss={() => setNotice('')} />

        <header className="admin-topbar">
          <div className="admin-topbar-left">
            <button type="button" className="admin-menu-toggle" aria-label="打开菜单" onClick={() => setSidebarOpen(true)}>
              <span /><span /><span />
            </button>
            <div>
              <span className="admin-kicker">工作台</span>
              <h1>{activeTab?.label}</h1>
              <p className="admin-topbar-desc">{activeTab?.hint}</p>
            </div>
          </div>
        </header>

        {/* Workflow Progress Bar */}
        <nav className="admin-workflow-bar">
          {visibleWorkflow.map((step, index) => {
            const currentStep = visibleWorkflow.findIndex((item) => item.tab === tab);
            const isCompleted = currentStep > index;
            const isCurrent = currentStep === index;
            return (
              <button
                key={step.tab}
                type="button"
                className={`admin-workflow-bar-step${isCurrent ? ' is-current' : ''}${isCompleted ? ' is-completed' : ''}`}
                onClick={() => setTab(step.tab)}
                title={step.desc}
              >
                <span className="admin-workflow-bar-num">{isCompleted ? '✓' : index + 1}</span>
                <span className="admin-workflow-bar-label">{step.label}</span>
              </button>
            );
          })}
        </nav>

        <AdminTabPanel key={tab} tabKey={tab}>
          {tab === 'overview' && (
            <div className="admin-stack">
              <div className="admin-kpi-grid">
                {isHeadquarter && <AdminMetricCard label="选题建议" value={overview.intents} hint="来自意图挖掘" index={0} />}
                {isHeadquarter && <AdminMetricCard label="已生成内容" value={overview.generated} hint="本次会话" index={1} />}
                <AdminMetricCard label="网站线索" value={overview.leads} hint={isHeadquarter ? '官网留资' : '当前账号范围'} index={2} tone="ok" />
                {isHeadquarter && <AdminMetricCard label="待发布内容" value={overview.pendingPublish} hint="等待确认" index={3} tone="info" />}
                {isHeadquarter && <AdminMetricCard label="低分内容" value={overview.lowEeat} hint="需补案例/参数" index={4} tone="warn" />}
                {canViewMetrics && <AdminMetricCard label="TOP50 词数" value={overview.top50} hint="基础指标" index={5} />}
              </div>

              <section className="admin-card">
                <div className="admin-card-body">
                  <div className="admin-card-head">
                    <h2>城市门店</h2>
                    <span className="admin-card-note">当前账号可管理范围</span>
                  </div>
                  <div className="admin-city-grid">
                    {scopedCityCards.map(({ slug, city }, index) => {
                      const leadCount = overview.cityLeadCounts[city.name] ?? 0;
                      return (
                        <article
                          key={slug || city.name}
                          className="admin-city-card"
                          style={{ '--stagger': `${index * 50}ms` } as React.CSSProperties}
                        >
                          <div className="admin-city-card-head">
                            <strong>{city.name}</strong>
                            {city.hotline && <span>{city.hotline}</span>}
                          </div>
                          <p>{city.address}</p>
                          <p className="admin-city-card-meta">{city.subtitle}</p>
                          <div className="admin-city-card-stats">
                            <span><b>{leadCount}</b> 条线索</span>
                            <span>{city.cases.length} 个案例</span>
                          </div>
                          <div className="admin-city-card-actions">
                            {slug && <Link href={`/${slug}`} className="btn btn-outline btn-sm" target="_blank" prefetch={false}>预览分站</Link>}
                            {allowedTabIds.has('leads') && <button type="button" className="btn btn-outline btn-sm" onClick={() => openCityLeads(city.name)}>看线索</button>}
                            {canViewMetrics && <button type="button" className="btn btn-primary btn-sm" onClick={() => openCityMetrics(city.name)}>看指标</button>}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </section>

              <section className="admin-card">
                <div className="admin-card-body">
                  <h2>建议流程</h2>
                  <div className="admin-workflow">
                    {visibleWorkflow.map((step, index) => (
                      <button
                        key={step.tab}
                        type="button"
                        className={`admin-workflow-step${tab === step.tab ? ' is-active' : ''}`}
                        onClick={() => setTab(step.tab)}
                      >
                        {index + 1}. {step.label}
                      </button>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          )}

          {tab === 'intents' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>第 1 步：挖词选题</strong>
                <p>输入行业关键词（如"防盗门"、"阳台封窗"），系统会分析搜索意图和竞争难度，推荐高价值选题。选好主题后进入下一步生成内容。</p>
              </div>
              <div className="admin-grid-two">
              <section className="admin-card">
                <div className="admin-card-body admin-form">
                  <h2>生成选题建议</h2>
                  <label>搜索词<input value={searchTerms} onChange={(event) => setSearchTerms(event.target.value)} /></label>
                  <label>城市
                    <select value={intentCity} onChange={(event) => setIntentCity(event.target.value)}>
                      {cityOptions.map((city) => <option key={city}>{city}</option>)}
                    </select>
                  </label>
                  <button className="btn btn-primary" type="button" disabled={loading} onClick={loadIntents}>
                    {loading ? '挖掘中…' : '开始挖掘'}
                  </button>
                </div>
              </section>
              <section className="admin-card">
                <div className="admin-card-body">
                  <h2>结果列表</h2>
                  <AdminTable
                    rows={intents}
                    rowKey={(row) => row.label}
                    emptyText="点击左侧开始挖掘，结果会出现在这里。"
                    columns={[
                      {
                        key: 'label',
                        title: '主题',
                        render: (row) => (
                          <>
                            <strong>{row.label}</strong>
                            <small>{row.keywords.slice(0, 3).join(' / ')}</small>
                          </>
                        ),
                      },
                      { key: 'intent_type', title: '意图' },
                      { key: 'hotness_score', title: '热度' },
                      { key: 'difficulty_score', title: '难度' },
                      {
                        key: 'priority',
                        title: '优先级',
                        render: (row) => (
                          <AdminStatusPill tone={row.priority === 'P0' ? 'good' : 'neutral'}>{row.priority}</AdminStatusPill>
                        ),
                      },
                      {
                        key: 'action',
                        title: '操作',
                        render: (row) => (
                          <button
                            className="btn btn-primary btn-sm"
                            type="button"
                            onClick={() => {
                              setContentIntent(row.label);
                              setContentCity(intentCity);
                              setTab('content');
                              showNotice(`已选用"${row.label}"，即将生成内容`, 'success');
                            }}
                          >
                            选用
                          </button>
                        ),
                      },
                    ]}
                  />
                </div>
              </section>
              </div>
            </div>
          )}

          {tab === 'content' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>第 2 步：生成内容</strong>
                <p>选择选题主题和城市，点击"生成内容"即可自动产出 SEO 长文/GEO 摘要/结构化数据。生成后会自动跳转到审核评分。</p>
              </div>
              <div className="admin-grid-two admin-grid-wide">
                <section className="admin-card">
                  <div className="admin-card-body admin-form">
                    <h2>生成稿件</h2>
                    <label>主题<input value={contentIntent} onChange={(event) => setContentIntent(event.target.value)} /></label>
                    <label>城市
                      <select value={contentCity} onChange={(event) => setContentCity(event.target.value)}>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                    </label>
                    <label>内容类型
                      <select value={contentType} onChange={(event) => setContentType(event.target.value)}>
                        <option value="seo">长文</option>
                        <option value="geo">短摘要</option>
                        <option value="schema">结构化信息</option>
                      </select>
                    </label>
                    <label>优先级
                      <select value={contentPriority} onChange={(event) => setContentPriority(event.target.value)}>
                        <option>P0</option><option>P1</option><option>P2</option>
                      </select>
                    </label>
                    <button className="btn btn-primary" type="button" disabled={loading} onClick={generateContent}>
                      {loading ? '生成中…' : '生成内容'}
                    </button>
                  </div>
                </section>
                <section className="admin-card">
                  <div className="admin-card-body">
                    <h2>内容预览</h2>
                    {generatedContent ? (
                      <div className="admin-preview">
                        <div className="admin-preview-meta">
                          <AdminStatusPill tone={generatedContent.metadata.eeat_score >= 70 ? 'good' : 'warn'}>
                            评分 {generatedContent.metadata.eeat_score}
                          </AdminStatusPill>
                          <span>ID {generatedContent.content_id}</span>
                          <span>{generatedContent.metadata.model_used}</span>
                          <span>{generatedContent.metadata.references?.length ?? 0} 条引用</span>
                        </div>
                        {generatedContent.metadata.references && generatedContent.metadata.references.length > 0 && (
                          <ul className="admin-reference-list">
                            {generatedContent.metadata.references.map((item) => (
                              <li key={`${item.document_id}-${item.chunk_id}`}>
                                <strong>{item.title}</strong>
                                <span>{item.source || `资料 ${item.document_id}`} · 片段 {item.chunk_id}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                        <pre>{generatedContent.markdown}</pre>
                      </div>
                    ) : (
                      <div className="admin-empty">
                        <span className="admin-empty-icon" aria-hidden>✎</span>
                        <p>生成后会在这里预览稿件内容。</p>
                      </div>
                    )}
                  </div>
                </section>
              </div>

              <section className="admin-card">
                <div className="admin-card-body">
                  <div className="admin-toolbar">
                    <h2>内容库</h2>
                    <div className="admin-toolbar-controls">
                      <select value={libraryCity} onChange={(event) => setLibraryCity(event.target.value)}>
                        <option>全部</option>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                      <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={loadContentLibrary}>刷新</button>
                    </div>
                  </div>
                  <AdminTable
                    rows={contentLibrary}
                    rowKey={(row) => row.content_id}
                    emptyText="暂无内容，生成后会出现在这里。"
                    columns={[
                      { key: 'content_id', title: 'ID' },
                      { key: 'title', title: '标题' },
                      { key: 'city', title: '城市' },
                      { key: 'type', title: '类型' },
                      {
                        key: 'status',
                        title: '状态',
                        render: (row) => <AdminStatusPill tone={row.status === 'published' ? 'good' : 'info'}>{row.status}</AdminStatusPill>,
                      },
                      {
                        key: 'eeat_score',
                        title: '评分',
                        render: (row) => (row.eeat_score != null ? row.eeat_score : '-'),
                      },
                      {
                        key: 'actions',
                        title: '操作',
                        render: (row) => (
                          <div className="admin-row-actions">
                            <button type="button" className="btn btn-primary btn-sm" onClick={() => selectContentForReview(row)}>去审核</button>
                            <button type="button" className="btn btn-outline btn-sm" onClick={() => loadContentDetail(row.content_id)}>加载正文</button>
                            {row.published_url && (
                              <a href={row.published_url} target="_blank" rel="noreferrer" className="admin-task-link">查看</a>
                            )}
                          </div>
                        ),
                      },
                    ]}
                  />
                </div>
              </section>
            </div>
          )}

          {tab === 'knowledge' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>知识库管理</strong>
                <p>知识库是内容生成的素材来源。新增资料后会自动切片和索引，生成内容时会自动引用相关知识。可使用"测试检索"验证搜索效果。</p>
              </div>
              <div className="admin-grid-two admin-grid-wide">
                <section className="admin-card">
                  <div className="admin-card-body admin-form">
                    <h2>新增资料</h2>
                    <label>标题<input value={knowledgeTitle} onChange={(event) => setKnowledgeTitle(event.target.value)} /></label>
                    <label>类型
                      <select value={knowledgeDocType} onChange={(event) => setKnowledgeDocType(event.target.value)}>
                        <option value="case">案例</option>
                        <option value="faq">问答</option>
                        <option value="product">产品</option>
                        <option value="policy">政策</option>
                        <option value="general">通用</option>
                      </select>
                    </label>
                    <label>城市
                      <select value={knowledgeCity} onChange={(event) => setKnowledgeCity(event.target.value)}>
                        <option>通用</option>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                    </label>
                    <label>分类<input value={knowledgeCategory} onChange={(event) => setKnowledgeCategory(event.target.value)} /></label>
                    <label>标签<input value={knowledgeTags} onChange={(event) => setKnowledgeTags(event.target.value)} /></label>
                    <label>来源<input value={knowledgeSource} onChange={(event) => setKnowledgeSource(event.target.value)} /></label>
                    <label>正文<textarea value={knowledgeContent} onChange={(event) => setKnowledgeContent(event.target.value)} /></label>
                    <button className="btn btn-primary" type="button" disabled={loading} onClick={createKnowledgeDocument}>
                      {loading ? '入库中…' : '新增资料'}
                    </button>
                  </div>
                </section>

                <section className="admin-card">
                  <div className="admin-card-body admin-form">
                    <h2>测试检索</h2>
                    <label>关键词<input value={knowledgeSearchQuery} onChange={(event) => setKnowledgeSearchQuery(event.target.value)} /></label>
                    <label>城市
                      <select value={knowledgeSearchCity} onChange={(event) => setKnowledgeSearchCity(event.target.value)}>
                        <option>全部</option>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                    </label>
                    <button className="btn btn-primary" type="button" disabled={loading} onClick={testKnowledgeSearch}>
                      {loading ? '检索中…' : '测试检索'}
                    </button>

                    {knowledgeSearchResults.length > 0 ? (
                      <div className="admin-search-results">
                        {knowledgeSearchResults.map((item) => (
                          <article key={item.chunk_id} className="admin-search-hit">
                            <div>
                              <strong>{item.title}</strong>
                              <span>{item.city || '通用'} · {item.doc_type} · 分数 {item.score}</span>
                            </div>
                            <p>{item.content}</p>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="admin-empty">
                        <span className="admin-empty-icon" aria-hidden>⌕</span>
                        <p>输入关键词后可验证 Postgres 关键词检索结果。</p>
                      </div>
                    )}
                  </div>
                </section>
              </div>

              <section className="admin-card">
                <div className="admin-card-body">
                  <div className="admin-toolbar">
                    <h2>资料列表</h2>
                    <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={loadKnowledgeList}>刷新</button>
                  </div>
                  <AdminTable
                    rows={knowledgeList}
                    rowKey={(row) => row.id}
                    emptyText="暂无资料，新增文本资料后会自动切片。"
                    columns={[
                      { key: 'id', title: 'ID' },
                      {
                        key: 'title',
                        title: '标题',
                        render: (row) => (
                          <>
                            <strong>{row.title}</strong>
                            <small>{row.source || '未填写来源'}</small>
                          </>
                        ),
                      },
                      { key: 'doc_type', title: '类型' },
                      { key: 'city', title: '城市', render: (row) => row.city || '通用' },
                      { key: 'category', title: '分类', render: (row) => row.category || '-' },
                      {
                        key: 'tags',
                        title: '标签',
                        render: (row) => row.tags.slice(0, 3).join(' / ') || '-',
                      },
                      { key: 'chunk_count', title: '片段' },
                      {
                        key: 'status',
                        title: '状态',
                        render: (row) => <AdminStatusPill tone={row.status === 'active' ? 'good' : 'neutral'}>{row.status}</AdminStatusPill>,
                      },
                      {
                        key: 'actions',
                        title: '操作',
                        render: (row) => (
                          <div className="admin-row-actions">
                            <button type="button" className="btn btn-outline btn-sm" onClick={() => rebuildKnowledgeDocument(row.id)}>
                              重建索引
                            </button>
                            <button type="button" className="btn btn-outline btn-sm" onClick={() => deleteKnowledgeDocument(row.id, row.title)}>
                              删除
                            </button>
                          </div>
                        ),
                      },
                    ]}
                  />
                </div>
              </section>
            </div>
          )}

          {tab === 'eeat' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>第 3 步：审核评分</strong>
                <p>系统会从经验、专业性、权威性、可信度四个维度评分。评分 ≥ 70 分才能发布。审核通过后会自动跳转到发布页面。</p>
              </div>
              {eeatContentId && (
                <div className="admin-current-pick">
                  当前选用内容 ID：<strong>{eeatContentId}</strong>
                  {contentLibrary.find((r) => String(r.content_id) === eeatContentId) && (
                    <span> · {contentLibrary.find((r) => String(r.content_id) === eeatContentId)?.title}</span>
                  )}
                </div>
              )}
              <div className="admin-grid-two admin-grid-wide">
              <section className="admin-card">
                <div className="admin-card-body admin-form">
                  <h2>审核内容</h2>
                  <label>内容 ID<input value={eeatContentId} onChange={(event) => setEeatContentId(event.target.value)} /></label>
                  <label>正文<textarea value={eeatMarkdown} onChange={(event) => setEeatMarkdown(event.target.value)} /></label>
                  <button className="btn btn-primary" type="button" disabled={loading} onClick={scoreContent}>
                    {loading ? '评分中…' : '重新评分'}
                  </button>
                </div>
              </section>
              <section className="admin-card">
                <div className="admin-card-body">
                  <h2>审核结果</h2>
                  {eeatResult ? (
                    <>
                      <div className="admin-score-head">
                        <strong>{eeatResult.eeat_score}</strong>
                        <AdminStatusPill tone={eeatResult.passed ? 'good' : 'warn'}>
                          {eeatResult.passed ? '可发布' : '需修改'}
                        </AdminStatusPill>
                      </div>
                      <div className="admin-score-bars">
                        {Object.entries(eeatResult.breakdown).map(([key, value], index) => (
                          <div key={key} className="admin-score-row">
                            <span>{EEAT_LABELS[key] ?? key}</span>
                            <div className="admin-score-track">
                              <i
                                className="admin-score-fill"
                                style={{
                                  width: `${value}%`,
                                  '--bar-delay': `${index * 60}ms`,
                                } as React.CSSProperties}
                              />
                            </div>
                            <b>{value}</b>
                          </div>
                        ))}
                      </div>
                      {eeatResult.suggestions.length > 0 && (
                        <ul className="admin-suggestion-list">
                          {eeatResult.suggestions.map((item) => <li key={item}>{item}</li>)}
                        </ul>
                      )}
                    </>
                  ) : (
                    <div className="admin-empty">
                      <span className="admin-empty-icon" aria-hidden>◎</span>
                      <p>内容生成后可在这里查看评分和修改建议。</p>
                    </div>
                  )}
                </div>
              </section>
              </div>
            </div>
          )}

          {tab === 'publish' && (
            <div className="admin-publish-tabs">
              <details className="admin-subsection" open>
                <summary>站内内容发布</summary>
                <ContentPublishPanel token={token} showNotice={showNotice} cityOptions={cityOptions} role={role} defaultStoreId={currentUser?.store_id} canUploadVideo={isHeadquarter} />
              </details>
              {isHeadquarter && (
                <details className="admin-subsection">
                  <summary>外部平台分发</summary>
                  <ExternalDistributionPanel token={token} showNotice={showNotice} />
                </details>
              )}
            </div>
          )}

          {tab === 'leads' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>第 5 步：线索与指标</strong>
                <p>查看官网留资线索和运营指标。热线推送可将线索直接分配给经销商并触发外呼。运营指标展示 UV、线索量、成本等关键数据。</p>
              </div>
              <section className="admin-card">
                <div className="admin-card-body">
                  <div className="admin-toolbar">
                    <h2>网站线索</h2>
                    <div className="admin-toolbar-controls">
                      <select value={leadsCity} onChange={(event) => setLeadsCity(event.target.value)}>
                        <option>全部</option>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                      <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={loadLeads}>刷新</button>
                    </div>
                  </div>
                  <AdminTable
                    rows={filteredLeads}
                    rowKey={(row) => row.lead_id}
                    emptyText={`暂无${leadsCity === '全部' ? '' : leadsCity}线索，官网表单提交后会出现在这里。`}
                    columns={[
                      { key: 'lead_id', title: 'ID' },
                      { key: 'name', title: '客户' },
                      { key: 'phone_masked', title: '手机' },
                      { key: 'city', title: '城市' },
                      { key: 'interest', title: '需求' },
                      { key: 'source', title: '来源' },
                      {
                        key: 'status',
                        title: '状态',
                        render: (row) => (
                          <AdminStatusPill tone={row.status === 'converted' ? 'good' : row.status === 'contacted' ? 'info' : 'neutral'}>
                            {LEAD_STATUS_LABELS[row.status] || row.status}
                          </AdminStatusPill>
                        ),
                      },
                      {
                        key: 'actions',
                        title: '操作',
                        render: (row) => (
                          <select
                            className="admin-status-select"
                            value={row.status}
                            onChange={(e) => updateLeadStatus(row.lead_id, e.target.value)}
                          >
                            {LEAD_STATUS_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        ),
                      },
                    ]}
                  />
                </div>
              </section>

              {isHeadquarter && (
                <section className="admin-card">
                  <div className="admin-card-body admin-form">
                    <h2>热线推送</h2>
                    <p className="admin-card-note">将线索推送到外呼队列（对接 API 后可直连呼叫中心）。</p>
                    <label>客户姓名<input value={hotlineName} onChange={(event) => setHotlineName(event.target.value)} /></label>
                    <label>手机号<input value={hotlinePhone} onChange={(event) => setHotlinePhone(event.target.value)} /></label>
                    <label>城市
                      <select value={hotlineCity} onChange={(event) => setHotlineCity(event.target.value)}>
                        {cityOptions.map((city) => <option key={city}>{city}</option>)}
                      </select>
                    </label>
                    <label>需求<input value={hotlineInterest} onChange={(event) => setHotlineInterest(event.target.value)} /></label>
                    <button className="btn btn-primary" type="button" disabled={loading} onClick={pushHotline}>
                      {loading ? '推送中…' : '推送到热线'}
                    </button>
                    {hotlineResult && (
                      <p className="admin-card-note">
                        呼叫编号 {hotlineResult.call_id} · 分配经销商 {hotlineResult.assigned_dealer}
                      </p>
                    )}
                  </div>
                </section>
              )}
            </div>
          )}

          {tab === 'service' && isHeadquarter && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>总站人工客服</strong>
                <p>只处理主站在线客服窗口的会话。访客点击“转人工”或继续留言后进入待接入列表，客服可直接在后台回复、结束或重新打开会话。</p>
              </div>
              <CustomerServicePanel token={token!} showNotice={showNotice} />
            </div>
          )}

          {tab === 'metrics' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>运营指标</strong>
                <p>展示各城市的 UV 访问量、线索数量、平均获客成本和 TOP50 排名趋势。当前为模拟数据，配置百度统计 API 后可切换为真实数据。</p>
              </div>
              <section className="admin-card">
                <div className="admin-card-body admin-toolbar">
                  <div>
                    <h2>基础指标</h2>
                    {metricsData?.data_source === 'mock' && (
                      <p className="admin-card-note">当前为演示数据；配置 METRICS_PROVIDER=live 与 BAIDU_TONGJI_TOKEN 后切换真实指标</p>
                    )}
                  </div>
                  <div className="admin-toolbar-controls">
                    <select value={metricsCity} onChange={(event) => setMetricsCity(event.target.value)}>
                      {cityOptions.map((city) => <option key={city}>{city}</option>)}
                    </select>
                    <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={loadMetrics}>刷新</button>
                  </div>
                </div>
              </section>
              {metricsData?.summary && (
                <div className="admin-kpi-grid">
                  <AdminMetricCard label="总访问" value={metricsData.summary.total_uv} hint={metricsData.summary.uv_trend === 'up' ? '较前期上升' : '观察中'} index={0} />
                  <AdminMetricCard label="总线索" value={metricsData.summary.total_leads} hint={metricsData.summary.lead_trend === 'up' ? '较前期上升' : '观察中'} index={1} tone="ok" />
                  <AdminMetricCard label="平均成本" value={`¥${metricsData.summary.avg_cpl}`} hint="按当前模拟数据" index={2} tone="info" />
                  <AdminMetricCard label="TOP50 词" value={metricsData.summary.latest_rank_top50} hint="基础排名指标" index={3} />
                </div>
              )}
              <section className="admin-card">
                <div className="admin-card-body">
                  <AdminTable
                    rows={metricsData?.metrics ?? []}
                    rowKey={(row) => row.date}
                    emptyText="暂无指标数据"
                    columns={[
                      { key: 'date', title: '日期' },
                      { key: 'rank_top50_cnt', title: 'TOP50 词', render: (row) => row.rank_top50_cnt ?? '-' },
                      { key: 'uv', title: '访问', render: (row) => row.uv ?? '-' },
                      { key: 'lead_cnt', title: '线索', render: (row) => row.lead_cnt ?? '-' },
                      {
                        key: 'cpl',
                        title: '成本',
                        render: (row) => (row.cpl != null ? `¥${row.cpl}` : '-'),
                      },
                    ]}
                  />
                </div>
              </section>
            </div>
          )}

          {tab === 'cities' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>城市站管理</strong>
                <p>管理各城市分站的发布状态、子域名配置与基础信息。点击左侧城市进入编辑，可发布或下架分站。</p>
              </div>
              <CityManagerPanel token={token!} showNotice={showNotice} role={role} />
            </div>
          )}

          {tab === 'stores' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>门店管理</strong>
                <p>按城市管理门店列表，支持新建/编辑门店、设置主门店。主门店将作为城市页默认展示门店。</p>
              </div>
              <StoreManagerPanel token={token!} showNotice={showNotice} role={role} />
            </div>
          )}

          {tab === 'citySeo' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>城市 SEO 配置</strong>
                <p>配置各城市分站的 SEO 标题/描述、子域名、canonical_url、robots 策略和关键词。canonical 留空时自动生成 https://子域名.boyamingge.com/。</p>
              </div>
              <CitySeoPanel token={token!} showNotice={showNotice} />
            </div>
          )}

          {tab === 'domains' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>域名 / 二级域名状态</strong>
                <p>查看所有城市分站的子域名配置、访问地址、canonical_url 与发布状态。生产环境请确保所有已发布城市的 subdomain 已正确配置。</p>
              </div>
              <DomainStatusPanel token={token!} showNotice={showNotice} />
            </div>
          )}

          {tab === 'users' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>权限账号管理</strong>
                <p>管理系统用户与角色权限。admin 拥有全部权限；operator 限总部运营；city_manager 限本城市管理；store_manager 限本门店管理。</p>
              </div>
              <UserScopePanel token={token!} showNotice={showNotice} />
            </div>
          )}
          {tab === 'cityContent' && (
            <div className="admin-stack">
              <div className="admin-guide-banner">
                <strong>城市案例与常见问题</strong>
                <p>维护城市分站展示的真实案例、图片和 FAQ，保存后前台会直接读取最新数据。</p>
              </div>
              <CityContentPanel token={token!} showNotice={showNotice} />
            </div>
          )}
          {tab === 'security' && (
            <AccountSettingsPanel
              token={token!}
              user={currentUser}
              showNotice={showNotice}
              onPasswordChanged={handleLogout}
            />
          )}
          {tab === 'audit' && <AuditLogPanel token={token!} showNotice={showNotice} />}
        </AdminTabPanel>
      </section>
    </main>
  );
}

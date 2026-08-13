import { API_BASE, getServerApiBase } from './site';

export type ArticleListItem = {
  slug: string;
  title: string;
  seo_description: string;
  city: string;
  tags: string[];
  geo_summary: string;
  published_at: string;
};

export type ArticleDetail = ArticleListItem & {
  seo_title: string;
  h1: string;
  sections: Array<{ heading: string; level: number; content: string }>;
  faq: Array<{ question: string; answer: string }>;
  cta: string;
  schema_jsonld: string;
};

function resolveApiBase() {
  return typeof window === 'undefined' ? getServerApiBase() : API_BASE;
}

export async function fetchArticles(city?: string): Promise<ArticleListItem[]> {
  const params = new URLSearchParams();
  if (city) params.set('city', city);
  const base = resolveApiBase();
  const url = `${base}/api/v1/articles${params.toString() ? `?${params}` : ''}`;
  try {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.items) ? data.items : [];
  } catch {
    return [];
  }
}

export async function fetchArticle(slug: string): Promise<ArticleDetail | null> {
  const base = resolveApiBase();
  try {
    const res = await fetch(`${base}/api/v1/articles/${slug}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function submitLead(data: {
  name: string;
  phone: string;
  city: string;
  interest?: string;
  source?: string;
}) {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, source: data.source || 'website' }),
    });
  } catch {
    throw new Error('无法连接服务，请确认 Docker 已启动或直接拨打 400 热线');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || '提交失败，请稍后重试或直接拨打 400 热线');
  }
  return res.json();
}

export async function submitCityLead(data: {
  name: string;
  phone: string;
  city_name?: string;
  city_id?: number;
  preferred_store_id?: number;
  interest?: string;
  source?: string;
  source_path?: string;
  host?: string;
  landing_url?: string;
  utm_json?: Record<string, string>;
}) {
  let res: Response;
  try {
    const isClient = typeof window !== 'undefined';
    const body: Record<string, unknown> = {
      ...data,
      source: data.source || 'website',
      source_path: data.source_path || (isClient ? window.location.pathname : undefined),
      // 二级域名归因：客户端自动带 host 与 landing_url
      host: data.host || (isClient ? window.location.host : undefined),
      landing_url: data.landing_url || (isClient ? window.location.href : undefined),
    };
    // 自动解析 utm 参数（仅客户端）
    if (isClient && !data.utm_json) {
      const params = new URLSearchParams(window.location.search);
      const utm: Record<string, string> = {};
      for (const [k, v] of params.entries()) {
        if (k.startsWith('utm_')) utm[k] = v;
      }
      if (Object.keys(utm).length > 0) body.utm_json = utm;
    }
    res = await fetch(`${API_BASE}/api/v1/cities/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('无法连接服务，请确认 Docker 已启动或直接拨打 400 热线');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || '提交失败，请稍后重试或直接拨打 400 热线');
  }
  return res.json();
}

export async function adminLogin(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  } catch {
    throw new Error('无法连接登录服务，请确认 Docker 已启动且 API 正常');
  }
  if (res.status === 401) throw new Error('账号或密码不正确');
  if (!res.ok) throw new Error(`登录服务异常（${res.status}），请执行：docker compose restart nginx fastapi`);
  const data = await res.json();
  sessionStorage.setItem('admin_token', data.access_token);
  sessionStorage.setItem('admin_refresh_token', data.refresh_token);
  return data.access_token;
}

async function refreshAdminToken(): Promise<string | null> {
  const refreshToken = sessionStorage.getItem('admin_refresh_token');
  if (!refreshToken) return null;
  const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return null;
  const data = await response.json();
  sessionStorage.setItem('admin_token', data.access_token);
  sessionStorage.setItem('admin_refresh_token', data.refresh_token);
  window.dispatchEvent(new CustomEvent('admin-token-refreshed', { detail: data.access_token }));
  return data.access_token as string;
}

export type AdminCurrentUser = {
  id: number;
  username: string;
  role: string;
  dealer_code: string | null;
  city_id: number | null;
  store_id: number | null;
  is_active: boolean;
  password_changed_at: string | null;
  created_at: string | null;
  last_login_at: string | null;
};

export async function adminGetMe(token: string): Promise<AdminCurrentUser> {
  return adminFetch<AdminCurrentUser>('/api/v1/auth/me', token);
}

export async function adminFetch<T>(path: string, token: string, options?: RequestInit): Promise<T> {
  const request = (accessToken: string) => fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
        ...(options?.headers || {}),
      },
    });
  const storedToken = typeof window !== 'undefined' ? sessionStorage.getItem('admin_token') : null;
  let res = await request(storedToken || token);
  if (res.status === 401) {
    const refreshed = await refreshAdminToken();
    if (refreshed) res = await request(refreshed);
  }
  if (res.status === 401) {
    sessionStorage.removeItem('admin_token');
    sessionStorage.removeItem('admin_refresh_token');
    throw new Error('登录已过期，请重新登录');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    let detail = err.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((e: { msg?: string; loc?: string[] }) => {
        const field = e.loc?.slice(-1)[0] || '';
        return field ? `${field}: ${e.msg || '验证失败'}` : (e.msg || '验证失败');
      }).join('; ');
    }
    throw new Error(detail || `请求失败 ${res.status}`);
  }
  return res.json();
}

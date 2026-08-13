/**
 * 二级域名解析工具。
 *
 * 设计目标：
 * - 生产环境支持 *.boyamingge.com 城市二级域名。
 * - 本地开发支持 guangzhou.localhost:3000、shenzhen.localhost:3000。
 * - admin/api/www 等保留子域名不被当作城市。
 * - middleware 只用本模块做 host 解析与 rewrite，不查数据库。
 */

/** 根域名，例如 boyamingge.com（不含协议、不含 www）。 */
export const ROOT_DOMAIN =
  process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com';

/** 后台域名，例如 https://admin.boyamingge.com。 */
export const ADMIN_URL =
  process.env.NEXT_PUBLIC_ADMIN_URL || `https://admin.${ROOT_DOMAIN}`;

/** 官站域名，例如 https://www.boyamingge.com。 */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || `https://www.${ROOT_DOMAIN}`;

/** 生产环境是否把 /{city} 路径 301 到 https://{city}.boyamingge.com/。 */
export const ENABLE_CITY_PATH_REDIRECT =
  process.env.NEXT_PUBLIC_ENABLE_CITY_PATH_REDIRECT === 'true';

/** 城市域名模式：subdomain（二级域名）| path（仅路径，MVP 兼容）。 */
export const CITY_DOMAIN_MODE =
  process.env.NEXT_PUBLIC_CITY_DOMAIN_MODE || 'subdomain';

/**
 * 保留子域名：不能作为城市 slug。
 * admin / api / www / static / assets / cdn / m / mail / ftp / localhost。
 */
export const RESERVED_SUBDOMAINS = [
  'www',
  'admin',
  'api',
  'static',
  'assets',
  'cdn',
  'm',
  'mail',
  'ftp',
  'localhost',
] as const;

/** 本地开发根域名后缀（xxx.localhost）。 */
const LOCALHOST_ROOT = 'localhost';

/**
 * 规范化 host：去掉端口、转小写、去首尾空白。
 * 例：`Guangzhou.localhost:3000` -> `guangzhou.localhost`
 */
export function normalizeHost(host: string | null | undefined): string {
  if (!host) return '';
  return host.trim().toLowerCase().split(':')[0];
}

/** 是否为 localhost 本地开发环境。 */
export function isLocalhost(host: string | null | undefined): boolean {
  const normalized = normalizeHost(host);
  return normalized === LOCALHOST_ROOT || normalized.endsWith(`.${LOCALHOST_ROOT}`);
}

/** 判断子域名是否为保留子域名。 */
export function isReservedSubdomain(subdomain: string | null | undefined): boolean {
  if (!subdomain) return false;
  const lower = subdomain.toLowerCase();
  return (RESERVED_SUBDOMAINS as readonly string[]).includes(lower);
}

/**
 * 从 host 中提取城市子域名。
 *
 * - `guangzhou.localhost` -> `guangzhou`
 * - `guangzhou.boyamingge.com` -> `guangzhou`
 * - `www.boyamingge.com` -> `www`（保留，调用方需自行判断）
 * - `boyamingge.com` -> `''`（根域名，无子域名）
 * - `localhost` -> `''`
 *
 * @returns 子域名字符串；根域名/无子域名时返回空串。
 */
export function extractSubdomain(host: string | null | undefined): string {
  const normalized = normalizeHost(host);
  if (!normalized) return '';

  // 本地开发：xxx.localhost
  if (normalized === LOCALHOST_ROOT) return '';
  if (normalized.endsWith(`.${LOCALHOST_ROOT}`)) {
    const parts = normalized.split('.');
    // xxx.localhost -> xxx
    if (parts.length === 2) return parts[0];
    // 多级不处理，返回空
    return '';
  }

  // 生产环境：xxx.boyamingge.com
  const root = ROOT_DOMAIN.toLowerCase();
  if (normalized === root) return '';
  if (normalized.endsWith(`.${root}`)) {
    const sub = normalized.slice(0, -(`.${root}`).length);
    // 仅取第一段作为城市子域名（不支持多级子域名）
    const firstSegment = sub.split('.')[0];
    return firstSegment || '';
  }

  // 其它 host（如 IP、自定义域名）不解析
  return '';
}

/** 城市子域名类型判断结果。 */
export type SubdomainKind = 'city' | 'reserved' | 'root' | 'none';

/**
 * 判断 host 的子域名类型。
 * - `root`：根域名或 www（品牌总站）。
 * - `reserved`：admin/api 等保留子域名。
 * - `city`：城市子域名。
 * - `none`：无法识别（如 IP）。
 */
export function classifyHost(host: string | null | undefined): {
  kind: SubdomainKind;
  subdomain: string;
} {
  const sub = extractSubdomain(host);
  if (!sub) {
    // 根域名或 localhost 根
    const normalized = normalizeHost(host);
    if (
      normalized === ROOT_DOMAIN.toLowerCase() ||
      normalized === `www.${ROOT_DOMAIN.toLowerCase()}` ||
      normalized === LOCALHOST_ROOT
    ) {
      return { kind: 'root', subdomain: '' };
    }
    return { kind: 'none', subdomain: '' };
  }
  if (sub === 'www') return { kind: 'root', subdomain: '' };
  if (isReservedSubdomain(sub)) return { kind: 'reserved', subdomain: sub };
  return { kind: 'city', subdomain: sub };
}

/**
 * 构建城市二级域名 URL。
 * - 生产：https://guangzhou.boyamingge.com/
 * - 本地：http://guangzhou.localhost:3000/
 */
export function buildCityUrl(subdomain: string, port?: number): string {
  const sub = subdomain.toLowerCase();
  if (isLocalhost(typeof window !== 'undefined' ? window.location.host : null)) {
    const portSuffix = port && port !== 80 ? `:${port}` : '';
    return `http://${sub}.localhost${portSuffix || ':3000'}`;
  }
  return `https://${sub}.${ROOT_DOMAIN}`;
}

/**
 * 构建城市页 canonical URL（始终指向二级域名，避免路径版与子域名版双收录）。
 * 例：https://guangzhou.boyamingge.com/
 */
export function buildCanonicalUrl(subdomain: string | null | undefined): string | null {
  if (!subdomain) return null;
  return `https://${subdomain.toLowerCase()}.${ROOT_DOMAIN}/`;
}

/** 构建后台 URL（城市子域名访问 /admin 时跳转用）。 */
export function buildAdminUrl(path = '/admin'): string {
  return `${ADMIN_URL.replace(/\/$/, '')}${path}`;
}

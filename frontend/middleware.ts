import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

import {
  ADMIN_URL,
  ROOT_DOMAIN,
  ENABLE_CITY_PATH_REDIRECT,
  isLocalhost,
  classifyHost,
} from '@/lib/domain';
import { CITY_SLUGS } from '@/lib/citySlugs';

/**
 * 二级域名多城市 MVP middleware。
 *
 * 规则（详见 二级域名多城市总部后台改造计划.md §7.2）：
 * 1. 读取 Host，提取子域名。
 * 2. 根域名 / www / admin / api：放行，不 rewrite。
 * 3. 静态资源 / _next / /api / robots / sitemap / favicon：放行。
 * 4. 城市子域名且 path === '/'：rewrite 到 /{subdomain}。
 * 5. 城市子域名访问 /admin：redirect 到后台域名（或 404）。
 * 6. MVP 阶段只 rewrite 城市子域名根路径 /，不 rewrite 其它路径。
 *
 * middleware 不查数据库；城市是否存在由 app/[city]/page.tsx 或 API 404 兜底。
 */

/** 不需要 rewrite 的路径前缀。 */
const SKIP_PREFIXES = ['/_next/', '/api/', '/admin'];

/** 命中即放行的精确路径（静态/SEO 文件）。 */
const SKIP_EXACT_PATHS = new Set([
  '/',
  '/favicon.ico',
  '/robots.txt',
  '/sitemap.xml',
  '/manifest.webmanifest',
]);

function shouldSkipPath(pathname: string): boolean {
  // 静态文件扩展名
  if (/\.(ico|png|jpg|jpeg|gif|svg|webp|avif|css|js|map|txt|xml|json|woff|woff2|ttf|eot)$/.test(pathname)) {
    return true;
  }
  for (const prefix of SKIP_PREFIXES) {
    if (pathname.startsWith(prefix)) return true;
  }
  return false;
}

function isLocalAdminRoot(host: string | null, pathname: string): boolean {
  if (pathname !== '/') return false;
  if (!host) return false;
  const normalized = host.trim().toLowerCase();
  return normalized === 'localhost:20001' || normalized === '127.0.0.1:20001';
}

export function middleware(request: NextRequest) {
  const host = request.headers.get('host');
  const { kind, subdomain } = classifyHost(host);
  const { pathname, search } = request.nextUrl;

  if (isLocalAdminRoot(host, pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = '/admin';
    return NextResponse.redirect(url, 307);
  }

  // 非城市子域名（根域名 / www / admin / api / 无法识别）
  if (kind !== 'city') {
    // Fix 4: 生产环境路径版城市页 301 到二级域名
    // /guangzhou -> https://guangzhou.boyamingge.com/（仅生产、仅已知城市 slug）
    if (ENABLE_CITY_PATH_REDIRECT && !isLocalhost(host) && kind === 'root') {
      const segments = pathname.split('/').filter(Boolean);
      if (segments.length === 1 && CITY_SLUGS.includes(segments[0])) {
        const citySlug = segments[0];
        const target = `https://${citySlug}.${ROOT_DOMAIN}/${search}`;
        return NextResponse.redirect(target, 301);
      }
    }
    return NextResponse.next();
  }

  // 城市子域名访问 /admin：跳转到后台域名，避免城市站进入后台
  if (pathname === '/admin' || pathname.startsWith('/admin/')) {
    const adminBase = ADMIN_URL || `https://admin.${process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com'}`;
    const target = `${adminBase.replace(/\/$/, '')}${pathname}${search}`;
    return NextResponse.redirect(target, 307);
  }

  // 静态资源 / _next / api / robots / sitemap：放行
  if (shouldSkipPath(pathname)) {
    return NextResponse.next();
  }

  // MVP：只 rewrite 城市子域名根路径 / -> /{subdomain}
  if (pathname === '/') {
    const url = request.nextUrl.clone();
    url.pathname = `/${subdomain}`;
    return NextResponse.rewrite(url);
  }

  // 其它路径 MVP 阶段放行，不做 /{subdomain}{pathname} rewrite
  // 避免与不存在的城市级路由冲突导致 404
  return NextResponse.next();
}

export const config = {
  /**
   * matcher：排除 _next/static、_next/image、favicon 等静态资源，
   * 其余请求进入 middleware（内部仍会按 host/path 判断是否真正处理）。
   */
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

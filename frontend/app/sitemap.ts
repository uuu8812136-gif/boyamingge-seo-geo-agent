import type { MetadataRoute } from 'next';
import { fetchArticles } from '@/lib/api';
import { getServerApiBase } from '@/lib/site';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost';

export const dynamic = 'force-dynamic';

type ApiCity = {
  slug: string;
  subdomain?: string | null;
  canonical_url?: string | null;
  is_active?: boolean;
  has_store?: boolean;
  seo_indexable?: boolean;
  content_status?: string;
};

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // 静态页面：不含 /admin（admin 路径禁止收录，已在 robots.ts 中 disallow）
  const staticPages: MetadataRoute.Sitemap = [
    { url: siteUrl, lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
    { url: `${siteUrl}/articles`, lastModified: new Date(), changeFrequency: 'daily', priority: 0.9 },
    { url: `${siteUrl}/stores`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
  ];

  // 拉取后端城市列表，只输出 seo_indexable=true && content_status='published' && is_active=true 的城市
  // URL 优先使用后端 canonical_url（即 https://子域名.boyamingge.com/），fallback 到 /{slug} 路径
  let cities: ApiCity[] = [];
  try {
    const base = getServerApiBase();
    const res = await fetch(`${base}/api/v1/cities?active_only=true`, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      cities = Array.isArray(data.items) ? data.items as ApiCity[] : [];
    }
  } catch {
    // 后端不可用时不输出未经核验的城市页。
  }

  const publishedCities = cities.filter(
    (c) => c.is_active !== false && c.seo_indexable !== false && c.content_status === 'published',
  );

  const cityPages: MetadataRoute.Sitemap = publishedCities.map((c) => {
    const canonical = c.canonical_url || (c.subdomain ? `https://${c.subdomain}.${process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com'}/` : `${siteUrl}/${c.slug}`);
    return {
      url: canonical,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.9,
    };
  });

  let articleSlugs: string[] = [];
  try {
    const articles = await fetchArticles();
    articleSlugs = [...new Set(articles.map((item) => item.slug))];
  } catch {
    // 后端不可用时不输出文章页。
  }

  const articlePages = articleSlugs.map((slug) => ({
    url: `${siteUrl}/articles/${slug}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  return [...staticPages, ...cityPages, ...articlePages];
}

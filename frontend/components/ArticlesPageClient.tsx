'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import type { ArticleListItem } from '@/lib/api';
import { ARTICLE_CATEGORIES, formatArticleExcerpt, resolveArticleCategory } from '@/lib/site';

export default function ArticlesPageClient({ articles: initial }: { articles: ArticleListItem[] }) {
  const [articles] = useState(initial);
  const [category, setCategory] = useState<string>('all');

  const filtered = useMemo(() => {
    if (category === 'all') return articles;
    return articles.filter((a) => resolveArticleCategory(a.slug, a.tags) === category);
  }, [articles, category]);

  return (
    <>
      <Header />
      <main className="articles-page page-with-solid-header">
        <section className="inner-page-hero inner-page-hero--articles">
          <div className="container inner-page-hero-grid">
            <div className="inner-page-hero-copy">
              <p className="eyebrow eyebrow-light">选购参考</p>
              <h1>门窗选购<br />指南</h1>
              <p>安装避坑、本地案例与价格说明，供装修前参考。</p>
            </div>
            <aside className="inner-page-proof-card articles-proof-card">
              <span>内容范围</span>
              <strong>{articles.length > 0 ? `${articles.length} 篇已发布指南` : '持续更新专业指南'}</strong>
              <p>围绕选材、施工、验收与本地服务整理，帮助您在测量前把关键问题想清楚。</p>
            </aside>
          </div>
        </section>

        <section className="section articles-list-section">
          <div className="container">
            <nav className="breadcrumb articles-breadcrumb" aria-label="面包屑导航">
              <ol>
                <li><Link href="/">首页</Link><span className="sep">/</span></li>
                <li><span>选购指南</span></li>
              </ol>
            </nav>

            {articles.length > 0 && (
              <div className="filter-tabs articles-filter-tabs">
                <button type="button" className={category === 'all' ? 'active' : ''} onClick={() => setCategory('all')}>
                  全部
                </button>
                {ARTICLE_CATEGORIES.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className={category === c.id ? 'active' : ''}
                    onClick={() => setCategory(c.id)}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            )}

            {filtered.length > 0 ? (
              <div className="article-grid">
                {filtered.map((article, index) => (
                  <article key={article.slug} className="article-card">
                    <span className="article-card-index">{String(index + 1).padStart(2, '0')}</span>
                    <p className="article-card-meta">
                      <span>{ARTICLE_CATEGORIES.find((c) => c.id === resolveArticleCategory(article.slug, article.tags))?.label ?? '指南'}</span>
                      <span>{article.city}</span>
                      <time>{article.published_at}</time>
                    </p>
                    <h2><Link href={`/articles/${article.slug}`}>{article.title}</Link></h2>
                    <p>{formatArticleExcerpt(article.seo_description || article.geo_summary, article.title)}</p>
                    <Link href={`/articles/${article.slug}`} className="article-card-link">阅读全文 →</Link>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state empty-state--spacious">
                暂无已发布内容，文章将在后台审核发布后显示。
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

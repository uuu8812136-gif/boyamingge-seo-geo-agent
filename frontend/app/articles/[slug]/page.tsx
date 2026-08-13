import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import LeadForm from '@/components/LeadForm';
import Breadcrumb from '@/components/Breadcrumb';
import { BlurText, Reveal, SplitText, Threads } from '@/components/react-bits';
import { fetchArticle } from '@/lib/api';
import { ARTICLE_CATEGORIES, formatArticleExcerpt, formatArticleText, resolveArticleCategory } from '@/lib/site';

export const revalidate = 3600;
export const dynamic = 'force-dynamic';

type PageProps = { params: Promise<{ slug: string }> };

function safeJsonLd(value: string): string | null {
  try {
    return JSON.stringify(JSON.parse(value)).replace(/</g, '\\u003c');
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) return {};
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost';
  const title = article.seo_title || article.h1;
  const description = formatArticleExcerpt(article.seo_description || article.geo_summary, article.h1, 180);
  return {
    title: { absolute: title },
    description,
    alternates: { canonical: `${siteUrl}/articles/${slug}` },
    openGraph: {
      title,
      description,
      type: 'article',
      url: `${siteUrl}/articles/${slug}`,
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

export default async function ArticleDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) notFound();

  const category = ARTICLE_CATEGORIES.find((c) => c.id === resolveArticleCategory(slug, article.tags));
  const jsonLd = safeJsonLd(article.schema_jsonld);
  const summary = formatArticleExcerpt(article.geo_summary || article.seo_description, article.h1, 200);
  const sections = article.sections
    .map((section) => ({ ...section, content: formatArticleText(section.content, section.heading) }))
    .filter((section) => section.content && !(article.sections.length === 1 && section.content === summary));

  return (
    <>
      <Header variant="overlay" />
      {jsonLd && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd }} />}

      <article>
        {/* Hero：深色 + Threads 砖红流动背景 */}
        <header className="article-hero">
          <div className="article-hero-bg">
            <Threads color={[0.77, 0.36, 0.15]} amplitude={0.9} distance={0.08} enableMouseInteraction={false} />
          </div>
          <div className="hero-overlay" />
          <div className="container container-narrow article-hero-content">
            <div className="article-breadcrumb">
              <Breadcrumb items={[{ name: '首页', href: '/' }, { name: '选购指南', href: '/articles' }, { name: article.h1 }]} />
            </div>
            <div className="article-meta">
              {category?.label && <span>{category.label}</span>}
              <span>适用城市：{article.city}</span>
              <time>更新：{article.published_at}</time>
            </div>
            <SplitText tag="h1" text={article.h1} delay={35} duration={0.6} blur y={28} />
            <BlurText text={summary} delay={250} animateBy="words" className="article-summary-box" />
          </div>
        </header>

        {/* 正文 */}
        <div className="article-body">
          <div className="container container-narrow">
            {sections.length > 0 && (
              <Reveal>
                <div className="article-prose">
                  {sections.map((section) => {
                    const Tag = section.level === 3 ? 'h3' : 'h2';
                    return (
                      <section key={section.heading}>
                        <Tag>{section.heading}</Tag>
                        <p>{section.content}</p>
                      </section>
                    );
                  })}
                </div>
              </Reveal>
            )}

            <Reveal>
              <section className="article-notes">
                <h2>注意事项</h2>
                <ul>
                  <li>文中价格区间仅供参考，实际以门店测量方案为准。</li>
                  <li>不同楼层、朝向与洞口条件会影响型材与玻璃选型。</li>
                  <li>安装前请确认物业对封阳台、换窗的相关要求。</li>
                </ul>
              </section>
            </Reveal>

            <Reveal>
              <section>
                <h2 style={{ fontSize: 28, fontWeight: 800, color: 'var(--ink)', margin: '48px 0 20px' }}>相关问题</h2>
                <dl className="faq-list">
                  {article.faq.map((f) => (
                    <div key={f.question} className="faq-row">
                      <dt>{f.question}</dt>
                      <dd>{f.answer}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            </Reveal>

            {/* 内联 CTA */}
            <Reveal>
              <section className="article-cta-inline">
                <div>
                  <h3>{article.cta}</h3>
                  <p>电话咨询或预约免费上门测量</p>
                </div>
                <div className="article-cta-actions">
                  <a href="tel:4008886688" className="btn btn-primary">电话咨询</a>
                  <a href="#lead" className="btn btn-ghost" style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.3)' }}>预约测量</a>
                </div>
              </section>
            </Reveal>

            {/* 预约表单 */}
            <section id="lead" className="article-book" style={{ marginTop: 64 }}>
              <Reveal>
                <h2 style={{ fontSize: 28, fontWeight: 800, color: 'var(--ink)', margin: '0 0 24px' }}>预约测量</h2>
                <div className="cta-form" style={{ padding: 32 }}>
                  <LeadForm defaultCity={article.city} />
                </div>
              </Reveal>
            </section>
          </div>
        </div>
      </article>

      <Footer />
    </>
  );
}

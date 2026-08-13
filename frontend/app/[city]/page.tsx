import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import BookingButton from '@/components/BookingButton';
import Breadcrumb from '@/components/Breadcrumb';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import LeadForm from '@/components/LeadForm';
import { BlurText, Reveal, SplitText, SpotlightCard, Threads, TiltedCard } from '@/components/react-bits';
import { AI_CITY_STATION_VALUES, HERO_IMAGE, SITE, formatArticleExcerpt, getServerApiBase } from '@/lib/site';

export const revalidate = 3600;
export const dynamic = 'force-dynamic';

type PageProps = {
  params: Promise<{ city: string }>;
};

// ── 后端返回类型（CityDetailResponse 关键字段）──
type BackendStore = {
  id: number;
  store_name: string;
  city: string;
  district: string;
  address: string;
  phone: string;
  opening_hours: string | null;
  services: string[];
  is_primary: boolean;
  booking_url: string | null;
};

type BackendCase = {
  id: number;
  city_id: number;
  title: string;
  service_type: string | null;
  content: string;
  images: string[];
};

type BackendFaq = {
  id: number;
  city_id: number;
  question: string;
  answer: string;
};

type ArticleListItem = {
  slug: string;
  title: string;
  seo_description: string;
  city: string;
  tags: string[];
  geo_summary: string;
  published_at: string;
};

async function fetchArticlesByCity(cityName: string): Promise<ArticleListItem[]> {
  const base = getServerApiBase();
  try {
    const res = await fetch(`${base}/api/v1/articles?city=${encodeURIComponent(cityName)}`, {
      cache: 'no-store',
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []) as ArticleListItem[];
  } catch {
    return [];
  }
}

type BackendCityDetail = {
  id: number;
  name: string;
  slug: string;
  province: string;
  is_active: boolean;
  has_store: boolean;
  seo_title: string | null;
  seo_description: string | null;
  hero_title: string | null;
  hero_subtitle: string | null;
  subdomain: string | null;
  canonical_url: string | null;
  seo_keywords: string[];
  seo_indexable: boolean;
  robots_policy: string;
  hero_image: string | null;
  service_area_json: string[];
  service_tags: string[];
  content_status: string;
  primary_store: BackendStore | null;
  stores: BackendStore[];
  cases: BackendCase[];
  faqs: BackendFaq[];
};

type FetchCityResult =
  | { status: 'ok'; data: BackendCityDetail }
  | { status: 'not_found' }
  | { status: 'error' };

async function fetchCityDetail(slug: string): Promise<FetchCityResult> {
  const base = getServerApiBase();
  try {
    const res = await fetch(`${base}/api/v1/cities/${slug}`, { cache: 'no-store' });
    if (res.status === 404) return { status: 'not_found' };
    if (!res.ok) return { status: 'error' };
    const data = (await res.json()) as BackendCityDetail;
    return { status: 'ok', data };
  } catch {
    return { status: 'error' };
  }
}

function uniqueCompactList(values: Array<string | null | undefined>, fallback: string[] = [], limit = 6): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of [...values, ...fallback]) {
    const value = String(item || '').trim();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    result.push(value);
    if (result.length >= limit) break;
  }
  return result;
}

function buildCoverageKeywords(cityName: string, districts: string[], services: string[]): string[] {
  const serviceTerms = uniqueCompactList(services, ['系统门窗', '阳台封窗', '旧窗改造', '断桥铝门窗'], 4);
  const districtTerms = uniqueCompactList(districts, [cityName], 5);
  const keywords = [
    ...serviceTerms.map((service) => `${cityName}${service}`),
    ...districtTerms.flatMap((district) => serviceTerms.slice(0, 2).map((service) => `${district}${service}`)),
  ];
  return uniqueCompactList(keywords, [], 12);
}

function safeJsonLd(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

function buildCityJsonLd(params: {
  backend: BackendCityDetail;
  canonicalUrl: string;
  heroTitle: string;
  heroSubtitle: string;
  primaryStore: BackendStore | null;
  districts: string[];
  services: string[];
  faqs: Array<{ question: string; answer: string }>;
  cases: Array<{ id: string; need: string; solution: string; image: string; tag: string }>;
}) {
  const { backend, canonicalUrl, heroTitle, heroSubtitle, primaryStore, districts, services, faqs, cases } = params;
  const businessId = `${canonicalUrl}#localbusiness`;
  const pageId = `${canonicalUrl}#webpage`;
  const serviceList = uniqueCompactList(services, ['系统门窗安装', '旧窗改造'], 6);
  const areaList = uniqueCompactList(districts, [backend.name], 8);

  const graph: Array<Record<string, unknown>> = [
    {
      '@type': 'LocalBusiness',
      '@id': businessId,
      name: primaryStore?.store_name || `${SITE.brandFull}${backend.name}服务中心`,
      url: canonicalUrl,
      telephone: primaryStore?.phone || SITE.hotline,
      image: backend.hero_image || HERO_IMAGE,
      address: primaryStore
        ? {
            '@type': 'PostalAddress',
            streetAddress: primaryStore.address,
            addressLocality: backend.name,
            addressRegion: backend.province,
            addressCountry: 'CN',
          }
        : {
            '@type': 'PostalAddress',
            addressLocality: backend.name,
            addressRegion: backend.province,
            addressCountry: 'CN',
          },
      areaServed: areaList.map((name) => ({ '@type': 'City', name })),
      makesOffer: serviceList.map((name) => ({
        '@type': 'Offer',
        itemOffered: { '@type': 'Service', name: `${backend.name}${name}` },
      })),
    },
    {
      '@type': 'WebPage',
      '@id': pageId,
      url: canonicalUrl,
      name: heroTitle,
      description: backend.seo_description || heroSubtitle,
      inLanguage: 'zh-CN',
      about: { '@id': businessId },
      keywords: buildCoverageKeywords(backend.name, districts, services),
    },
    {
      '@type': 'Service',
      '@id': `${canonicalUrl}#service`,
      name: `${backend.name}门窗安装与旧窗改造`,
      provider: { '@id': businessId },
      areaServed: areaList.map((name) => ({ '@type': 'City', name })),
      serviceType: serviceList,
    },
  ];

  if (faqs.length > 0) {
    graph.push({
      '@type': 'FAQPage',
      '@id': `${canonicalUrl}#faq`,
      mainEntity: faqs.slice(0, 6).map((faq) => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: { '@type': 'Answer', text: faq.answer },
      })),
    });
  }

  if (cases.length > 0) {
    graph.push({
      '@type': 'ItemList',
      '@id': `${canonicalUrl}#cases`,
      name: `${backend.name}门窗本地案例`,
      itemListElement: cases.slice(0, 6).map((item, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        item: {
          '@type': 'CreativeWork',
          name: item.need,
          text: item.solution,
          image: item.image,
          about: item.tag || `${backend.name}门窗服务`,
        },
      })),
    });
  }

  return { '@context': 'https://schema.org', '@graph': graph };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { city: citySlug } = await params;
  const result = await fetchCityDetail(citySlug);
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost';

  if (result.status !== 'ok') return {};

  const backend = result.data;
  const nameBase = backend.name;

  const seoTitle = backend.seo_title || `${nameBase}门窗安装与旧窗改造`;
  const seoDescription =
    backend.seo_description || `博雅敏格${nameBase}门窗服务，支持预约上门测量。`;

  const canonical = backend.canonical_url || `${siteUrl}/${citySlug}`;

  const meta: Metadata = {
    title: seoTitle,
    description: seoDescription,
    alternates: { canonical },
  };

  if (backend.seo_indexable === false || backend.robots_policy.startsWith('noindex')) {
    meta.robots = {
      index: false,
      follow: backend.robots_policy === 'noindex_follow',
    };
  }

  return meta;
}

export default async function CityPage({ params }: PageProps) {
  const { city: citySlug } = await params;
  const result = await fetchCityDetail(citySlug);
  if (result.status !== 'ok') notFound();

  const backend = result.data;
  const cityName = backend.name;
  const heroTitle = backend.hero_title || `博雅敏格${cityName}门窗安装与旧窗改造`;
  const heroSubtitle = backend.hero_subtitle || `${cityName}门窗服务，支持预约上门测量`;

  const primaryStore = backend.primary_store || backend.stores[0] || null;
  const storeAddress = primaryStore?.address || '';
  const storePhone = primaryStore?.phone || SITE.hotline;
  const storeHours = primaryStore?.opening_hours || '';
  const stores = backend.stores;

  const cases =
    backend.cases.length > 0
      ? backend.cases.map((c) => ({
          id: String(c.id),
          city: cityName,
          district: c.service_type || '',
          layout: '',
          image: (c.images?.[0] || '/images/cases/balcony-window.webp').replace(/\.jpg$/, '.webp'),
          need: c.title,
          solution: c.content,
          duration: '',
          result: '',
          tag: c.service_type || '',
        }))
      : [];

  const faqs =
    backend.faqs.length > 0
      ? backend.faqs.map((f) => ({ question: f.question, answer: f.answer }))
      : [];

  const districts = backend.service_area_json || [];
  const services = backend.service_tags || [];
  const displayStores = stores;

  const cityArticles = await fetchArticlesByCity(cityName);
  const aiServices = uniqueCompactList(services, ['系统门窗', '阳台封窗', '旧窗改造', '断桥铝门窗'], 4);
  const aiDistricts = uniqueCompactList(districts, [cityName], 5);
  const coverageKeywords = buildCoverageKeywords(cityName, aiDistricts, aiServices);
  const canonicalUrl =
    backend.canonical_url ||
    `${(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost').replace(/\/$/, '')}/${citySlug}`;
  const cityJsonLd = buildCityJsonLd({
    backend,
    canonicalUrl,
    heroTitle,
    heroSubtitle,
    primaryStore,
    districts: aiDistricts,
    services: aiServices,
    faqs,
    cases,
  });
  const citySubdomainLabel = backend.subdomain
    ? `${backend.subdomain}.${process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com'}`
    : `/${citySlug}`;
  const aiAnswer = `${SITE.brandFull}${cityName}服务页汇总了${aiServices.join('、')}等需求，覆盖${aiDistricts.join('、')}等区域，${primaryStore ? `可通过${primaryStore.store_name}` : '可通过本地门店'}预约上门测量，联系电话 ${storePhone}。`;
  const aiSignalRows = [
    {
      label: '城市分站',
      value: citySubdomainLabel,
      desc: '独立 canonical、城市标题和本地服务页，承接城市搜索词。',
    },
    {
      label: '本地实体',
      value: primaryStore ? primaryStore.store_name : `${cityName}服务中心`,
      desc: primaryStore ? `${primaryStore.address}，电话 ${storePhone}` : `默认承接 ${cityName} 上门咨询。`,
    },
    {
      label: '内容证据',
      value: `${cases.length} 个案例 / ${faqs.length} 个问答 / ${cityArticles.length} 篇指南`,
      desc: '案例、FAQ 和文章共同支撑 AI 摘要里的本地可信度。',
    },
    {
      label: '转化入口',
      value: storePhone,
      desc: '电话、表单和门店分配保持一致，减少 AI 推荐后的跳失。',
    },
  ];
  const seoSections: Array<{ title: string; content: string }> = [
    {
      title: '城市词覆盖',
      content: `重点覆盖 ${coverageKeywords.slice(0, 6).join('、')} 等本地搜索词。`,
    },
    {
      title: 'AI 可引用结构',
      content: '页面同步输出 LocalBusiness、Service、FAQPage 和案例列表结构化数据。',
    },
    ...AI_CITY_STATION_VALUES.slice(1, 4).map((item) => ({ title: item.title, content: item.desc })),
  ];

  const cityId: number | undefined = backend.id;
  const preferredStoreId: number | undefined = primaryStore?.id;

  return (
    <>
      <Header variant="overlay" />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: safeJsonLd(cityJsonLd) }} />

      <main className="city-page">
        {/* Hero：深色 + Threads 砖红流动背景 */}
        <section className="city-hero">
          <div className="city-hero-bg">
            <Threads color={[0.77, 0.36, 0.15]} amplitude={1.1} distance={0.08} enableMouseInteraction={false} />
          </div>
          <div className="hero-overlay" />
          <div className="container hero-layout city-hero-layout">
            <div className="hero-content city-hero-copy">
              <div className="article-breadcrumb city-hero-breadcrumb">
                <Breadcrumb items={[{ name: '首页', href: '/' }, { name: `${cityName}门窗服务` }]} />
              </div>
              <p className="hero-eyebrow">{cityName}门店服务</p>
              <SplitText tag="h1" text={heroTitle} delay={40} duration={0.6} blur y={32} className="hero-title city-hero-title" />
              <BlurText text={heroSubtitle} delay={250} animateBy="words" className="city-hero-lead" />
              <div className="hero-actions">
                <BookingButton label="预约上门测量" city={cityName} />
                <a className="btn btn-ghost" href={`tel:${storePhone.replace(/-/g, '')}`}>
                  {storePhone}
                </a>
              </div>
            </div>
            {primaryStore && (
              <aside className="hero-panel city-hero-panel">
                <p className="hero-panel-title">{primaryStore.store_name}</p>
                <ul>
                  {storeHours && <li><strong>01</strong><span>{storeHours}</span></li>}
                  {districts.length > 0 && <li><strong>02</strong><span>{districts.slice(0, 3).join(' / ')}等区域可预约</span></li>}
                  <li><strong>03</strong><span>{storeAddress}</span></li>
                </ul>
              </aside>
            )}
          </div>
        </section>

        {/* 门店信息 */}
        {(displayStores.length > 0 || districts.length > 0 || services.length > 0) && <section className="section city-local-summary" id="stores">
          <div className="container">
            <div className="city-local-summary-head">
              <Reveal className="city-local-title">
                <p className="eyebrow">门店信息</p>
                <h2 className="section-title">{cityName}体验中心</h2>
                <p className="section-desc">选择就近门店预约上门测量。</p>
              </Reveal>

              <div className="city-local-top-cards" aria-label={`${cityName}服务范围与需求`}>
                <Reveal>
                  <SpotlightCard className="city-store-card city-local-info-card" spotlightColor="rgba(74, 107, 122, 0.10)">
                    <p className="eyebrow">服务区域</p>
                    <h3 className="city-local-card-title">{cityName}可预约区域</h3>
                    <div className="chip-list">
                      {districts.map((district) => (
                        <span key={district} className="chip">{district}</span>
                      ))}
                    </div>
                  </SpotlightCard>
                </Reveal>
                <Reveal delay={80}>
                  <SpotlightCard className="city-store-card city-local-info-card" spotlightColor="rgba(196, 92, 38, 0.12)">
                    <p className="eyebrow">服务项目</p>
                    <h3 className="city-local-card-title">常见上门需求</h3>
                    <div className="chip-list">
                      {services.map((service: string) => (
                        <span key={service} className="chip chip-accent">{service}</span>
                      ))}
                    </div>
                  </SpotlightCard>
                </Reveal>
              </div>
            </div>

            <div className="city-store-equal-list city-store-equal-list--below" aria-label={`${cityName}门店列表`}>
              {displayStores.map((store, i) => (
                <Reveal key={store.id || store.store_name} delay={i * 60}>
                  <article className="city-store-equal-card">
                    <div className="city-store-equal-head">
                      <span>{store.district || `门店 ${i + 1}`}</span>
                      <h3>{store.store_name}</h3>
                    </div>
                    <p className="city-store-equal-address">{store.address}</p>
                    <div className="city-store-equal-meta">
                      <span>{store.opening_hours || storeHours}</span>
                      <span>{store.phone}</span>
                    </div>
                    <div className="city-store-equal-actions">
                      <a href="#lead" className="btn btn-primary">预约</a>
                      <a href={`tel:${store.phone.replace(/-/g, '')}`} className="btn btn-outline">电话</a>
                    </div>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>}

        <section className="section city-ai-visibility" id="ai-visibility">
          <div className="container city-ai-layout">
            <Reveal className="city-ai-answer">
              <p className="eyebrow">AI 可引用答案</p>
              <h2 className="section-title">{cityName}门窗服务，信息完整可核验</h2>
              <p className="city-ai-answer-text">{aiAnswer}</p>
              <div className="city-keyword-cloud" aria-label={`${cityName}关键词覆盖`}>
                {coverageKeywords.map((keyword) => (
                  <span key={keyword}>{keyword}</span>
                ))}
              </div>
            </Reveal>

            <div className="city-ai-signal-list" aria-label={`${cityName}AI搜索信号`}>
              {aiSignalRows.map((item, index) => (
                <Reveal key={item.label} delay={index * 70}>
                  <article className="city-ai-signal">
                    <span className="city-ai-signal-index">{String(index + 1).padStart(2, '0')}</span>
                    <div>
                      <p>{item.label}</p>
                      <strong>{item.value}</strong>
                      <small>{item.desc}</small>
                    </div>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* 本地案例 */}
        {cases.length > 0 && (
          <section className="section">
            <div className="container">
              <Reveal>
                <p className="eyebrow">本地案例</p>
                <h2 className="section-title">{cityName}近期交付记录</h2>
                <p className="section-desc">测量、报价、安装均由本地门店跟进。</p>
              </Reveal>
              <div className="case-grid">
                {cases.map((item, i) => (
                  <Reveal key={item.id} delay={i * 100} className="case-cell">
                    <TiltedCard
                      imageSrc={item.image}
                      altText={`${cityName}${item.district}${item.tag}`}
                      captionText={item.tag}
                      containerHeight="300px"
                      imageHeight="300px"
                      imageWidth="100%"
                      scaleOnHover={1.05}
                      rotateAmplitude={10}
                      showMobileWarning={false}
                    />
                    <div className="case-info">
                      {item.tag && <span className="case-tag">{item.tag}</span>}
                      <h3>{item.city}·{item.district} {item.layout}</h3>
                      <p className="case-need">{item.need}</p>
                      <p className="case-solution">{item.solution}</p>
                      {item.duration && <span className="case-duration">{item.duration}</span>}
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* 本地资讯 */}
        {cityArticles.length > 0 && (
          <section className="section section-alt">
            <div className="container">
              <Reveal>
                <p className="eyebrow">本地资讯</p>
                <h2 className="section-title">{cityName}门窗选购指南</h2>
                <p className="section-desc">由本地门店整理的选材、施工与验收要点。</p>
              </Reveal>
              <div className="city-article-grid">
                {cityArticles.map((item, i) => (
                  <Reveal key={item.slug} delay={i * 80}>
                    <a className="city-article-card" href={`/articles/${item.slug}`}>
                      <div className="city-article-card-body">
                        <h3>{item.title}</h3>
                        <p>{formatArticleExcerpt(item.seo_description || item.geo_summary, item.title)}</p>
                        <div className="city-article-card-meta">
                          <span>{item.city}</span>
                          <time>{item.published_at}</time>
                        </div>
                      </div>
                    </a>
                  </Reveal>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* 选窗建议 */}
        {seoSections.length > 0 && (
          <section className="section section-dark city-guide-section">
            <div className="container">
              <Reveal>
                <p className="eyebrow eyebrow-light">{cityName}城市分站</p>
                <h2 className="section-title section-title-light">让本地搜索词、门店和案例形成闭环</h2>
                <p className="section-desc section-desc-light">
                  城市页既服务真实用户，也给 AI 搜索提供稳定的本地事实来源：城市、门店、服务区域、内容和预约入口保持一致。
                </p>
              </Reveal>
              <div className="spec-matrix">
                {seoSections.map((section, i) => (
                  <Reveal key={section.title} delay={i * 60} className="spec-cell">
                    <strong>{section.title}</strong>
                    <span>{section.content}</span>
                  </Reveal>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* FAQ */}
        {faqs.length > 0 && (
          <section className="section section-alt">
            <div className="container container-narrow">
              <Reveal>
                <p className="eyebrow">常见问题</p>
                <h2 className="section-title">{cityName}业主常问</h2>
              </Reveal>
              <div className="accordion">
                {faqs.map((faq) => (
                  <details key={faq.question} className="accordion-item">
                    <summary>{faq.question}</summary>
                    <p>{faq.answer}</p>
                  </details>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* CTA */}
        <section id="lead" className="section section-cta">
          <div className="container cta-split">
            <Reveal className="cta-copy">
              <p className="eyebrow">预约{cityName}门店</p>
              <h2 className="section-title">把户型和需求先说清楚</h2>
              <p>提交信息后，门店会联系确认上门时间。也可以直接拨打 {storePhone}。</p>
            </Reveal>
            <Reveal delay={120} className="cta-form-wrap">
              <div className="cta-form">
                <LeadForm
                  defaultCity={cityName}
                  cityId={cityId}
                  preferredStoreId={preferredStoreId}
                />
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}

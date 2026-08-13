import type { Metadata } from 'next';
import BookingButton from '@/components/BookingButton';
import CityDetector from '@/components/CityDetector';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import HomeIntro from '@/components/HomeIntro';
import LeadForm from '@/components/LeadForm';
import { Reveal } from '@/components/react-bits';
import {
  AI_CITY_STATION_VALUES,
  AI_ENTITY_SIGNALS,
  AI_SEARCH_PAIN_POINTS,
  HERO,
  HOME_FAQS,
  NEED_ENTRIES,
  PROCESS_STEPS,
  PRODUCT_SPECS,
  SITE,
} from '@/lib/site';
import { Suspense } from 'react';

export const metadata: Metadata = {
  title: '系统门窗安装与旧窗改造 | 博雅敏格门窗',
  description: SITE.description,
  alternates: { canonical: '/' },
};

const SERVICE_IMAGES = [
  '/images/cases/balcony-window.webp',
  '/images/cases/large-window-room.webp',
  '/images/cases/old-window-room.webp',
];

export default function HomePage() {
  const [heroLead, heroFocus] = HERO.title.split('，');

  return (
    <>
      <HomeIntro brand={SITE.brand} />
      <Header variant="overlay" />
      <Suspense fallback={null}>
        <CityDetector />
      </Suspense>

      <main>
        <section className="velar-home-hero">
          <div className="velar-home-hero-image" aria-hidden="true" />
          <div className="velar-home-hero-shade" aria-hidden="true" />
          <div className="velar-home-hero-shell">
            <div className="velar-home-hero-top">
              <p className="velar-home-kicker">系统门窗 · 现场测量 · 专业安装</p>
              <p className="velar-home-subtitle">{HERO.subtitle}</p>
            </div>

            <h1 className="velar-home-title" aria-label={HERO.title}>
              <span>{heroLead}，</span>
              <strong>{heroFocus}</strong>
            </h1>

            <div className="velar-home-hero-bottom">
              <div className="hero-actions">
                <BookingButton label="预约免费测量" />
                <a className="btn btn-ghost" href={`tel:${SITE.hotline.replace(/-/g, '')}`}>
                  {SITE.hotlineDisplay}
                </a>
              </div>
              <aside className="velar-home-measure">
                <p>为什么先测量</p>
                <ol>
                  <li><span>01</span>记录洞口尺寸与现场条件</li>
                  <li><span>02</span>确认型材、玻璃与五金配置</li>
                  <li><span>03</span>给出工期与报价，避免后期增项</li>
                </ol>
              </aside>
            </div>

            <a className="velar-home-scroll" href="#ai-visibility">
              <span />
              向下了解
            </a>
          </div>
        </section>

        {/* AI 搜索可见性 */}
        <section className="home-story-section" id="ai-visibility">
          <div className="home-story-wordmark" aria-hidden="true">
            博雅敏格 · 博雅敏格 · 博雅敏格
          </div>
          <div className="container home-story-inner">
            <Reveal className="home-story-copy">
              <p className="eyebrow eyebrow-light">AI 搜索可见性</p>
              <h2>客户都在问 AI，先让 AI 读懂本地门窗品牌</h2>
              <p>
                城市分站把品牌身份、门店地址、服务区域、本地案例、FAQ 和预约入口统一沉淀，用户搜索本地门窗需求时，页面有更完整的证据链可以被搜索引擎和 AI 摘要读取。
              </p>
            </Reveal>

            <div className="home-story-pains">
              {AI_SEARCH_PAIN_POINTS.map((item, index) => (
                <Reveal key={item.pain} delay={index * 0.06}>
                  <article className="home-story-pain">
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <div>
                      <h3>{item.pain}</h3>
                      <p>{item.detail}</p>
                    </div>
                  </article>
                </Reveal>
              ))}
            </div>

            <div className="home-story-signals" aria-label="AI 可引用实体信号">
              {AI_ENTITY_SIGNALS.map((signal) => (
                <span key={signal}>{signal}</span>
              ))}
            </div>

            <div className="home-story-values" aria-label="城市分站价值">
              {AI_CITY_STATION_VALUES.map((item, index) => (
                <Reveal key={item.title} delay={index * 0.06}>
                  <article>
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <strong>{item.title}</strong>
                    <p>{item.desc}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* 服务 */}
        <section className="home-service-section" id="services">
          <div className="container">
            <Reveal>
              <div className="home-section-heading">
                <div>
                  <p className="eyebrow">按需求选择</p>
                  <h2>你可能需要的门窗服务</h2>
                </div>
                <p>先按实际问题选方向，测量后再确认型材、玻璃、五金和工期。</p>
              </div>
            </Reveal>
            <div className="home-service-gallery">
              {NEED_ENTRIES.map((item, i) => (
                <article
                  className="home-service-card"
                  key={item.id}
                  tabIndex={0}
                  style={{ backgroundImage: `url(${SERVICE_IMAGES[i % SERVICE_IMAGES.length]})` }}
                >
                  <div className="home-service-card-shade" />
                  <div className="home-service-card-copy">
                    <span>0{i + 1}</span>
                    <h3>{item.name}</h3>
                    <p>{item.pain}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* 流程 */}
        <section className="section home-process-section" id="process">
          <div className="container">
            <Reveal>
              <div className="home-section-heading">
                <div>
                  <p className="eyebrow">服务流程</p>
                  <h2>从咨询到验收，五步走完</h2>
                </div>
                <p>每一步都有明确交付，方案、报价、施工和验收都以现场条件为准。</p>
              </div>
            </Reveal>
            <div className="home-process-track">
              {PROCESS_STEPS.map((step, i) => (
                <Reveal key={step.step} delay={i * 0.07} className="home-process-node">
                  <span>{step.step}</span>
                  <h3>{step.title}</h3>
                  <p>{step.desc}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* 配置（深色） */}
        <section className="section section-dark home-spec-section" id="specs">
          <div className="container">
            <Reveal>
              <div className="home-section-heading home-section-heading--light">
                <div>
                  <p className="eyebrow eyebrow-light">配置怎么定</p>
                  <h2>门窗不是只看单价，关键看现场条件</h2>
                </div>
                <p>同样是封阳台，楼层、朝向、物业要求、玻璃厚度和开启方式都会影响方案。测量时会把这些条件逐项确认，避免后期返工。</p>
              </div>
            </Reveal>
            <div className="home-spec-grid">
              {PRODUCT_SPECS.map((item, i) => (
                <Reveal key={item.name} delay={i * 0.06} className="home-spec-card">
                  <span>0{i + 1}</span>
                  <strong>{item.name}</strong>
                  <p>{item.desc}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="section home-faq-section" id="faq">
          <div className="container container-narrow">
            <Reveal>
              <p className="eyebrow">常见问题</p>
              <h2 className="section-title">装修前先问清楚</h2>
            </Reveal>
            <div className="accordion">
              {HOME_FAQS.map((item) => (
                <details key={item.question} className="accordion-item">
                  <summary>{item.question}</summary>
                  <p>{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section section-cta home-lead-section" id="lead">
          <div className="container cta-split">
            <Reveal className="cta-copy">
              <p className="eyebrow">预约测量</p>
              <h2 className="section-title">先把现场情况说清楚，再安排门店上门</h2>
              <p>填写信息后，工作人员会电话确认城市、户型、楼层和主要需求。</p>
            </Reveal>
            <Reveal delay={0.12} className="cta-form-wrap">
              <div className="cta-form">
                <LeadForm />
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}

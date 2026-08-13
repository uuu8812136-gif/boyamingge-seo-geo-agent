import type { Metadata } from 'next';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import { SITE } from '@/lib/site';

export const metadata: Metadata = {
  title: '关于我们 - 博雅敏格门窗',
  description: `${SITE.brandFull}专注于系统门窗、防盗门、阳台封窗与旧窗改造服务。`,
  alternates: { canonical: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost'}/about` },
};

export default function AboutPage() {
  const services = [
    {
      title: '阳台封窗',
      desc: '断桥铝推拉或平开窗，重点确认抗风压、排水与密封。',
    },
    {
      title: '卧室隔音窗',
      desc: '中空钢化、三玻两腔方案，针对临街与高架噪音场景。',
    },
    {
      title: '旧窗改造',
      desc: '保留原洞口整窗更换，改善漏风、结露与密封老化。',
    },
    {
      title: '防盗门安装',
      desc: '甲级防盗门测量定制，包含拆旧、安装与现场调试。',
    },
    {
      title: '断桥铝门窗',
      desc: '按楼层、朝向和洞口尺寸确认型材壁厚与玻璃配置。',
    },
    {
      title: '全屋门窗定制',
      desc: '新房装修或二次翻新，统一测量、统一交付与验收。',
    },
  ];

  const process = [
    ['01', '预约咨询', '电话或在线留资，说明城市、户型与主要需求。'],
    ['02', '上门测量', '工程师上门记录洞口尺寸与现场条件。'],
    ['03', '方案报价', '确认型材、玻璃、五金配置与工期，价格以实测为准。'],
    ['04', '安装施工', '按约定时间进场，完成拆旧、安装、打胶和调试。'],
    ['05', '售后质保', '验收后登记质保，使用中问题可联系 400 或门店。'],
  ];

  return (
    <>
      <Header />
      <main className="editorial-page page-with-solid-header">
        <section className="inner-page-hero inner-page-hero--about">
          <div className="container inner-page-hero-grid">
            <div className="inner-page-hero-copy">
              <p className="eyebrow eyebrow-light">关于我们</p>
              <h1>{SITE.brandFull}：<br />本地门窗服务品牌</h1>
              <p>
                专注系统门窗安装与旧窗改造，以现场测量、专业施工和售后跟进为核心。
              </p>
            </div>
            <aside className="inner-page-proof-card">
              <span>服务原则</span>
              <strong>先看现场，再定方案</strong>
              <p>洞口、楼层、朝向和使用需求都会影响配置，测量清楚再报价。</p>
            </aside>
          </div>
        </section>

        <section className="section editorial-intro-section">
          <div className="container editorial-intro-grid">
            <div>
              <p className="eyebrow">品牌简介</p>
              <h2>把复杂配置讲清楚，把安装过程做扎实</h2>
            </div>
            <p className="editorial-lead">
              {SITE.brandFull}提供防盗门、断桥铝、阳台封窗、隔音窗与旧窗改造服务，
              采用现场测量、方案确认、专业施工和售后跟进的服务流程。
            </p>
          </div>
        </section>

        <section className="section about-service-section">
          <div className="container">
            <div className="editorial-section-head">
              <div>
                <p className="eyebrow">服务范围</p>
                <h2>按实际问题选择服务</h2>
              </div>
              <p>配置与价格以现场测量后的正式方案为准。</p>
            </div>
            <div className="about-service-grid">
              {services.map((service, index) => (
                <article className="about-service-card" key={service.title}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <h3>{service.title}</h3>
                  <p>{service.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section about-process-section">
          <div className="container">
            <div className="editorial-section-head">
              <div>
                <p className="eyebrow">服务流程</p>
                <h2>五步完成，从咨询到质保</h2>
              </div>
              <p>每一步都有清晰交付，避免方案、报价与施工信息脱节。</p>
            </div>
            <ol className="about-process-grid">
              {process.map(([step, title, desc]) => (
                <li className="about-process-card" key={step}>
                  <span>{step}</span>
                  <h3>{title}</h3>
                  <p>{desc}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section about-contact-section">
          <div className="container">
            <div className="about-contact-card">
              <div>
                <p className="eyebrow eyebrow-light">联系我们</p>
                <h2>先说清现场情况，再安排就近门店上门</h2>
              </div>
              <div className="about-contact-actions">
                <a className="btn btn-primary" href={`tel:${SITE.hotline.replace(/-/g, '')}`}>
                  {SITE.hotlineDisplay}
                </a>
                <a className="btn btn-ghost" href="/stores">查看门店分布</a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

import type { Metadata } from 'next';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import LeadForm from '@/components/LeadForm';
import { SITE } from '@/lib/site';

export const metadata: Metadata = {
  title: '联系我们 - 博雅敏格门窗',
  description: `联系${SITE.brandFull}，全国服务热线 ${SITE.hotlineDisplay}，或在线提交测量预约。`,
  alternates: { canonical: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost'}/contact` },
};

export default function ContactPage() {
  return (
    <>
      <Header />
      <main className="contact-page page-with-solid-header">
        <section className="inner-page-hero inner-page-hero--contact">
          <div className="container inner-page-hero-grid">
            <div className="inner-page-hero-copy">
              <p className="eyebrow eyebrow-light">联系我们</p>
              <h1>电话或在线<br />预约测量</h1>
              <p>工作人员将联系您确认城市、户型、现场条件与测量时间。</p>
            </div>
            <a className="contact-phone-card" href={`tel:${SITE.hotline.replace(/-/g, '')}`}>
              <span>全国服务热线</span>
              <strong>{SITE.hotlineDisplay}</strong>
              <small>点击直接拨打</small>
            </a>
          </div>
        </section>

        <section className="section contact-main-section">
          <div className="container contact-main-grid">
            <aside className="contact-channel-list">
              <div className="editorial-section-head editorial-section-head--stacked">
                <div>
                  <p className="eyebrow">联系方式</p>
                  <h2>选择适合你的咨询方式</h2>
                </div>
                <p>正式方案与价格以现场测量结果为准。</p>
              </div>
              <a className="contact-channel-card" href={`tel:${SITE.hotline.replace(/-/g, '')}`}>
                <span>01</span>
                <div><strong>电话咨询</strong><small>{SITE.hotlineDisplay}</small></div>
                <b>立即拨打 →</b>
              </a>
              <a className="contact-channel-card" href="/stores">
                <span>02</span>
                <div><strong>门店分布</strong><small>查询已开通的真实门店</small></div>
                <b>查看门店 →</b>
              </a>
              <a className="contact-channel-card" href="/articles">
                <span>03</span>
                <div><strong>选购指南</strong><small>装修前先了解配置与避坑</small></div>
                <b>阅读指南 →</b>
              </a>
            </aside>

            <div className="contact-form-card">
              <div className="contact-form-head">
                <p className="eyebrow">预约测量</p>
                <h2>留下基本信息</h2>
                <p>客服将联系您确认服务范围与测量时间。</p>
              </div>
              <LeadForm />
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

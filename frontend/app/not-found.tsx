import type { Metadata } from 'next';
import Footer from '@/components/Footer';
import Header from '@/components/Header';

export const metadata: Metadata = {
  title: '页面不存在',
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <>
      <Header />
      <main className="container container-narrow page-with-solid-header" style={{ padding: '80px 24px 120px', textAlign: 'center' }}>
        <h1>页面不存在</h1>
        <p>您访问的页面未找到，请返回首页或选择城市分站。</p>
        <p style={{ marginTop: 24 }}>
          <a href="/" className="btn btn-primary">返回首页</a>
          <a href="/stores" className="btn btn-outline" style={{ marginLeft: 12 }}>查看门店</a>
        </p>
      </main>
      <Footer />
    </>
  );
}

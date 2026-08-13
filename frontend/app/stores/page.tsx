import type { Metadata } from 'next';
import Footer from '@/components/Footer';
import Header from '@/components/Header';
import StoresExplorer from '@/components/StoresExplorer';
import { getServerApiBase } from '@/lib/site';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: '门店分布 - 博雅敏格门窗',
  description: '查看博雅敏格门窗已开通的线下门店与服务信息。',
  alternates: { canonical: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost'}/stores` },
};

async function fetchAllCities() {
  const base = getServerApiBase();
  try {
    const res = await fetch(`${base}/api/v1/cities?active_only=true`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchAllStores() {
  const base = getServerApiBase();
  try {
    const res = await fetch(`${base}/api/v1/cities/stores/all`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function StoresPage() {
  const [apiStores, apiCities] = await Promise.all([fetchAllStores(), fetchAllCities()]);
  const apiStoreItems = apiStores?.items || [];

  const cityNameToSlug = new Map<string, string>();
  for (const c of apiCities?.items || []) {
    cityNameToSlug.set(c.name, c.slug);
  }
  const getCitySlug = (name: string) => cityNameToSlug.get(name) || '';

  let groups: Array<{ cityName: string; citySlug: string; stores: any[] }>;

  if (apiStoreItems.length > 0) {
    const grouped = apiStoreItems.reduce((acc: Record<string, any[]>, store: any) => {
      const cityKey = store.city;
      if (!acc[cityKey]) acc[cityKey] = [];
      acc[cityKey].push({
        id: store.id,
        store_name: store.store_name,
        city: store.city,
        district: store.district || '',
        address: store.address,
        phone: store.phone,
        opening_hours: store.opening_hours,
        services: store.services || [],
      });
      return acc;
    }, {} as Record<string, any[]>);

    groups = (Object.entries(grouped) as [string, any[]][]).map(([cityName, stores]) => ({
      cityName,
      citySlug: getCitySlug(cityName),
      stores,
    }));
  } else {
    groups = [];
  }

  return (
    <>
      <Header />
      <main className="directory-page page-with-solid-header">
        <section className="inner-page-hero directory-hero">
          <div className="container directory-hero-inner">
            <div>
              <p className="eyebrow eyebrow-light">门店分布</p>
              <h1>选择就近门店</h1>
            </div>
            <p>这里只展示后台已发布的真实门店信息，可按城市、门店名或地址搜索。</p>
          </div>
        </section>
        <section className="section directory-list-section">
          <div className="container">
            <h1 style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>博雅敏格门窗门店分布</h1>
            <StoresExplorer groups={groups} />
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

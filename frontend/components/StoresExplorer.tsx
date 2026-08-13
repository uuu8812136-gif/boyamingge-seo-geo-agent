'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';

type StoreItem = {
  id: number;
  store_name: string;
  city: string;
  district: string;
  address: string;
  phone: string;
  opening_hours: string | null;
  services: string[];
};

type CityGroup = {
  cityName: string;
  citySlug: string;
  stores: StoreItem[];
};

interface Props {
  groups: CityGroup[];
}

const PAGE_SIZE = 6;

export default function StoresExplorer({ groups }: Props) {
  const [query, setQuery] = useState('');
  const [expandedCities, setExpandedCities] = useState<Set<string>>(() => {
    return new Set(groups.length > 0 ? [groups[0].cityName] : []);
  });
  const [visibleCounts, setVisibleCounts] = useState<Record<string, number>>({});

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((g) => {
        const matchedStores = g.stores.filter(
          (s) =>
            s.store_name.toLowerCase().includes(q) ||
            s.address.toLowerCase().includes(q) ||
            (s.district || '').toLowerCase().includes(q) ||
            (s.services || []).some((sv) => sv.toLowerCase().includes(q))
        );
        if (g.cityName.toLowerCase().includes(q)) return g;
        if (matchedStores.length > 0) return { ...g, stores: matchedStores };
        return null;
      })
      .filter(Boolean) as CityGroup[];
  }, [query, groups]);

  const toggleCity = (cityName: string) => {
    setExpandedCities((prev) => {
      const next = new Set(prev);
      if (next.has(cityName)) next.delete(cityName);
      else next.add(cityName);
      return next;
    });
  };

  const getVisibleCount = (cityName: string, total: number) =>
    visibleCounts[cityName] ?? Math.min(PAGE_SIZE, total);

  const loadMore = (cityName: string, total: number) => {
    setVisibleCounts((prev) => ({
      ...prev,
      [cityName]: Math.min((prev[cityName] ?? PAGE_SIZE) + PAGE_SIZE, total),
    }));
  };

  if (groups.length === 0) {
    return (
      <div className="empty-state empty-state--spacious">
        暂无门店数据，请稍后重试或拨打 400-888-6688 咨询。
      </div>
    );
  }

  return (
    <div>
      {/* 搜索框 */}
      <div className="store-search-wrap">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索城市、门店名或地址..."
          aria-label="搜索门店"
          className="store-search-input"
        />
        <svg className="store-search-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.6" />
          <path d="M14 14L18 18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </div>

      {query.trim() && (
        <p className="store-search-result">
          找到 {filtered.length} 个城市的门店
        </p>
      )}

      <div className="city-store-groups">
        {filtered.map((group) => {
          const isExpanded = expandedCities.has(group.cityName);
          const visibleCount = getVisibleCount(group.cityName, group.stores.length);
          const visibleStores = group.stores.slice(0, visibleCount);
          const hasMore = visibleCount < group.stores.length;

          return (
            <div key={group.cityName} className="city-store-group">
              <div className="city-store-header">
                <button
                  onClick={() => toggleCity(group.cityName)}
                  aria-expanded={isExpanded}
                  aria-label={isExpanded ? `收起${group.cityName}门店` : `展开${group.cityName}门店`}
                  className="city-store-toggle"
                >
                  <h2>{group.cityName}</h2>
                  <span>{group.stores.length} 家门店</span>
                  <svg className="city-store-chevron" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                    <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {group.citySlug && (
                  <Link href={`/${group.citySlug}`} className="link-arrow city-store-page-link">
                    城市页 →
                  </Link>
                )}
              </div>

              {isExpanded && (
                <div>
                  {visibleStores.map((store) => (
                    <div key={store.id} className="store-detail-card">
                      <div className="store-detail-info">
                        <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 12px' }}>{store.store_name}</h3>
                        <div className="store-detail-row"><strong>地址</strong><span>{store.address}</span></div>
                        {store.opening_hours && <div className="store-detail-row"><strong>营业时间</strong><span>{store.opening_hours}</span></div>}
                        <div className="store-detail-row"><strong>服务热线</strong><a href={`tel:${store.phone.replace(/-/g, '')}`}>{store.phone}</a></div>
                        {store.services && store.services.length > 0 && (
                          <div className="store-detail-row"><strong>服务范围</strong><div className="chip-list">{store.services.map((s) => <span key={s} className="chip chip-sm">{s}</span>)}</div></div>
                        )}
                      </div>
                      <div className="store-detail-actions">
                        <a href={group.citySlug ? `/${group.citySlug}#lead` : '/stores#lead'} className="btn btn-primary btn-sm">预约测量</a>
                        <a href={`tel:${store.phone.replace(/-/g, '')}`} className="btn btn-outline btn-sm">拨打电话</a>
                      </div>
                    </div>
                  ))}
                  {hasMore && (
                    <button onClick={() => loadMore(group.cityName, group.stores.length)} className="btn btn-outline btn-sm" style={{ display: 'block', margin: '16px auto 0' }}>
                      加载更多（剩余 {group.stores.length - visibleCount} 家）
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="empty-state empty-state--spacious">
            未找到匹配的门店，请尝试其他关键词或拨打 400-888-6688 咨询。
          </div>
        )}
      </div>
    </div>
  );
}

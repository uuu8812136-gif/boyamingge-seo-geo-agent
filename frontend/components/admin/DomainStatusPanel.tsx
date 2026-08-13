'use client';

import { useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';

type CityDomain = {
  id: number;
  name: string;
  slug: string;
  subdomain: string | null;
  custom_domain: string | null;
  canonical_url: string | null;
  content_status: string;
  seo_indexable: boolean;
  is_active: boolean;
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
};

/** 域名/二级域名状态面板：展示所有城市的子域名与 canonical 状态。 */
export default function DomainStatusPanel({ token, showNotice }: Props) {
  const [cities, setCities] = useState<CityDomain[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    adminFetch<{ items: CityDomain[]; total: number }>(`/api/v1/admin/cities`, token)
      .then((data) => {
        if (alive) setCities(data.items || []);
      })
      .catch((e) => {
        if (alive) showNotice(e instanceof Error ? e.message : '加载失败', 'error');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [token, showNotice]);

  const rootDomain = process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com';

  return (
    <div className="admin-panel-main">
      <div className="admin-form">
        <h3 className="admin-form-title">二级域名状态总览</h3>
        <p className="admin-help">
          根域名：<strong>{rootDomain}</strong>。城市二级域名格式：
          <code>https://{'{subdomain}'}.{rootDomain}/</code>
        </p>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>城市</th>
                <th>slug</th>
                <th>子域名</th>
                <th>访问地址</th>
                <th>canonical_url</th>
                <th>自定义域名</th>
                <th>状态</th>
                <th>可索引</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="admin-empty">加载中…</td>
                </tr>
              ) : cities.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">暂无城市</td>
                </tr>
              ) : (
                cities.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.slug}</td>
                    <td>{c.subdomain || <span className="admin-tag admin-tag-warn">未配置</span>}</td>
                    <td>
                      {c.subdomain ? (
                        <a href={`https://${c.subdomain}.${rootDomain}/`} target="_blank" rel="noreferrer">
                          {c.subdomain}.{rootDomain}
                        </a>
                      ) : (
                        <span className="admin-muted">—</span>
                      )}
                    </td>
                    <td className="admin-mono">{c.canonical_url || '—'}</td>
                    <td className="admin-mono">{c.custom_domain || '—'}</td>
                    <td>
                      <span className={`admin-tag ${c.content_status === 'published' ? 'admin-tag-primary' : 'admin-tag-warn'}`}>
                        {c.content_status}
                      </span>
                      {!c.is_active && <span className="admin-tag admin-tag-disabled">未启用</span>}
                    </td>
                    <td>{c.seo_indexable ? '是' : '否'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

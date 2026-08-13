'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';
import AdminCitySelector from './AdminCitySelector';

type CityRow = {
  id: number;
  name: string;
  slug: string;
  province: string;
  is_active: boolean;
  has_store: boolean;
  subdomain: string | null;
  content_status: string;
  seo_indexable: boolean;
  stores_count: number;
  canonical_url: string | null;
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
  role?: string;
};

/** 城市站管理：列表 + 发布/下架 + 编辑基础字段。 */
export default function CityManagerPanel({ token, showNotice, role }: Props) {
  const rootDomain = process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'boyamingge.com';
  const [cities, setCities] = useState<CityRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editing, setEditing] = useState<CityRow | null>(null);
  const [form, setForm] = useState<Partial<CityRow>>({});
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetch<{ items: CityRow[]; total: number }>(`/api/v1/admin/cities`, token);
      setCities(data.items || []);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [token, showNotice]);

  useEffect(() => {
    load();
  }, [load]);

  const startEdit = (row: CityRow) => {
    setEditing(row);
    setForm({ name: row.name, subdomain: row.subdomain, is_active: row.is_active, has_store: row.has_store });
    setSelectedId(row.id);
    setShowCreate(false);
  };

  const save = async () => {
    if (!editing && !showCreate) return;
    try {
      const path = showCreate ? '/api/v1/admin/cities' : `/api/v1/admin/cities/${editing!.id}`;
      await adminFetch(path, token, {
        method: showCreate ? 'POST' : 'PATCH',
        body: JSON.stringify(form),
      });
      showNotice(showCreate ? '城市已创建' : '城市已更新', 'success');
      setEditing(null);
      setShowCreate(false);
      setForm({});
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '保存失败', 'error');
    }
  };

  const publish = async (row: CityRow) => {
    try {
      await adminFetch(`/api/v1/admin/cities/${row.id}/publish`, token, { method: 'POST' });
      showNotice(`${row.name} 已发布`, 'success');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '发布失败', 'error');
    }
  };

  const unpublish = async (row: CityRow) => {
    try {
      await adminFetch(`/api/v1/admin/cities/${row.id}/unpublish`, token, { method: 'POST' });
      showNotice(`${row.name} 已下架`, 'success');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '下架失败', 'error');
    }
  };

  return (
    <div className="admin-panel-grid">
      <aside className="admin-panel-actions">
        {role !== 'city_manager' && (
          <button type="button" className="btn btn-primary btn-block" onClick={() => {
            setShowCreate(true);
            setEditing(null);
            setSelectedId(null);
            setForm({ is_active: true, has_store: false, content_status: 'draft' });
          }}>新建城市</button>
        )}
        <button type="button" className="btn btn-primary btn-block" onClick={load} disabled={loading}>
          {loading ? '刷新中…' : '刷新城市列表'}
        </button>
        {cities.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`admin-list-item ${selectedId === c.id ? 'is-active' : ''}`}
            onClick={() => startEdit(c)}
          >
            <span className="admin-list-name">{c.name}</span>
            <span className="admin-list-meta">
              {c.subdomain ? `${c.subdomain}.${rootDomain}` : '无子域名'} · {c.content_status}
            </span>
          </button>
        ))}
      </aside>

      <section className="admin-panel-main">
        {(editing || showCreate) ? (
          <div className="admin-form">
            <h3 className="admin-form-title">{showCreate ? '新建城市' : `编辑城市 - ${editing?.name}`}</h3>
            <div className="admin-field">
              <label className="admin-field-label">城市名</label>
              <input
                className="admin-input"
                value={form.name ?? ''}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            {showCreate && <>
              <div className="admin-field">
                <label className="admin-field-label">英文 slug</label>
                <input className="admin-input" value={form.slug ?? ''} placeholder="如 foshan" onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase() })} />
              </div>
              <div className="admin-field">
                <label className="admin-field-label">省份</label>
                <input className="admin-input" value={form.province ?? ''} onChange={(e) => setForm({ ...form, province: e.target.value })} />
              </div>
            </>}
            <div className="admin-field">
              <label className="admin-field-label">子域名（subdomain）</label>
              <input
                className="admin-input"
                value={form.subdomain ?? ''}
                placeholder="如 guangzhou"
                onChange={(e) => setForm({ ...form, subdomain: e.target.value || null })}
              />
              <small>访问 https://子域名.{rootDomain}/</small>
            </div>
            <div className="admin-field-row">
              <label>
                <input
                  type="checkbox"
                  checked={form.is_active ?? false}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                启用城市
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={form.has_store ?? false}
                  onChange={(e) => setForm({ ...form, has_store: e.target.checked })}
                />
                已有门店
              </label>
            </div>
            <div className="admin-form-actions">
              <button type="button" className="btn btn-primary" onClick={save}>保存</button>
              {!showCreate && editing?.content_status === 'published' ? (
                <button type="button" className="btn btn-outline" onClick={() => unpublish(editing)}>下架</button>
              ) : !showCreate && editing ? (
                <button type="button" className="btn btn-outline" onClick={() => publish(editing)}>发布</button>
              ) : null}
              <button type="button" className="btn btn-outline" onClick={() => { setEditing(null); setShowCreate(false); setForm({}); }}>取消</button>
            </div>
            {!showCreate && <div className="admin-field">
              <label className="admin-field-label">canonical_url</label>
              <input className="admin-input" value={editing?.canonical_url || ''} readOnly />
            </div>}
          </div>
        ) : (
          <div className="admin-empty">从左侧选择城市进行编辑，或点击刷新加载列表。</div>
        )}
      </section>
    </div>
  );
}

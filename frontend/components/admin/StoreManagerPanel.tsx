'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';
import AdminCitySelector from './AdminCitySelector';

type StoreRow = {
  id: number;
  city_id: number;
  store_name: string;
  province: string;
  city: string;
  district: string;
  address: string;
  phone: string;
  is_active: boolean;
  is_primary: boolean;
  store_code: string | null;
  status: string;
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
  role?: string;
};

/** 门店管理：按城市列出 + 新建/编辑 + 设主门店。 */
export default function StoreManagerPanel({ token, showNotice, role }: Props) {
  const [cityId, setCityId] = useState<number | null>(null);
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<StoreRow | null>(null);
  const [form, setForm] = useState<Partial<StoreRow>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [selectedCity, setSelectedCity] = useState<{ name: string; province: string } | null>(null);

  const load = useCallback(async () => {
    if (!cityId) return;
    setLoading(true);
    try {
      const data = await adminFetch<{ items: StoreRow[]; total: number }>(
        `/api/v1/admin/stores?city_id=${cityId}`,
        token,
      );
      setStores(data.items || []);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [cityId, token, showNotice]);

  useEffect(() => {
    if (cityId) {
      load();
      adminFetch<{ name: string; province: string }>(`/api/v1/admin/cities/${cityId}`, token)
        .then(setSelectedCity)
        .catch(() => setSelectedCity(null));
    } else {
      setStores([]);
      setSelectedCity(null);
    }
  }, [cityId, load, token]);

  const startEdit = (row: StoreRow) => {
    setEditing(row);
    setForm({
      store_name: row.store_name,
      address: row.address,
      district: row.district,
      phone: row.phone,
      is_active: row.is_active,
      status: row.status,
    });
    setShowCreate(false);
  };

  const save = async () => {
    if (!editing) return;
    if (!form.store_name?.trim() || !form.district?.trim() || !form.address?.trim() || !form.phone?.trim()) {
      showNotice('请完整填写门店名称、区县、地址和电话', 'error');
      return;
    }
    try {
      await adminFetch(`/api/v1/admin/stores/${editing.id}`, token, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      showNotice('门店已更新', 'success');
      setEditing(null);
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '保存失败', 'error');
    }
  };

  const setPrimary = async (row: StoreRow) => {
    try {
      await adminFetch(`/api/v1/admin/stores/${row.id}/set-primary`, token, { method: 'POST' });
      showNotice(`${row.store_name} 已设为主门店`, 'success');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '设置失败', 'error');
    }
  };

  const createStore = async () => {
    if (!cityId) {
      showNotice('请先选择城市', 'error');
      return;
    }
    if (!selectedCity) {
      showNotice('城市详情加载失败，请重新选择城市', 'error');
      return;
    }
    if (!form.store_name?.trim() || !form.district?.trim() || !form.address?.trim() || !form.phone?.trim()) {
      showNotice('请完整填写门店名称、区县、地址和电话', 'error');
      return;
    }
    try {
      await adminFetch(`/api/v1/admin/stores`, token, {
        method: 'POST',
        body: JSON.stringify({
          city_id: cityId,
          store_name: form.store_name,
          province: selectedCity.province,
          city: selectedCity.name,
          district: form.district,
          address: form.address,
          phone: form.phone,
        }),
      });
      showNotice('门店已创建', 'success');
      setShowCreate(false);
      setForm({});
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '创建失败', 'error');
    }
  };

  return (
    <div className="admin-panel-grid">
      <aside className="admin-panel-actions">
        <AdminCitySelector token={token} value={cityId} onChange={setCityId} />
        {role !== 'store_manager' && (
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={() => {
              setShowCreate(true);
              setEditing(null);
              setForm({});
            }}
            disabled={!cityId}
          >
            新建门店
          </button>
        )}
        <button
          type="button"
          className="btn btn-outline btn-block"
          onClick={load}
          disabled={loading || !cityId}
        >
          {loading ? '刷新中…' : '刷新门店'}
        </button>
        {stores.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`admin-list-item ${editing?.id === s.id ? 'is-active' : ''}`}
            onClick={() => startEdit(s)}
          >
            <span className="admin-list-name">
              {s.store_name}
              {s.is_primary && <span className="admin-tag admin-tag-primary">主</span>}
            </span>
            <span className="admin-list-meta">{s.district} · {s.status}</span>
          </button>
        ))}
      </aside>

      <section className="admin-panel-main">
        {(editing || showCreate) && (
          <div className="admin-form">
            <h3 className="admin-form-title">{showCreate ? '新建门店' : `编辑 - ${editing?.store_name}`}</h3>
            <div className="admin-field">
              <label className="admin-field-label">门店名称</label>
              <input
                className="admin-input"
                value={form.store_name ?? ''}
                onChange={(e) => setForm({ ...form, store_name: e.target.value })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">区县</label>
              <input
                className="admin-input"
                value={form.district ?? ''}
                onChange={(e) => setForm({ ...form, district: e.target.value })}
                placeholder="如：天河区"
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">地址</label>
              <input
                className="admin-input"
                value={form.address ?? ''}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">电话</label>
              <input
                className="admin-input"
                value={form.phone ?? ''}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            {!showCreate && role !== 'store_manager' && (
              <div className="admin-field-row">
                <label>
                  <input
                    type="checkbox"
                    checked={form.is_active ?? false}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  启用
                </label>
              </div>
            )}
            <div className="admin-form-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={showCreate ? createStore : save}
              >
                {showCreate ? '创建' : '保存'}
              </button>
              {!showCreate && editing && !editing.is_primary && role !== 'store_manager' && (
                <button type="button" className="btn btn-outline" onClick={() => setPrimary(editing)}>
                  设为主门店
                </button>
              )}
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  setEditing(null);
                  setShowCreate(false);
                }}
              >
                取消
              </button>
            </div>
          </div>
        )}
        {!editing && !showCreate && (
          <div className="admin-empty">{cityId ? '从左侧选择门店，或点击新建。' : '请先选择城市。'}</div>
        )}
      </section>
    </div>
  );
}

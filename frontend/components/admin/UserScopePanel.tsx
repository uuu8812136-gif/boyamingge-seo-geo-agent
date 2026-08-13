'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';

type UserRow = {
  id: number;
  username: string;
  role: string;
  dealer_code: string | null;
  city_id: number | null;
  store_id: number | null;
  is_active: boolean;
  last_login_at: string | null;
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
};

const ROLE_OPTIONS = [
  { value: 'admin', label: 'admin（超级管理员）' },
  { value: 'operator', label: 'operator（运营）' },
  { value: 'city_manager', label: 'city_manager（城市管理员）' },
  { value: 'store_manager', label: 'store_manager（门店管理员）' },
];

/** 权限账号：用户列表 + 新建 + 编辑 role/city_id/store_id。 */
export default function UserScopePanel({ token, showNotice }: Props) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [form, setForm] = useState<Partial<UserRow> & { password?: string }>({});
  const [showCreate, setShowCreate] = useState(false);
  const selectedRole = form.role || 'operator';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetch<{ items: UserRow[]; total: number }>(`/api/v1/admin/users`, token);
      setUsers(data.items || []);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [token, showNotice]);

  useEffect(() => {
    load();
  }, [load]);

  const startEdit = (row: UserRow) => {
    setEditing(row);
    setForm({
      role: row.role,
      city_id: row.city_id,
      store_id: row.store_id,
      is_active: row.is_active,
      dealer_code: row.dealer_code,
    });
    setShowCreate(false);
  };

  const save = async () => {
    if (!editing) return;
    try {
      await adminFetch(`/api/v1/admin/users/${editing.id}`, token, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      showNotice('用户已更新', 'success');
      setEditing(null);
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '保存失败', 'error');
    }
  };

  const createUser = async () => {
    const username = form.username?.trim();
    const password = form.password || '';
    if (!username || password.length < 12) {
      showNotice('请填写用户名和至少 12 位密码', 'error');
      return;
    }
    try {
      await adminFetch(`/api/v1/admin/users`, token, {
        method: 'POST',
        body: JSON.stringify({
          username,
          password,
          role: selectedRole,
          dealer_code: selectedRole === 'dealer' ? form.dealer_code : null,
          city_id: selectedRole === 'city_manager' ? form.city_id : null,
          store_id: selectedRole === 'store_manager' ? form.store_id : null,
          is_active: form.is_active ?? true,
        }),
      });
      showNotice('用户已创建', 'success');
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
        <button
          type="button"
          className="btn btn-primary btn-block"
          onClick={() => {
            setShowCreate(true);
            setEditing(null);
            setForm({ role: 'operator', is_active: true });
          }}
        >
          新建用户
        </button>
        <button type="button" className="btn btn-outline btn-block" onClick={load} disabled={loading}>
          {loading ? '刷新中…' : '刷新用户'}
        </button>
        {users.map((u) => (
          <button
            key={u.id}
            type="button"
            className={`admin-list-item ${editing?.id === u.id ? 'is-active' : ''}`}
            onClick={() => startEdit(u)}
          >
            <span className="admin-list-name">
              {u.username}
              {!u.is_active && <span className="admin-tag admin-tag-disabled">禁用</span>}
            </span>
            <span className="admin-list-meta">{u.role}</span>
          </button>
        ))}
      </aside>

      <section className="admin-panel-main">
        {(editing || showCreate) && (
          <div className="admin-form">
            <h3 className="admin-form-title">{showCreate ? '新建用户' : `编辑 - ${editing?.username}`}</h3>
            {showCreate && (
              <>
                <div className="admin-field">
                  <label className="admin-field-label" htmlFor="admin-new-username">用户名</label>
                  <input
                    id="admin-new-username"
                    className="admin-input"
                    value={form.username ?? ''}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                  />
                </div>
                <div className="admin-field">
                  <label className="admin-field-label" htmlFor="admin-new-password">密码</label>
                  <input
                    id="admin-new-password"
                    className="admin-input"
                    type="password"
                    minLength={12}
                    maxLength={128}
                    value={form.password ?? ''}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="12–128 位，至少三类字符"
                  />
                </div>
              </>
            )}
            <div className="admin-field">
              <label className="admin-field-label" htmlFor="admin-user-role">角色</label>
              <select
                id="admin-user-role"
                className="admin-input"
                value={selectedRole}
                onChange={(e) => {
                  const role = e.target.value;
                  setForm({
                    ...form,
                    role,
                    city_id: role === 'city_manager' ? form.city_id : null,
                    store_id: role === 'store_manager' ? form.store_id : null,
                    dealer_code: role === 'dealer' ? form.dealer_code : null,
                  });
                }}
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
                {editing?.role === 'dealer' && <option value="dealer">dealer（旧版经销商账号）</option>}
              </select>
            </div>
            {selectedRole === 'city_manager' && (
              <div className="admin-field">
                <label className="admin-field-label" htmlFor="admin-user-city">城市 ID</label>
                <input
                  id="admin-user-city"
                  className="admin-input"
                  type="number"
                  value={form.city_id ?? ''}
                  onChange={(e) => setForm({ ...form, city_id: e.target.value ? Number(e.target.value) : null })}
                />
              </div>
            )}
            {selectedRole === 'store_manager' && (
              <div className="admin-field">
                <label className="admin-field-label" htmlFor="admin-user-store">门店 ID</label>
                <input
                  id="admin-user-store"
                  className="admin-input"
                  type="number"
                  value={form.store_id ?? ''}
                  onChange={(e) => setForm({ ...form, store_id: e.target.value ? Number(e.target.value) : null })}
                />
              </div>
            )}
            {selectedRole === 'dealer' && (
              <div className="admin-field">
                <label className="admin-field-label" htmlFor="admin-user-dealer">经销商代码（dealer_code）</label>
                <input
                  id="admin-user-dealer"
                  className="admin-input"
                  value={form.dealer_code ?? ''}
                  onChange={(e) => setForm({ ...form, dealer_code: e.target.value || null })}
                />
              </div>
            )}
            {!showCreate && (
              <>
                <div className="admin-field">
                  <label className="admin-field-label" htmlFor="admin-reset-password">重置密码（留空表示不修改）</label>
                  <input
                    id="admin-reset-password"
                    className="admin-input"
                    type="password"
                    minLength={12}
                    maxLength={128}
                    value={form.password ?? ''}
                    onChange={(e) => setForm({ ...form, password: e.target.value || undefined })}
                    placeholder="至少 12 位"
                  />
                </div>
                <div className="admin-field-row">
                  <label>
                    <input
                      type="checkbox"
                      checked={form.is_active ?? true}
                      onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    />
                    启用
                  </label>
                </div>
              </>
            )}
            <div className="admin-form-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={showCreate ? createUser : save}
              >
                {showCreate ? '创建' : '保存'}
              </button>
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
          <div className="admin-empty">从左侧选择用户，或点击新建。</div>
        )}
      </section>
    </div>
  );
}

'use client';

import { FormEvent, useMemo, useState } from 'react';
import AdminStatusPill from '@/components/admin/AdminStatusPill';
import { adminFetch, type AdminCurrentUser } from '@/lib/api';

type Props = {
  token: string;
  user: AdminCurrentUser;
  showNotice: (message: string, kind?: 'success' | 'error' | 'info') => void;
  onPasswordChanged: () => void;
};

const ROLE_LABELS: Record<string, string> = {
  admin: '总部管理员',
  operator: '总部运营',
  city_manager: '城市管理员',
  store_manager: '门店管理员',
  dealer: '经销商',
};

function formatDate(value?: string | null) {
  if (!value) return '暂无记录';
  const hasTimeZone = /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
  const date = new Date(hasTimeZone ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return '暂无记录';
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  });
}

function scopeLabel(user: AdminCurrentUser) {
  if (user.store_id) return `门店 ID ${user.store_id}`;
  if (user.city_id) return `城市 ID ${user.city_id}`;
  if (user.dealer_code) return `经销商 ${user.dealer_code}`;
  return '总部全局范围';
}

export default function AccountSettingsPanel({ token, user, showNotice, onPasswordChanged }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const passwordChecks = useMemo(() => {
    const categories = [
      /[a-z]/.test(newPassword),
      /[A-Z]/.test(newPassword),
      /\d/.test(newPassword),
      /[^\p{L}\p{N}]/u.test(newPassword),
      /[^\x00-\x7F]/.test(newPassword),
    ].filter(Boolean).length;
    return {
      length: newPassword.length >= 12 && newPassword.length <= 128,
      categories: categories >= 3,
      matches: Boolean(confirmation) && newPassword === confirmation,
      categoryCount: categories,
    };
  }, [confirmation, newPassword]);

  const strength = useMemo(() => {
    if (!newPassword) return 0;
    let score = passwordChecks.length ? 1 : 0;
    if (passwordChecks.categoryCount >= 3) score += 1;
    if (newPassword.length >= 16) score += 1;
    if (passwordChecks.categoryCount >= 4) score += 1;
    return Math.min(score, 4);
  }, [newPassword, passwordChecks]);

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (!passwordChecks.length || !passwordChecks.categories) {
      showNotice('新密码不符合安全要求', 'error');
      return;
    }
    if (!passwordChecks.matches) {
      showNotice('两次输入的新密码不一致', 'error');
      return;
    }
    setSavingPassword(true);
    try {
      await adminFetch('/api/v1/auth/change-password', token, {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      sessionStorage.removeItem('admin_token');
      sessionStorage.removeItem('admin_refresh_token');
      showNotice('密码已修改，正在退出，请使用新密码重新登录', 'success');
      window.setTimeout(onPasswordChanged, 900);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '密码修改失败', 'error');
    } finally {
      setSavingPassword(false);
    }
  };

  const strengthLabel = ['未输入', '较弱', '一般', '良好', '强'][strength];

  return (
    <div className="admin-account-settings">
      <section className="admin-account-overview">
        <div className="admin-account-identity">
          <span className="admin-account-avatar" aria-hidden>{user.username.slice(0, 1).toUpperCase()}</span>
          <div>
            <span className="admin-kicker">当前登录账号</span>
            <h2>{user.username}</h2>
            <p>{ROLE_LABELS[user.role] || user.role} · {scopeLabel(user)}</p>
          </div>
        </div>
        <div className="admin-account-state-list" aria-label="账号安全状态">
          <AdminStatusPill tone="good">账号正常</AdminStatusPill>
          <AdminStatusPill tone={user.password_changed_at ? 'info' : 'warn'}>
            {user.password_changed_at ? '密码已更新' : '建议更新密码'}
          </AdminStatusPill>
        </div>
      </section>

      <div className="admin-account-grid">
        <aside className="admin-card admin-account-profile">
          <div className="admin-card-body">
            <div className="admin-card-head">
              <div>
                <h2>账号资料</h2>
                <p className="admin-card-note">账号和权限由管理员分配，此处仅展示。</p>
              </div>
            </div>
            <dl className="admin-account-details">
              <div><dt>登录账号</dt><dd>{user.username}</dd></div>
              <div><dt>账号编号</dt><dd>#{user.id}</dd></div>
              <div><dt>角色</dt><dd>{ROLE_LABELS[user.role] || user.role}</dd></div>
              <div><dt>权限范围</dt><dd>{scopeLabel(user)}</dd></div>
              <div><dt>创建时间</dt><dd>{formatDate(user.created_at)}</dd></div>
              <div><dt>最近登录</dt><dd>{formatDate(user.last_login_at)}</dd></div>
            </dl>
            <div className="admin-security-advice">
              <strong>安全建议</strong>
              <ul>
                <li className={user.password_changed_at ? 'is-complete' : ''}>定期更新高强度密码</li>
                <li className="is-complete">敏感操作需要当前密码确认</li>
                <li className="is-complete">离开公共设备前退出登录</li>
              </ul>
            </div>
          </div>
        </aside>

        <div className="admin-account-security-stack">
          <section className="admin-card">
            <form className="admin-card-body admin-form admin-security-form" onSubmit={changePassword}>
              <div className="admin-card-head">
                <div>
                  <h2>修改登录密码</h2>
                  <p className="admin-card-note">最近修改：{formatDate(user.password_changed_at)}</p>
                </div>
                <AdminStatusPill tone="info">修改后重新登录</AdminStatusPill>
              </div>
              <label>当前密码
                <input
                  type={showPasswords ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              </label>
              <div className="admin-field-row admin-password-fields">
                <label className="admin-field">新密码
                  <input
                    className="admin-input"
                    type={showPasswords ? 'text' : 'password'}
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={128}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    required
                  />
                </label>
                <label className="admin-field">确认新密码
                  <input
                    className="admin-input"
                    type={showPasswords ? 'text' : 'password'}
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={128}
                    value={confirmation}
                    onChange={(event) => setConfirmation(event.target.value)}
                    required
                  />
                </label>
              </div>
              <div className="admin-password-meter" aria-label={`密码强度：${strengthLabel}`}>
                <div className="admin-password-meter-head"><span>密码强度</span><strong>{strengthLabel}</strong></div>
                <div className="admin-password-meter-bars" aria-hidden>
                  {[1, 2, 3, 4].map((level) => <span key={level} className={strength >= level ? 'is-active' : ''} />)}
                </div>
              </div>
              <ul className="admin-password-rules">
                <li className={passwordChecks.length ? 'is-complete' : ''}>长度为 12–128 位</li>
                <li className={passwordChecks.categories ? 'is-complete' : ''}>大小写字母、数字、符号或中文至少三类</li>
                <li className={passwordChecks.matches ? 'is-complete' : ''}>两次输入的新密码一致</li>
              </ul>
              <label className="admin-check-row">
                <input type="checkbox" checked={showPasswords} onChange={(event) => setShowPasswords(event.target.checked)} />
                显示输入的密码
              </label>
              <p className="admin-form-warning">保存后当前账号的所有旧登录会立即失效，本页面也会自动退出。</p>
              <button className="btn btn-primary" type="submit" disabled={savingPassword}>
                {savingPassword ? '修改中…' : '修改密码并重新登录'}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}

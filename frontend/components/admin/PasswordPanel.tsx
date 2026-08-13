'use client';

import { FormEvent, useState } from 'react';
import { adminFetch } from '@/lib/api';

type Props = {
  token: string;
  username: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
  onPasswordChanged: () => void;
};

export default function PasswordPanel({ token, username, showNotice, onPasswordChanged }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword.length < 12) {
      showNotice('新密码至少 12 位', 'error');
      return;
    }
    if (newPassword !== confirmation) {
      showNotice('两次输入的新密码不一致', 'error');
      return;
    }
    setSaving(true);
    try {
      await adminFetch('/api/v1/auth/change-password', token, {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      sessionStorage.removeItem('admin_token');
      sessionStorage.removeItem('admin_refresh_token');
      showNotice('密码已修改，正在退出，请用新密码重新登录', 'success');
      window.setTimeout(onPasswordChanged, 900);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '密码修改失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="admin-card">
      <form className="admin-card-body admin-form" onSubmit={submit}>
        <h2>账号安全</h2>
        <p className="admin-card-note">当前账号：{username}。修改后所有旧登录令牌立即失效。</p>
        <label>当前密码
          <input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
        </label>
        <label>新密码
          <input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required />
        </label>
        <p className="admin-card-note">12–128 位，至少包含大小写字母、数字、符号或中文中的三类。</p>
        <label>确认新密码
          <input type="password" autoComplete="new-password" minLength={12} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required />
        </label>
        <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? '修改中…' : '修改密码'}</button>
      </form>
    </section>
  );
}

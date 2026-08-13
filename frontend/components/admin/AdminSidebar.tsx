'use client';

import BrandMark from '@/components/BrandMark';
import Link from 'next/link';

export type AdminTabItem = {
  id: string;
  label: string;
  hint: string;
};

type Props = {
  tabs: AdminTabItem[];
  active: string;
  onChange: (id: string) => void;
  onLogout: () => void;
  open: boolean;
  onClose: () => void;
  account?: {
    username: string;
    role: string;
    city_id?: number | null;
    store_id?: number | null;
  } | null;
};

const ROLE_LABELS: Record<string, string> = {
  admin: '总部管理员',
  operator: '总部运营',
  city_manager: '城市管理员',
  store_manager: '门店管理员',
  dealer: '经销商',
};

export default function AdminSidebar({ tabs, active, onChange, onLogout, open, onClose, account }: Props) {
  return (
    <>
      <button
        type="button"
        className={`admin-sidebar-backdrop ${open ? 'is-visible' : ''}`}
        aria-label="关闭菜单"
        onClick={onClose}
      />
      <aside className={`admin-sidebar ${open ? 'is-open' : ''}`}>
        <div className="admin-brand">
          <BrandMark className="admin-brand-mark" />
          <div>
            <strong>博雅敏格</strong>
            <span>运营工作台</span>
          </div>
        </div>

        <nav className="admin-nav" aria-label="后台导航">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              className={active === item.id ? 'is-active' : ''}
              onClick={() => {
                onChange(item.id);
                onClose();
              }}
            >
              <span className="admin-nav-label">{item.label}</span>
              <span className="admin-nav-hint">{item.hint}</span>
            </button>
          ))}
        </nav>

        <div className="admin-sidebar-foot">
          {account && (
            <button
              type="button"
              className={`admin-account-card${active === 'security' ? ' is-active' : ''}`}
              onClick={() => {
                onChange('security');
                onClose();
              }}
            >
              <strong>{account.username}</strong>
              <span>{ROLE_LABELS[account.role] || account.role}</span>
              {account.city_id && <small>城市 ID：{account.city_id}</small>}
              {account.store_id && <small>门店 ID：{account.store_id}</small>}
            </button>
          )}
          <Link href="/" className="admin-sidebar-link" target="_blank" prefetch={false}>
            查看官网
          </Link>
          <Link href="/articles" className="admin-sidebar-link" target="_blank" prefetch={false}>
            选购指南
          </Link>
          <button type="button" className="admin-logout" onClick={onLogout}>
            退出登录
          </button>
        </div>
      </aside>
    </>
  );
}

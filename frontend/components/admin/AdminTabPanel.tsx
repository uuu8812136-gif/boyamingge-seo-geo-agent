'use client';

export default function AdminTabPanel({ children }: { tabKey: string; children: React.ReactNode }) {
  return <div className="admin-tab-panel">{children}</div>;
}

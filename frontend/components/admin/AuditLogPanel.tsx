'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';

type AuditRow = {
  id: number; username: string | null; method: string; path: string; status_code: number;
  client_ip: string | null; created_at: string;
};
type Props = { token: string; showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void };

export default function AuditLogPanel({ token, showNotice }: Props) {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetch<{ items: AuditRow[]; total: number }>('/api/v1/admin/audit-logs?page_size=100', token);
      setRows(data.items || []); setTotal(data.total || 0);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '审计日志加载失败', 'error');
    } finally { setLoading(false); }
  }, [showNotice, token]);
  useEffect(() => { load(); }, [load]);
  return <section className="admin-card"><div className="admin-card-body">
    <div className="admin-toolbar"><div><h2>操作审计日志</h2><p className="admin-card-note">共 {total} 条；记录后台和公开接口的写操作，不保存密码或请求正文。</p></div><button className="btn btn-outline btn-sm" type="button" onClick={load} disabled={loading}>{loading ? '刷新中…' : '刷新'}</button></div>
    {rows.length === 0 ? <p className="admin-empty">暂无写操作记录。</p> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>时间</th><th>账号</th><th>操作</th><th>路径</th><th>状态</th><th>IP</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString('zh-CN')}</td><td>{row.username || '匿名访客'}</td><td>{row.method}</td><td>{row.path}</td><td>{row.status_code}</td><td>{row.client_ip || '-'}</td></tr>)}</tbody></table></div>}
  </div></section>;
}

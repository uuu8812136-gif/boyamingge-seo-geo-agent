'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';
import AdminCitySelector from './AdminCitySelector';

type CaseRow = { id: number; city_id: number; title: string; service_type: string | null; content: string; images: string[] };
type FaqRow = { id: number; city_id: number; question: string; answer: string };
type Props = { token: string; showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void };

export default function CityContentPanel({ token, showNotice }: Props) {
  const [cityId, setCityId] = useState<number | null>(null);
  const [mode, setMode] = useState<'cases' | 'faqs'>('cases');
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [faqs, setFaqs] = useState<FaqRow[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!cityId) return;
    setLoading(true);
    try {
      const [caseData, faqData] = await Promise.all([
        adminFetch<{ items: CaseRow[] }>(`/api/v1/admin/cities/${cityId}/cases`, token),
        adminFetch<{ items: FaqRow[] }>(`/api/v1/admin/cities/${cityId}/faqs`, token),
      ]);
      setCases(caseData.items || []);
      setFaqs(faqData.items || []);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '城市内容加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [cityId, showNotice, token]);

  useEffect(() => {
    setEditingId(null);
    setCreating(false);
    setForm({});
    if (cityId) load();
  }, [cityId, load]);

  const startCase = (row: CaseRow) => {
    setMode('cases'); setEditingId(row.id); setCreating(false);
    setForm({ title: row.title, service_type: row.service_type || '', content: row.content, images: row.images.join('\n') });
  };
  const startFaq = (row: FaqRow) => {
    setMode('faqs'); setEditingId(row.id); setCreating(false);
    setForm({ question: row.question, answer: row.answer });
  };
  const startCreate = () => {
    setEditingId(null); setCreating(true);
    setForm(mode === 'cases' ? { title: '', service_type: '', content: '', images: '' } : { question: '', answer: '' });
  };

  const save = async () => {
    if (!cityId) return;
    const isCase = mode === 'cases';
    const payload = isCase
      ? { title: form.title, service_type: form.service_type || null, content: form.content, images: (form.images || '').split(/[,\n]/).map((item) => item.trim()).filter(Boolean) }
      : { question: form.question, answer: form.answer };
    if (isCase ? !payload.title || !('content' in payload) || !payload.content : !('question' in payload) || !payload.question || !payload.answer) {
      showNotice('请填写完整内容', 'error'); return;
    }
    const path = creating
      ? `/api/v1/admin/cities/${cityId}/${mode}`
      : `/api/v1/admin/${isCase ? 'cases' : 'faqs'}/${editingId}`;
    try {
      await adminFetch(path, token, { method: creating ? 'POST' : 'PATCH', body: JSON.stringify(payload) });
      showNotice(`${isCase ? '案例' : 'FAQ'}已${creating ? '创建' : '更新'}`, 'success');
      setCreating(false); setEditingId(null); setForm({}); await load();
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '保存失败', 'error');
    }
  };

  const remove = async () => {
    if (!editingId || !confirm(`确认删除这个${mode === 'cases' ? '案例' : 'FAQ'}？`)) return;
    try {
      await adminFetch(`/api/v1/admin/${mode}/${editingId}`, token, { method: 'DELETE' });
      showNotice('已删除', 'success'); setEditingId(null); setForm({}); await load();
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '删除失败', 'error');
    }
  };

  const rows = mode === 'cases' ? cases : faqs;
  return (
    <div className="admin-panel-grid">
      <aside className="admin-panel-actions">
        <AdminCitySelector token={token} value={cityId} onChange={setCityId} />
        <div className="admin-field-row">
          <button type="button" className={`btn btn-sm ${mode === 'cases' ? 'btn-primary' : 'btn-outline'}`} onClick={() => { setMode('cases'); setEditingId(null); setCreating(false); }}>案例</button>
          <button type="button" className={`btn btn-sm ${mode === 'faqs' ? 'btn-primary' : 'btn-outline'}`} onClick={() => { setMode('faqs'); setEditingId(null); setCreating(false); }}>FAQ</button>
        </div>
        <button type="button" className="btn btn-primary btn-block" disabled={!cityId} onClick={startCreate}>新建{mode === 'cases' ? '案例' : 'FAQ'}</button>
        <button type="button" className="btn btn-outline btn-block" disabled={!cityId || loading} onClick={load}>{loading ? '刷新中…' : '刷新'}</button>
        {rows.map((row) => (
          <button key={row.id} type="button" className={`admin-list-item ${editingId === row.id ? 'is-active' : ''}`} onClick={() => mode === 'cases' ? startCase(row as CaseRow) : startFaq(row as FaqRow)}>
            <span className="admin-list-name">{'title' in row ? row.title : row.question}</span>
            <span className="admin-list-meta">ID {row.id}</span>
          </button>
        ))}
      </aside>
      <section className="admin-panel-main">
        {(creating || editingId) ? (
          <div className="admin-form">
            <h3 className="admin-form-title">{creating ? '新建' : '编辑'}{mode === 'cases' ? '案例' : 'FAQ'}</h3>
            {mode === 'cases' ? <>
              <label>标题<input value={form.title || ''} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
              <label>服务类型<input value={form.service_type || ''} onChange={(event) => setForm({ ...form, service_type: event.target.value })} placeholder="如：阳台封窗" /></label>
              <label>案例内容<textarea value={form.content || ''} onChange={(event) => setForm({ ...form, content: event.target.value })} /></label>
              <label>图片地址（每行一个）<textarea value={form.images || ''} onChange={(event) => setForm({ ...form, images: event.target.value })} /></label>
            </> : <>
              <label>问题<input value={form.question || ''} onChange={(event) => setForm({ ...form, question: event.target.value })} /></label>
              <label>回答<textarea value={form.answer || ''} onChange={(event) => setForm({ ...form, answer: event.target.value })} /></label>
            </>}
            <div className="admin-form-actions">
              <button type="button" className="btn btn-primary" onClick={save}>保存</button>
              {!creating && <button type="button" className="btn btn-outline" onClick={remove}>删除</button>}
              <button type="button" className="btn btn-outline" onClick={() => { setCreating(false); setEditingId(null); setForm({}); }}>取消</button>
            </div>
          </div>
        ) : <div className="admin-empty">{cityId ? `选择或新建${mode === 'cases' ? '案例' : 'FAQ'}。` : '请先选择城市。'}</div>}
      </section>
    </div>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { adminFetch } from '@/lib/api';
import { API_BASE } from '@/lib/site';
import AdminStatusPill from './AdminStatusPill';

type PostStatus = 'draft' | 'approved' | 'published' | 'offline' | 'rejected';

type ContentPost = {
  id: number;
  title: string | null;
  slug: string | null;
  post_type: string;
  city: string;
  store_id: number | null;
  status: string;
  summary: string | null;
  cover_image: string | null;
  seo_title: string | null;
  seo_description: string | null;
  canonical: string | null;
  keywords: string[];
  scheduled_at: string | null;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type PublicationRecord = {
  id: number;
  content_id: number;
  platform: string;
  tier: string;
  url: string | null;
  status: string;
  publish_mode: string;
  published_at: string | null;
  error_message: string | null;
  created_at: string | null;
};

type ContentMaterial = {
  id: number;
  content_id: number | null;
  filename: string;
  file_type: string;
  url: string | null;
  cover_url: string | null;
  size_mb: number | null;
  duration_sec: number | null;
  status: string;
  created_at: string | null;
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
  cityOptions?: string[];
  role?: string;
  defaultStoreId?: number | null;
  canUploadVideo?: boolean;
};

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  approved: '待发布',
  published: '已发布',
  offline: '已下线',
  rejected: '已驳回',
};

const STATUS_TONES: Record<string, 'neutral' | 'info' | 'good' | 'warn' | 'bad'> = {
  draft: 'neutral',
  approved: 'info',
  published: 'good',
  offline: 'warn',
  rejected: 'bad',
};

const POST_TYPES: Array<{ value: string; label: string }> = [
  { value: 'article', label: '文章' },
  { value: 'case', label: '案例' },
  { value: 'knowledge', label: '知识' },
  { value: 'seo_page', label: '城市页SEO' },
];

const EMPTY_FORM = {
  title: '',
  markdown: '',
  post_type: 'article',
  city: '',
  store_id: '',
  summary: '',
  cover_image: '',
  seo_title: '',
  seo_description: '',
  canonical: '',
  keywords: '',
};

/** 站内内容发布管理：列表 + 新建/编辑 + 发布/下线/定时 + 发布记录。 */
export default function ContentPublishPanel({
  token,
  showNotice,
  cityOptions,
  role,
  defaultStoreId,
  canUploadVideo = true,
}: Props) {
  const availableCities = useMemo(
    () => cityOptions || [],
    [cityOptions],
  );
  const emptyForm = useCallback(() => ({
    ...EMPTY_FORM,
    city: availableCities[0] || EMPTY_FORM.city,
    store_id: role === 'store_manager' && defaultStoreId ? String(defaultStoreId) : '',
  }), [availableCities, defaultStoreId, role]);
  const [posts, setPosts] = useState<ContentPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<ContentPost | null>(null);
  const [form, setForm] = useState(() => emptyForm());
  const [showForm, setShowForm] = useState(false);
  const [publications, setPublications] = useState<PublicationRecord[]>([]);
  const [showPubs, setShowPubs] = useState(false);
  const [scheduleAt, setScheduleAt] = useState('');
  const [showSchedule, setShowSchedule] = useState(false);
  // 视频素材（供短视频平台外部分发使用）
  const [videos, setVideos] = useState<ContentMaterial[]>([]);
  const [videoUploading, setVideoUploading] = useState(false);
  const videoInputRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      params.set('page', String(page));
      params.set('page_size', '20');
      const data = await adminFetch<{ items: ContentPost[]; total: number }>(
        `/api/v1/content/posts?${params}`,
        token,
      );
      setPosts(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [token, showNotice, statusFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const loadPublications = async () => {
    try {
      const data = await adminFetch<{ items: PublicationRecord[]; total: number }>(
        `/api/v1/content/publications?page=1&page_size=50`,
        token,
      );
      setPublications(data.items || []);
      setShowPubs(true);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载发布记录失败', 'error');
    }
  };

  const startCreate = () => {
    setEditing(null);
    setForm(emptyForm());
    setShowForm(true);
    setShowSchedule(false);
    setScheduleAt('');
  };

  const loadVideos = useCallback(async (contentId: number) => {
    try {
      const data = await adminFetch<{ items: ContentMaterial[]; total: number }>(
        `/api/v1/content/${contentId}/materials?file_type=video`,
        token,
      );
      setVideos(data.items || []);
    } catch {
      setVideos([]);
    }
  }, [token]);

  const startEdit = (row: ContentPost) => {
    setEditing(row);
    setForm({
      title: row.title || '',
      markdown: '',
      post_type: row.post_type || 'article',
      city: row.city,
      store_id: row.store_id ? String(row.store_id) : '',
      summary: row.summary || '',
      cover_image: row.cover_image || '',
      seo_title: row.seo_title || '',
      seo_description: row.seo_description || '',
      canonical: row.canonical || '',
      keywords: Array.isArray(row.keywords) ? row.keywords.join(', ') : '',
    });
    setVideos([]);
    setShowForm(true);
    loadVideos(row.id);
  };

  const uploadVideo = async (file: File) => {
    if (!editing) return;
    setVideoUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API_BASE}/api/v1/content/${editing.id}/materials/video`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `上传失败 ${res.status}`);
      }
      showNotice('视频素材已上传并绑定该内容', 'success');
      await loadVideos(editing.id);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '视频上传失败', 'error');
    } finally {
      setVideoUploading(false);
      if (videoInputRef.current) videoInputRef.current.value = '';
    }
  };

  const removeVideo = async (material: ContentMaterial) => {
    if (!editing) return;
    if (!confirm(`确认移除视频素材「${material.filename}」？`)) return;
    try {
      await adminFetch(`/api/v1/content/${editing.id}/materials/${material.id}`, token, { method: 'DELETE' });
      showNotice('视频素材已移除', 'info');
      await loadVideos(editing.id);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '移除失败', 'error');
    }
  };

  const save = async () => {
    if (!form.title.trim()) {
      showNotice('请输入标题', 'error');
      return;
    }
    const body: Record<string, unknown> = {
      title: form.title,
      markdown: form.markdown,
      post_type: form.post_type,
      city: form.city,
      summary: form.summary || null,
      cover_image: form.cover_image || null,
      seo_title: form.seo_title || null,
      seo_description: form.seo_description || null,
      canonical: form.canonical || null,
      keywords: form.keywords
        ? form.keywords.split(',').map((k) => k.trim()).filter(Boolean)
        : [],
      type: 'seo',
    };
    if (form.store_id) body.store_id = Number(form.store_id);
    try {
      if (editing) {
        await adminFetch(`/api/v1/content/posts/${editing.id}`, token, {
          method: 'PUT',
          body: JSON.stringify(body),
        });
        showNotice('内容已更新', 'success');
      } else {
        await adminFetch(`/api/v1/content/posts`, token, {
          method: 'POST',
          body: JSON.stringify(body),
        });
        showNotice('内容已创建（草稿）', 'success');
      }
      setShowForm(false);
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '保存失败', 'error');
    }
  };

  const publish = async (row: ContentPost, mode: 'direct' | 'schedule') => {
    const body =
      mode === 'schedule'
        ? { publish_mode: 'schedule', scheduled_at: scheduleAt }
        : { publish_mode: 'direct' };
    try {
      const result = await adminFetch<{ status: string; url?: string }>(
        `/api/v1/content/posts/${row.id}/publish`,
        token,
        { method: 'POST', body: JSON.stringify(body) },
      );
      if (result.status === 'scheduled') {
        showNotice(`已加入定时发布（${scheduleAt}）`, 'success');
      } else {
        showNotice('已发布到官网', 'success');
      }
      setShowSchedule(false);
      setScheduleAt('');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '发布失败', 'error');
    }
  };

  const unpublish = async (row: ContentPost) => {
    if (!confirm(`确认下线「${row.title}」？`)) return;
    try {
      await adminFetch(`/api/v1/content/posts/${row.id}/unpublish`, token, { method: 'POST' });
      showNotice('内容已下线', 'info');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '下线失败', 'error');
    }
  };

  const remove = async (row: ContentPost) => {
    if (!confirm(`确认删除「${row.title}」？仅草稿/已下线可删除。`)) return;
    try {
      await adminFetch(`/api/v1/content/posts/${row.id}`, token, { method: 'DELETE' });
      showNotice('内容已删除', 'info');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '删除失败', 'error');
    }
  };

  const previewUrl = (row: ContentPost): string | undefined => {
    if (row.slug) return `/articles/${row.slug}`;
    return undefined;
  };

  if (showForm) {
    return (
      <div className="admin-stack">
        <section className="admin-card">
          <div className="admin-card-body admin-form">
            <div className="admin-toolbar">
              <h2>{editing ? '编辑内容' : '新建内容'}</h2>
              <button className="btn btn-outline btn-sm" type="button" onClick={() => setShowForm(false)}>
                返回列表
              </button>
            </div>
            <label>标题<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="文章标题" /></label>
            <label>类型
              <select value={form.post_type} onChange={(e) => setForm({ ...form, post_type: e.target.value })}>
                {POST_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </label>
            <label>城市
              <select value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}>
                {availableCities.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label>门店 ID（可选）
              <input
                value={form.store_id}
                readOnly={role === 'store_manager'}
                onChange={(e) => setForm({ ...form, store_id: e.target.value })}
                placeholder="留空表示不绑定门店"
              />
            </label>
            <label>摘要<input value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} placeholder="一句话摘要" /></label>
            <label>正文（Markdown）<textarea rows={10} value={form.markdown} onChange={(e) => setForm({ ...form, markdown: e.target.value })} placeholder="## 标题\n\n正文内容..." /></label>
            <label>封面图 URL<input value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.target.value })} placeholder="/images/cover.jpg" /></label>
            <label>SEO Title<input value={form.seo_title} onChange={(e) => setForm({ ...form, seo_title: e.target.value })} placeholder="SEO 标题（不填则用文章标题）" /></label>
            <label>SEO Description<input value={form.seo_description} onChange={(e) => setForm({ ...form, seo_description: e.target.value })} placeholder="SEO 描述" /></label>
            <label>Canonical URL<input value={form.canonical} onChange={(e) => setForm({ ...form, canonical: e.target.value })} placeholder="留空则自动生成" /></label>
            <label>关键词（逗号分隔）<input value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} placeholder="防盗门, 广州, 选购" /></label>

            {editing && canUploadVideo ? (
              <div className="admin-video-section">
                <div className="admin-video-head">
                  <span>视频素材（用于视频号/抖音/快手/B站分发）</span>
                  <input
                    ref={videoInputRef}
                    type="file"
                    accept="video/*"
                    style={{ display: 'none' }}
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadVideo(f); }}
                  />
                  <button
                    className="btn btn-outline btn-sm"
                    type="button"
                    disabled={videoUploading}
                    onClick={() => videoInputRef.current?.click()}
                  >
                    {videoUploading ? '上传中…' : '上传视频'}
                  </button>
                </div>
                {videos.length === 0 ? (
                  <p className="admin-card-note">尚未绑定视频素材。上传后可在「外部分发」中向短视频平台发布（mp4/mov/webm，≤500MB）。</p>
                ) : (
                  <ul className="admin-video-list">
                    {videos.map((v) => (
                      <li key={v.id}>
                        <span className="admin-video-name">{v.filename}</span>
                        <span className="admin-video-meta">{v.size_mb ? `${v.size_mb}MB` : ''}</span>
                        {v.url && (
                          <a className="admin-video-link" href={`${API_BASE}${v.url}`} target="_blank" rel="noreferrer">查看</a>
                        )}
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => removeVideo(v)}>移除</button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : canUploadVideo ? (
              <p className="admin-card-note">提示：视频素材需先创建草稿后，在「编辑」态上传绑定。</p>
            ) : null}

            <div className="admin-form-actions">
              <button className="btn btn-primary" type="button" onClick={save}>{editing ? '保存修改' : '创建草稿'}</button>
              <button className="btn btn-outline" type="button" onClick={() => setShowForm(false)}>取消</button>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (showPubs) {
    return (
      <div className="admin-stack">
        <section className="admin-card">
          <div className="admin-card-body">
            <div className="admin-toolbar">
              <h2>发布记录</h2>
              <button className="btn btn-outline btn-sm" type="button" onClick={() => setShowPubs(false)}>返回内容列表</button>
            </div>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>内容ID</th>
                  <th>平台</th>
                  <th>层级</th>
                  <th>状态</th>
                  <th>URL</th>
                  <th>模式</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {publications.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>{p.content_id}</td>
                    <td>{p.platform}</td>
                    <td>{p.tier}</td>
                    <td><AdminStatusPill tone={p.status === 'published' ? 'good' : p.status === 'offline' ? 'warn' : 'info'}>{p.status}</AdminStatusPill></td>
                    <td>{p.url ? <a href={p.url} target="_blank" rel="noreferrer">查看</a> : '-'}</td>
                    <td>{p.publish_mode}</td>
                    <td>{p.published_at || p.created_at || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="admin-stack">
      <div className="admin-guide-banner">
        <strong>站内内容发布</strong>
        <p>创建文章/案例/知识内容，发布到官网城市站。支持草稿、定时发布、下线，发布后自动生成 /articles/ 路径并纳入 sitemap。</p>
      </div>

      <div className="admin-toolbar">
        <div className="admin-toolbar-controls">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
            <option value="">全部状态</option>
            <option value="draft">草稿</option>
            <option value="approved">待发布</option>
            <option value="published">已发布</option>
            <option value="offline">已下线</option>
          </select>
          <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={load}>刷新</button>
          <button className="btn btn-outline btn-sm" type="button" onClick={loadPublications}>发布记录</button>
        </div>
        <button className="btn btn-primary btn-sm" type="button" onClick={startCreate}>+ 新建内容</button>
      </div>

      <section className="admin-card">
        <div className="admin-card-body">
          {posts.length === 0 ? (
            <p className="admin-empty">暂无内容，点击「新建内容」创建第一篇。</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>标题</th>
                  <th>类型</th>
                  <th>城市</th>
                  <th>状态</th>
                  <th>发布时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.title || '(无标题)'}</td>
                    <td>{POST_TYPES.find((t) => t.value === row.post_type)?.label || row.post_type}</td>
                    <td>{row.city}</td>
                    <td><AdminStatusPill tone={STATUS_TONES[row.status] || 'neutral'}>{STATUS_LABELS[row.status] || row.status}</AdminStatusPill></td>
                    <td>{row.published_at ? row.published_at.slice(0, 10) : row.scheduled_at ? `定时 ${row.scheduled_at.slice(0, 16)}` : '-'}</td>
                    <td>
                      <div className="admin-row-actions">
                        {previewUrl(row) && row.status === 'published' && (
                          <a href={previewUrl(row)} target="_blank" rel="noreferrer" className="admin-task-link">预览</a>
                        )}
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => startEdit(row)}>编辑</button>
                        {(row.status === 'draft' || row.status === 'approved' || row.status === 'offline') && (
                          <>
                            <button className="btn btn-primary btn-sm" type="button" onClick={() => publish(row, 'direct')}>立即发布</button>
                            <button className="btn btn-outline btn-sm" type="button" onClick={() => { setShowSchedule(true); setEditing(row); }}>定时</button>
                          </>
                        )}
                        {row.status === 'published' && (
                          <button className="btn btn-outline btn-sm" type="button" onClick={() => unpublish(row)}>下线</button>
                        )}
                        {(row.status === 'draft' || row.status === 'offline') && (
                          <button className="btn btn-outline btn-sm" type="button" onClick={() => remove(row)}>删除</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {total > 20 && (
            <div className="admin-pagination">
              <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
              <span>第 {page} 页</span>
              <button className="btn btn-outline btn-sm" disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>下一页</button>
            </div>
          )}
        </div>
      </section>

      {showSchedule && editing && (
        <div className="admin-modal-overlay" onClick={() => setShowSchedule(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>定时发布 — {editing.title}</h3>
            <label>发布时间
              <input
                type="datetime-local"
                value={scheduleAt}
                onChange={(e) => setScheduleAt(e.target.value)}
              />
            </label>
            <p className="admin-card-note">到达指定时间后，后台扫描线程会自动发布。</p>
            <div className="admin-form-actions">
              <button
                className="btn btn-primary"
                type="button"
                disabled={!scheduleAt}
                onClick={() => publish(editing, 'schedule')}
              >确认定时</button>
              <button className="btn btn-outline" type="button" onClick={() => setShowSchedule(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

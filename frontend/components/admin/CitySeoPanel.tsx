'use client';

import { useCallback, useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';
import AdminCitySelector from './AdminCitySelector';

type CityDetail = {
  id: number;
  name: string;
  slug: string;
  seo_title: string | null;
  seo_description: string | null;
  hero_title: string | null;
  hero_subtitle: string | null;
  subdomain: string | null;
  custom_domain: string | null;
  canonical_url: string | null;
  seo_keywords: string[];
  seo_indexable: boolean;
  robots_policy: string;
  hero_image: string | null;
  service_tags: string[];
};

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
};

/** 城市 SEO：编辑标题/描述/canonical/robots/关键词等。 */
export default function CitySeoPanel({ token, showNotice }: Props) {
  const [cityId, setCityId] = useState<number | null>(null);
  const [detail, setDetail] = useState<CityDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<Partial<CityDetail>>({});

  const load = useCallback(async () => {
    if (!cityId) return;
    setLoading(true);
    try {
      const data = await adminFetch<CityDetail>(`/api/v1/admin/cities/${cityId}`, token);
      setDetail(data);
      setForm({
        seo_title: data.seo_title,
        seo_description: data.seo_description,
        hero_title: data.hero_title,
        hero_subtitle: data.hero_subtitle,
        subdomain: data.subdomain,
        custom_domain: data.custom_domain,
        canonical_url: data.canonical_url,
        seo_keywords: data.seo_keywords,
        seo_indexable: data.seo_indexable,
        robots_policy: data.robots_policy === 'noindex' ? 'noindex_nofollow' : data.robots_policy,
        hero_image: data.hero_image,
        service_tags: data.service_tags,
      });
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [cityId, token, showNotice]);

  useEffect(() => {
    if (cityId) load();
    else setDetail(null);
  }, [cityId, load]);

  const save = async () => {
    if (!cityId) return;
    try {
      await adminFetch(`/api/v1/admin/cities/${cityId}`, token, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      showNotice('SEO 配置已保存', 'success');
      load();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '保存失败', 'error');
    }
  };

  return (
    <div className="admin-panel-grid">
      <aside className="admin-panel-actions">
        <AdminCitySelector token={token} value={cityId} onChange={setCityId} />
        <button
          type="button"
          className="btn btn-primary btn-block"
          onClick={save}
          disabled={!cityId || loading}
        >
          保存 SEO 配置
        </button>
        <button
          type="button"
          className="btn btn-outline btn-block"
          onClick={load}
          disabled={!cityId || loading}
        >
          {loading ? '加载中…' : '重新加载'}
        </button>
      </aside>

      <section className="admin-panel-main">
        {detail ? (
          <div className="admin-form">
            <h3 className="admin-form-title">{detail.name} - SEO 配置</h3>
            <div className="admin-field">
              <label className="admin-field-label">SEO 标题</label>
              <input
                className="admin-input"
                value={form.seo_title ?? ''}
                onChange={(e) => setForm({ ...form, seo_title: e.target.value })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">SEO 描述</label>
              <textarea
                className="admin-input admin-textarea"
                rows={2}
                value={form.seo_description ?? ''}
                onChange={(e) => setForm({ ...form, seo_description: e.target.value })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">Hero 标题</label>
              <input
                className="admin-input"
                value={form.hero_title ?? ''}
                onChange={(e) => setForm({ ...form, hero_title: e.target.value })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">Hero 副标题</label>
              <input
                className="admin-input"
                value={form.hero_subtitle ?? ''}
                onChange={(e) => setForm({ ...form, hero_subtitle: e.target.value })}
              />
            </div>
            <div className="admin-field-row">
              <div className="admin-field">
                <label className="admin-field-label">子域名</label>
                <input
                  className="admin-input"
                  value={form.subdomain ?? ''}
                  onChange={(e) => setForm({ ...form, subdomain: e.target.value || null })}
                />
              </div>
              <div className="admin-field">
                <label className="admin-field-label">自定义域名</label>
                <input
                  className="admin-input"
                  value={form.custom_domain ?? ''}
                  onChange={(e) => setForm({ ...form, custom_domain: e.target.value || null })}
                />
              </div>
            </div>
            <div className="admin-field">
              <label className="admin-field-label">canonical_url</label>
              <input
                className="admin-input"
                value={form.canonical_url ?? ''}
                placeholder="留空自动生成 https://子域名.boyamingge.com/"
                onChange={(e) => setForm({ ...form, canonical_url: e.target.value || null })}
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">关键词（逗号分隔）</label>
              <input
                className="admin-input"
                value={(form.seo_keywords || []).join(',')}
                onChange={(e) =>
                  setForm({
                    ...form,
                    seo_keywords: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
            </div>
            <div className="admin-field">
              <label className="admin-field-label">服务标签（逗号分隔）</label>
              <input
                className="admin-input"
                value={(form.service_tags || []).join(',')}
                onChange={(e) =>
                  setForm({
                    ...form,
                    service_tags: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
            </div>
            <div className="admin-field-row">
              <div className="admin-field">
                <label className="admin-field-label" htmlFor="city-seo-robots">robots 策略</label>
                <select
                  id="city-seo-robots"
                  className="admin-input"
                  value={form.robots_policy ?? 'index_follow'}
                  onChange={(e) => setForm({ ...form, robots_policy: e.target.value })}
                >
                  <option value="index_follow">index, follow（收录）</option>
                  <option value="noindex_follow">noindex, follow（不收录，允许跟踪链接）</option>
                  <option value="noindex_nofollow">noindex, nofollow（不收录且不跟踪链接）</option>
                </select>
              </div>
              <div className="admin-field">
                <label className="admin-field-label">可索引</label>
                <label>
                  <input
                    type="checkbox"
                    checked={form.seo_indexable ?? true}
                    onChange={(e) => setForm({ ...form, seo_indexable: e.target.checked })}
                  />
                  允许搜索引擎索引
                </label>
              </div>
            </div>
            <div className="admin-field">
              <label className="admin-field-label">Hero 图片 URL</label>
              <input
                className="admin-input"
                value={form.hero_image ?? ''}
                onChange={(e) => setForm({ ...form, hero_image: e.target.value || null })}
              />
            </div>
          </div>
        ) : (
          <div className="admin-empty">{cityId ? '加载中…' : '请先选择城市。'}</div>
        )}
      </section>
    </div>
  );
}

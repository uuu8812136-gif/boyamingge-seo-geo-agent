'use client';

import { useEffect, useState } from 'react';
import { adminFetch } from '@/lib/api';

type CityOption = { id: number; name: string; slug: string; subdomain: string | null };

type Props = {
  token: string;
  value: number | null;
  onChange: (cityId: number | null) => void;
};

/** 城市选择器：被门店/SEO/案例面板复用。从 /api/v1/admin/cities 拉取。 */
export default function AdminCitySelector({ token, value, onChange }: Props) {
  const [cities, setCities] = useState<CityOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    adminFetch<{ items: CityOption[]; total: number }>(`/api/v1/admin/cities`, token)
      .then((data) => {
        if (alive) setCities(data.items || []);
      })
      .catch(() => {
        if (alive) setCities([]);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [token]);

  useEffect(() => {
    if (!value && cities.length === 1) {
      onChange(cities[0].id);
    }
  }, [cities, onChange, value]);

  return (
    <div className="admin-field">
      <label className="admin-field-label">选择城市</label>
      <select
        className="admin-input"
        value={value ?? ''}
        disabled={loading}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">{loading ? '加载中…' : '请选择城市'}</option>
        {cities.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}（{c.slug}{c.subdomain ? ` / ${c.subdomain}` : ''}）
          </option>
        ))}
      </select>
    </div>
  );
}

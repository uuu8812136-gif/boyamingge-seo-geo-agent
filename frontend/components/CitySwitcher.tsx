'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

type CityOption = { slug: string; name: string };

type GeoLocateResponse = {
  ok?: boolean;
  cityName?: string | null;
  rawCity?: string | null;
};

type BackendLocateResponse = {
  city?: { name?: string; slug?: string } | null;
  redirect_slug?: string | null;
};

function normalizeCityName(value: string | null | undefined) {
  return (value || '')
    .trim()
    .replace(/^(中国|中华人民共和国)/, '')
    .replace(/(特别行政区|自治州|地区|盟|市|省|自治区|壮族自治区|回族自治区|维吾尔自治区)$/u, '')
    .trim();
}

function getBrowserPosition() {
  if (typeof window === 'undefined' || !navigator.geolocation) return Promise.resolve(null);

  return new Promise<GeolocationPosition | null>((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve(position),
      () => resolve(null),
      {
        enableHighAccuracy: false,
        timeout: 6000,
        maximumAge: 10 * 60 * 1000,
      },
    );
  });
}

export default function CitySwitcher({ currentCity }: { currentCity?: string }) {
  const [open, setOpen] = useState(false);
  const [cities, setCities] = useState<CityOption[]>([]);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // 仅展示后台已发布城市，避免把基础字典误当成已开通门店。
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch('/api/v1/cities?active_only=true');
        if (!res.ok) throw new Error('api error');
        const data = await res.json();
        if (cancelled) return;
        const apiCities: CityOption[] = (data.items || []).map((c: any) => ({ slug: c.slug, name: c.name }));
        setCities(apiCities);
      } catch {
        if (cancelled) return;
        setCities([]);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const currentName = cities.find((c) => c.slug === currentCity)?.name;
  const displayName = currentName || '选择城市';

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleSelect(slug: string) {
    setOpen(false);
    if (typeof window !== 'undefined') {
      localStorage.setItem('selected_city', slug);
    }
    router.push(`/${slug}`);
  }

  function findSlugByCityName(cityName: string) {
    const normalized = normalizeCityName(cityName);
    const fromApi = cities.find((city) => normalizeCityName(city.name) === normalized)?.slug;
    if (fromApi) return fromApi;
    return null;
  }

  async function readGeoCity(url: string) {
    const res = await fetch(url, { cache: 'no-store' });
    const data = (await res.json()) as GeoLocateResponse;
    if (!res.ok || !data.ok) return '';
    return normalizeCityName(data.cityName || data.rawCity);
  }

  async function handleLocate() {
    if (locating) return;
    setLocating(true);
    setLocateError('');

    try {
      let cityName = '';
      const position = await getBrowserPosition();
      if (position) {
        const { latitude, longitude } = position.coords;
        cityName = await readGeoCity(`/api/geo/locate?lat=${latitude}&lng=${longitude}`);
      }

      if (!cityName) {
        cityName = await readGeoCity('/api/geo/locate');
      }

      if (!cityName) {
        setLocateError('暂未定位到城市，请手动选择');
        return;
      }

      let slug = findSlugByCityName(cityName);
      try {
        const locatedRes = await fetch(`/api/v1/cities/locate?city_name=${encodeURIComponent(cityName)}`, {
          cache: 'no-store',
        });
        if (locatedRes.ok) {
          const located = (await locatedRes.json()) as BackendLocateResponse;
          slug = located.redirect_slug || located.city?.slug || slug;
        }
      } catch {
        // 后端定位失败时继续使用前端城市映射兜底。
      }

      if (!slug) {
        setLocateError(`${cityName}暂未开通门店，请手动选择`);
        return;
      }

      handleSelect(slug);
    } catch {
      setLocateError('定位失败，请手动选择');
    } finally {
      setLocating(false);
    }
  }

  return (
    <div ref={ref} className="city-switcher">
      <button
        className="city-switcher-btn"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="切换城市"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        <span>{displayName}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <ul className="city-switcher-dropdown" role="listbox">
          <li className="city-switcher-locate-item">
            <button type="button" className="city-switcher-locate" onClick={handleLocate} disabled={locating}>
              {locating ? '定位中…' : '定位当前城市'}
            </button>
            {locateError && <span className="city-switcher-error">{locateError}</span>}
          </li>
          {cities.map((city) => (
            <li key={city.slug} role="option" aria-selected={city.slug === currentCity}>
              <button onClick={() => handleSelect(city.slug)} className={city.slug === currentCity ? 'active' : ''}>
                {city.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

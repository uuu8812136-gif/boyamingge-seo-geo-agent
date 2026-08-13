'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

type AmapLocateResponse = {
  ok?: boolean;
  cityName?: string | null;
  rawCity?: string | null;
};

type BackendLocateResponse = {
  city?: { name?: string; slug?: string } | null;
  redirect_slug?: string | null;
  message?: string | null;
};

function normalizeCityName(value: string | null | undefined) {
  return (value || '')
    .trim()
    .replace(/^(中国|中华人民共和国)/, '')
    .replace(/(特别行政区|自治州|地区|盟|市|省|自治区|壮族自治区|回族自治区|维吾尔自治区)$/u, '')
    .trim();
}

async function readGeoCity(url: string) {
  const geoRes = await fetch(url, { cache: 'no-store' });
  const geo = (await geoRes.json()) as AmapLocateResponse;
  if (!geoRes.ok || !geo.ok) return '';
  return normalizeCityName(geo.cityName || geo.rawCity);
}

export default function CityDetector() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    const applyCity = (cityName: string, slug: string | null) => {
      if (cancelled || !cityName || !slug) return;
      localStorage.setItem('selected_city', slug);
      router.replace(`/${slug}`);
    };

    const cityParam = normalizeCityName(searchParams.get('city'));
    if (cityParam) {
      void (async () => {
        try {
          const response = await fetch(`/api/v1/cities/locate?city_name=${encodeURIComponent(cityParam)}`, { cache: 'no-store' });
          if (!response.ok) return;
          const located = (await response.json()) as BackendLocateResponse;
          applyCity(normalizeCityName(located.city?.name) || cityParam, located.redirect_slug || null);
        } catch {
          // 未发布城市不显示跳转提示。
        }
      })();
      return () => { cancelled = true; };
    }

    if (typeof window !== 'undefined' && localStorage.getItem('selected_city')) {
      return () => {
        cancelled = true;
      };
    }

    async function detectByAmap() {
      try {
        const cityName = await readGeoCity('/api/geo/locate');
        if (!cityName) return;

        let slug: string | null = null;
        let displayName = cityName;

        try {
          const locateRes = await fetch(`/api/v1/cities/locate?city_name=${encodeURIComponent(cityName)}`, {
            cache: 'no-store',
          });
          if (locateRes.ok) {
            const located = (await locateRes.json()) as BackendLocateResponse;
            slug = located.redirect_slug || located.city?.slug || slug;
            displayName = normalizeCityName(located.city?.name) || displayName;
          }
        } catch {
          // 后端定位接口异常时，保留高德返回城市并用本地映射兜底。
        }

        applyCity(displayName, slug);
      } catch {
        // 静默失败：定位不可用时不打断首页浏览。
      }
    }

    detectByAmap();

    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  return null;
}

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const AMAP_IP_ENDPOINT = 'https://restapi.amap.com/v3/ip';
const AMAP_REVERSE_GEOCODE_ENDPOINT = 'https://restapi.amap.com/v3/geocode/regeo';
const DIRECT_CITY_PROVINCES = new Set(['北京', '上海', '天津', '重庆']);

function firstForwardedIp(headers: Headers) {
  const raw =
    headers.get('x-forwarded-for') ||
    headers.get('x-real-ip') ||
    headers.get('cf-connecting-ip') ||
    '';
  return raw.split(',').map((item) => item.trim()).find(Boolean) || '';
}

function isPrivateOrLocalIp(ip: string) {
  if (!ip) return true;
  if (ip === '::1' || ip === '127.0.0.1' || ip.startsWith('fe80:')) return true;
  if (ip.startsWith('10.') || ip.startsWith('192.168.')) return true;
  const match = ip.match(/^172\.(\d+)\./);
  if (match) {
    const part = Number(match[1]);
    if (part >= 16 && part <= 31) return true;
  }
  return false;
}

function pickAmapText(value: unknown) {
  if (Array.isArray(value)) return typeof value[0] === 'string' ? value[0] : '';
  return typeof value === 'string' ? value : '';
}

function normalizeCityName(value: string) {
  return value
    .trim()
    .replace(/^(中国|中华人民共和国)/, '')
    .replace(/(特别行政区|自治州|地区|盟|市|省|自治区|壮族自治区|回族自治区|维吾尔自治区)$/u, '')
    .trim();
}

function readCityFromAmapAddressComponent(addressComponent: any) {
  const rawCity = pickAmapText(addressComponent?.city);
  const rawProvince = pickAmapText(addressComponent?.province);
  const provinceName = normalizeCityName(rawProvince);
  const cityName =
    normalizeCityName(rawCity) ||
    (DIRECT_CITY_PROVINCES.has(provinceName) ? provinceName : '');
  return { rawCity, rawProvince, cityName };
}

async function fetchAmapJson(url: URL, signal: AbortSignal) {
  const response = await fetch(url, {
    cache: 'no-store',
    signal,
    headers: { Accept: 'application/json' },
  });
  const data = await response.json();
  return { response, data };
}

export async function GET(request: NextRequest) {
  const rawSearchParams = new URL(request.url).searchParams;
  const latParam = request.nextUrl.searchParams.get('lat') || rawSearchParams.get('lat');
  const lngParam = request.nextUrl.searchParams.get('lng') || rawSearchParams.get('lng');
  if ((latParam && !lngParam) || (!latParam && lngParam)) {
    return NextResponse.json({ ok: false, message: 'lat 和 lng 必须同时提供' }, { status: 400 });
  }

  const lat = Number(latParam);
  const lng = Number(lngParam);
  if (
    latParam &&
    lngParam &&
    (!Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180)
  ) {
    return NextResponse.json({ ok: false, message: '经纬度参数无效' }, { status: 400 });
  }

  const key = process.env.AMAP_WEB_SERVICE_KEY;

  if (!key) {
    return NextResponse.json({ ok: false, message: 'AMap key is not configured' }, { status: 503 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4500);

  try {
    if (latParam && lngParam && Number.isFinite(lat) && Number.isFinite(lng)) {
      const url = new URL(AMAP_REVERSE_GEOCODE_ENDPOINT);
      url.searchParams.set('key', key);
      url.searchParams.set('location', `${lng},${lat}`);
      url.searchParams.set('extensions', 'base');
      const { response, data } = await fetchAmapJson(url, controller.signal);

      if (!response.ok || data.status !== '1') {
        return NextResponse.json({
          ok: false,
          provider: 'amap-regeo',
          message: data.info || `AMap request failed: ${response.status}`,
          infocode: data.infocode || null,
        });
      }

      const { rawCity, rawProvince, cityName } = readCityFromAmapAddressComponent(
        data.regeocode?.addressComponent,
      );

      return NextResponse.json({
        ok: Boolean(cityName),
        provider: 'amap-regeo',
        cityName: cityName || null,
        rawCity: rawCity || null,
        province: rawProvince || null,
        adcode: data.regeocode?.addressComponent?.adcode || null,
        district: pickAmapText(data.regeocode?.addressComponent?.district) || null,
        message: cityName ? null : '暂未从当前位置解析到城市',
      });
    }

    const ip = firstForwardedIp(request.headers);
    const url = new URL(AMAP_IP_ENDPOINT);
    url.searchParams.set('key', key);
    if (ip && !isPrivateOrLocalIp(ip)) {
      url.searchParams.set('ip', ip);
    }

    const { response, data } = await fetchAmapJson(url, controller.signal);

    if (!response.ok || data.status !== '1') {
      return NextResponse.json({
        ok: false,
        provider: 'amap-ip',
        message: data.info || `AMap request failed: ${response.status}`,
        infocode: data.infocode || null,
      });
    }

    const rawCity = pickAmapText(data.city);
    const rawProvince = pickAmapText(data.province);
    const provinceName = normalizeCityName(rawProvince);
    const cityName =
      normalizeCityName(rawCity) ||
      (DIRECT_CITY_PROVINCES.has(provinceName) ? provinceName : '');

    return NextResponse.json({
      ok: Boolean(cityName),
      provider: 'amap-ip',
      cityName: cityName || null,
      rawCity: rawCity || null,
      province: rawProvince || null,
      adcode: data.adcode || null,
      rectangle: data.rectangle || null,
      message: cityName ? null : '暂未从当前网络定位到城市',
    });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === 'AbortError';
    return NextResponse.json({
      ok: false,
      provider: 'amap-ip',
      message: timedOut ? '地图定位服务响应超时' : error instanceof Error ? error.message : 'AMap request failed',
    }, { status: timedOut ? 504 : 502 });
  } finally {
    clearTimeout(timer);
  }
}

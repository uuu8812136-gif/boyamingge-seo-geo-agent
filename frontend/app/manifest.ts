import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: '博雅敏格门窗 | 系统门窗与旧窗改造',
    short_name: '博雅敏格',
    description: '博雅敏格门窗——专注系统门窗、隔音门窗、旧窗改造、防盗门安装，全国多城上门测量。',
    start_url: '/',
    display: 'standalone',
    background_color: '#f7f5f2',
    theme_color: '#c45c26',
    icons: [
      { src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' },
    ],
  };
}

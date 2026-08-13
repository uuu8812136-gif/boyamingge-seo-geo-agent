import './globals.css';
import type { Metadata } from 'next';
import { SITE } from '@/lib/site';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost';

export const metadata: Metadata = {
  title: {
    default: `${SITE.brandFull} | 系统门窗与旧窗改造`,
    template: '%s | 博雅敏格',
  },
  description: SITE.description,
  metadataBase: new URL(siteUrl),
  openGraph: {
    type: 'website',
    siteName: SITE.brandFull,
    title: `${SITE.brandFull} | 系统门窗与旧窗改造`,
    description: SITE.description,
    url: siteUrl,
  },
  twitter: {
    card: 'summary_large_image',
    title: `${SITE.brandFull} | 系统门窗与旧窗改造`,
    description: SITE.description,
  },
};

import FloatingCustomerService from '@/components/FloatingCustomerService';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        {children}
        <FloatingCustomerService />
      </body>
    </html>
  );
}

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import BookingButton from '@/components/BookingButton';
import BrandMark from '@/components/BrandMark';
import CitySwitcher from '@/components/CitySwitcher';
import { SITE } from '@/lib/site';

const NAV = [
  { href: '/#services', label: '产品服务', match: 'services' },
  { href: '/#process', label: '服务流程', match: 'process' },
  { href: '/#faq', label: '常见问题', match: 'faq' },
];

type Props = {
  variant?: 'default' | 'overlay';
};

export default function Header({ variant = 'default' }: Props) {
  const pathname = usePathname();
  const isHome = pathname === '/';
  const isAdmin = pathname.startsWith('/admin');
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  if (isAdmin) return null;

  const overlayMode = variant === 'overlay' && !scrolled;

  return (
    <header className={`site-header ${overlayMode ? 'site-header--overlay' : 'site-header--solid'}`}>
      <div className="container header-inner">
        <Link href="/" className="logo">
          <BrandMark className="logo-badge" />
          <span className="logo-copy">
            <strong>{SITE.brandFull}</strong>
            <small>系统门窗 · 本地安装</small>
          </span>
        </Link>

        <button
          type="button"
          className="nav-toggle"
          aria-expanded={menuOpen}
          aria-controls="site-nav"
          aria-label={menuOpen ? '关闭菜单' : '打开菜单'}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav id="site-nav" className={`nav ${menuOpen ? 'nav-open' : ''}`} aria-label="主导航">
          <CitySwitcher />
          {NAV.map((item) => (
            <Link
              key={item.match}
              href={isHome ? `#${item.match}` : `/#${item.match}`}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </Link>
          ))}
          <Link href="/stores" onClick={() => setMenuOpen(false)}>城市门店</Link>
          <Link href="/articles" onClick={() => setMenuOpen(false)}>选购指南</Link>
        </nav>

        <div className="header-actions">
          <a href={`tel:${SITE.hotline.replace(/-/g, '')}`} className="header-phone">
            {SITE.hotlineDisplay}
          </a>
          <BookingButton label="预约测量" size="small" variant={overlayMode ? 'ghost' : 'primary'} />
        </div>
      </div>
      {menuOpen && (
        <button
          type="button"
          className="nav-backdrop"
          aria-hidden="true"
          tabIndex={-1}
          onClick={() => setMenuOpen(false)}
        />
      )}
    </header>
  );
}

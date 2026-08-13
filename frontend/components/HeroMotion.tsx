'use client';

import Image from 'next/image';
import { useEffect, useRef } from 'react';

type Props = {
  src: string;
  className?: string;
};

export default function HeroMotion({ src, className = '' }: Props) {
  const visualRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const visual = visualRef.current;
    const image = imageRef.current;
    if (!visual || !image) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return;

    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const y = window.scrollY;
        const limit = visual.offsetHeight || 1;
        const progress = Math.min(y / limit, 1);
        image.style.transform = `translate3d(0, ${y * 0.22}px, 0) scale(${1 + progress * 0.03})`;
      });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  return (
    <div ref={visualRef} className={`hero-banner-visual ${className}`} aria-hidden>
      <div ref={imageRef} className="hero-banner-parallax">
        <Image src={src} alt="" fill priority className="hero-banner-bg" sizes="100vw" />
      </div>
      <div className="hero-banner-shade" />
      <div className="hero-light-leak" />
    </div>
  );
}

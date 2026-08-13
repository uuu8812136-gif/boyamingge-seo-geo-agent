'use client';

import { useEffect, useState } from 'react';

const TYPE_START = 280;
const CHAR_INTERVAL = 120;

export default function HomeIntro({ brand }: { brand: string }) {
  const [typed, setTyped] = useState('');
  const [lifting, setLifting] = useState(false);
  const [done, setDone] = useState(false);
  const [cursorVisible, setCursorVisible] = useState(true);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const seen = window.sessionStorage.getItem('boyamingge-home-intro-seen');

    if (reduceMotion || seen) {
      setDone(true);
      return;
    }

    const timers: number[] = [];

    [...brand].forEach((_, index) => {
      timers.push(
        window.setTimeout(() => {
          setTyped(brand.slice(0, index + 1));
        }, TYPE_START + index * CHAR_INTERVAL),
      );
    });

    const liftAt = TYPE_START + brand.length * CHAR_INTERVAL + 520;
    timers.push(window.setTimeout(() => setCursorVisible(false), liftAt - 120));
    timers.push(window.setTimeout(() => setLifting(true), liftAt));
    timers.push(
      window.setTimeout(() => {
        window.sessionStorage.setItem('boyamingge-home-intro-seen', 'true');
        setDone(true);
      }, liftAt + 1150),
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [brand]);

  if (done) return null;

  return (
    <div className={`home-intro ${lifting ? 'home-intro--lifting' : ''}`} aria-hidden="true">
      <div className="home-intro-word">
        <span>{typed}</span>
        {cursorVisible && <i />}
      </div>
      <p>系统门窗 · 本地安装</p>
    </div>
  );
}

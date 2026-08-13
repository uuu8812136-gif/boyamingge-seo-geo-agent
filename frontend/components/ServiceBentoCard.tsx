'use client';

import { useRef, type MouseEvent } from 'react';

type Props = {
  index: number;
  name: string;
  pain: string;
};

export default function ServiceBentoCard({ index, name, pain }: Props) {
  const cardRef = useRef<HTMLElement>(null);

  function handleMove(event: MouseEvent<HTMLElement>) {
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    card.style.setProperty('--tilt-x', `${y * -6}deg`);
    card.style.setProperty('--tilt-y', `${x * 6}deg`);
    card.style.setProperty('--glare-x', `${(event.clientX - rect.left) / rect.width * 100}%`);
    card.style.setProperty('--glare-y', `${(event.clientY - rect.top) / rect.height * 100}%`);
  }

  function handleLeave() {
    const card = cardRef.current;
    if (!card) return;
    card.style.setProperty('--tilt-x', '0deg');
    card.style.setProperty('--tilt-y', '0deg');
  }

  return (
    <article
      ref={cardRef}
      className="bento-card bento-card--interactive"
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
    >
      <div className="bento-window-frame" aria-hidden>
        <span className="bento-sash bento-sash-left" />
        <span className="bento-sash bento-sash-right" />
        <span className="bento-mullion bento-mullion-v" />
        <span className="bento-mullion bento-mullion-h" />
      </div>
      <span className="bento-num">{String(index + 1).padStart(2, '0')}</span>
      <h3>{name}</h3>
      <p>{pain}</p>
      <span className="bento-glare" aria-hidden />
    </article>
  );
}

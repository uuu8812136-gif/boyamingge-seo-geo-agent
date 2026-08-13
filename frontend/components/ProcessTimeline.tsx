'use client';

import { useEffect, useRef } from 'react';

type Step = {
  step: string;
  title: string;
  desc: string;
};

export default function ProcessTimeline({ steps }: { steps: Step[] }) {
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          track.classList.add('timeline--active');
          observer.disconnect();
        }
      },
      { threshold: 0.25 },
    );

    observer.observe(track);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={trackRef} className="timeline">
      {steps.map((item, index) => (
        <div key={item.step} className="timeline-step" style={{ '--step-index': index } as React.CSSProperties}>
          <div className="timeline-marker">
            <span>{item.step}</span>
            {index < steps.length - 1 && <i aria-hidden />}
          </div>
          <div className="timeline-body">
            <h3>{item.title}</h3>
            <p>{item.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

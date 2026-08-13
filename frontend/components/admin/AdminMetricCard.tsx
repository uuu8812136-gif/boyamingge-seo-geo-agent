'use client';

import { useCountUp } from '@/hooks/useCountUp';

type Props = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: 'default' | 'warn' | 'ok' | 'info';
  index?: number;
};

export default function AdminMetricCard({ label, value, hint, tone = 'default', index = 0 }: Props) {
  const numeric = typeof value === 'number' ? value : null;
  const animated = useCountUp(numeric ?? 0);
  const display = numeric !== null ? animated : value;

  return (
    <article
      className={`admin-kpi admin-kpi--${tone}`}
      style={{ '--stagger': `${index * 45}ms` } as React.CSSProperties}
    >
      <span className="admin-kpi-label">{label}</span>
      <strong className="admin-kpi-value">{display}</strong>
      {hint && <span className="admin-kpi-hint">{hint}</span>}
    </article>
  );
}

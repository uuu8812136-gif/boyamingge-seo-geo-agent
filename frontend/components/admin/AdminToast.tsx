'use client';

import { useEffect } from 'react';

type Props = {
  message: string;
  kind?: 'success' | 'error' | 'info';
  onDismiss: () => void;
};

export default function AdminToast({ message, kind = 'info', onDismiss }: Props) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, 4200);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div className={`admin-toast admin-toast--${kind}`} role="status">
      <span className="admin-toast-dot" aria-hidden />
      <p>{message}</p>
      <button type="button" className="admin-toast-close" aria-label="关闭" onClick={onDismiss}>
        ×
      </button>
    </div>
  );
}

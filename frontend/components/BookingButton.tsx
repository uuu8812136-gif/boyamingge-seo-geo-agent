'use client';

import { useEffect, useId, useState } from 'react';
import { createPortal } from 'react-dom';
import LeadForm from './LeadForm';

type Props = {
  label?: string;
  city?: string;
  variant?: 'primary' | 'outline' | 'text' | 'ghost';
  size?: 'normal' | 'small';
};

export default function BookingButton({
  label = '预约测量',
  city = '广州',
  variant = 'primary',
  size = 'normal',
}: Props) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const titleId = useId();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        className={`btn btn-${variant} ${size === 'small' ? 'btn-sm' : ''}`}
        onClick={() => setOpen(true)}
      >
        {label}
      </button>

      {open && mounted && createPortal(
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setOpen(false)}>
          <div
            className="booking-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="modal-close" type="button" aria-label="关闭预约窗口" onClick={() => setOpen(false)}>
              ×
            </button>
            <div className="booking-modal-head">
              <span>上门测量</span>
              <h2 id={titleId}>留下信息，门店确认时间</h2>
              <p>提交后工作人员会先电话沟通需求，再安排本地工程师上门。</p>
            </div>
            <LeadForm defaultCity={city} />
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}

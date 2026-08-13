'use client';

import { useEffect, useRef, useState } from 'react';
import { submitCityLead } from '@/lib/api';

type Props = {
  defaultCity?: string;
  compact?: boolean;
  cityId?: number;
  preferredStoreId?: number;
};

const INTERESTS = ['阳台封窗', '卧室隔音窗', '旧窗改造', '防盗门安装', '断桥铝门窗', '全屋门窗定制'];

function OptionPicker({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    window.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className={`option-picker ${open ? 'option-picker-open' : ''}`} ref={rootRef}>
      <span className="field-label">{label}</span>
      <button
        type="button"
        className="option-trigger"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((current) => !current)}
      >
        <span>{value}</span>
        <span className="option-chevron" aria-hidden />
      </button>
      {open && (
        <div className="option-panel" role="listbox">
          {options.map((option) => (
            <button
              type="button"
              key={option}
              role="option"
              aria-selected={option === value}
              className={option === value ? 'selected' : ''}
              onClick={() => {
                onChange(option);
                setOpen(false);
              }}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LeadForm({ defaultCity = '', compact = false, cityId, preferredStoreId }: Props) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState(defaultCity);
  const [interest, setInterest] = useState('阳台封窗');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [cityOptions, setCityOptions] = useState<string[]>(defaultCity ? [defaultCity] : []);

  // 优先从后端拉城市列表
  useEffect(() => {
    let cancelled = false;
    async function loadCities() {
      try {
        const res = await fetch('/api/v1/cities?active_only=true');
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        const apiNames: string[] = (data.items || []).map((c: any) => c.name);
        setCityOptions(apiNames);
        if (!city && apiNames.length > 0) setCity(apiNames[0]);
      } catch {
        // 后端不可用时不展示未经发布的城市。
      }
    }
    loadCities();
    return () => { cancelled = true; };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('loading');
    try {
      const result = await submitCityLead({
        name,
        phone,
        city_name: city,
        city_id: cityId,
        preferred_store_id: preferredStoreId,
        interest,
      });
      setStatus('success');
      const assignedInfo = result.assigned_store ? `已分配至${result.assigned_city || ''}${result.assigned_store}` : '';
      setMessage(assignedInfo || result.message || '提交成功，客服将尽快联系您');
      setName('');
      setPhone('');
    } catch {
      setStatus('error');
      setMessage('提交失败，请稍后重试或直接拨打 400 热线');
    }
  }

  return (
    <form className={`lead-form ${compact ? 'lead-form-compact' : ''}`} onSubmit={handleSubmit}>
      <div className="form-row">
        <label>
          姓名
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="您的姓名" />
        </label>
        <label>
          手机号
          <input value={phone} onChange={(e) => setPhone(e.target.value)} required placeholder="11位手机号" pattern="1[3-9]\d{9}" />
        </label>
      </div>
      <div className="form-row">
        {cityOptions.length > 0 ? (
          <OptionPicker label="城市" value={city || '请选择城市'} options={cityOptions} onChange={setCity} />
        ) : (
          <label>
            城市
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              required
              maxLength={64}
              placeholder="请输入所在城市"
              autoComplete="address-level2"
            />
          </label>
        )}
        <OptionPicker label="需求" value={interest} options={INTERESTS} onChange={setInterest} />
      </div>
      <button type="submit" className="btn btn-primary btn-block" disabled={status === 'loading'}>
        {status === 'loading' ? '提交中...' : '提交预约'}
      </button>
      {message && (
        <p className={`form-message ${status === 'success' ? 'success' : 'error'}`}>{message}</p>
      )}
    </form>
  );
}

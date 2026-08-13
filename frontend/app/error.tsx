'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('页面运行时错误:', error);
  }, [error]);

  return (
    <div
      style={{
        minHeight: '60vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        textAlign: 'center',
        fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
      }}
    >
      <div style={{ fontSize: 72, lineHeight: 1, marginBottom: 16 }}>⚠️</div>
      <h1 style={{ fontSize: 24, color: '#141210', marginBottom: 12 }}>页面出错了</h1>
      <p style={{ color: '#675f57', marginBottom: 24, maxWidth: 480 }}>
        抱歉，页面遇到了一些问题。您可以尝试重新加载，或返回首页继续浏览。
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <button
          onClick={() => reset()}
          style={{
            padding: '12px 24px',
            borderRadius: 999,
            border: '1px solid #cfc5b8',
            background: '#fff',
            color: '#141210',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          重试
        </button>
        <a
          href="/"
          style={{
            padding: '12px 24px',
            borderRadius: 999,
            background: 'linear-gradient(135deg, #ad4b20, #863717)',
            color: '#fff',
            fontWeight: 700,
            textDecoration: 'none',
          }}
        >
          返回首页
        </a>
      </div>
    </div>
  );
}

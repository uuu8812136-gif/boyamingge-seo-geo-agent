'use client';

export default function AdminLoadingBar({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="admin-loading-bar" role="status" aria-label="加载中">
      <span />
    </div>
  );
}

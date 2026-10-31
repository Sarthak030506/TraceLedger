import React from 'react';

export default function StatCard({ title, value, subtitle }) {
  return (
    <div className="rounded-card hairline-light bg-white p-6">
      <p className="label-mono text-muted-light">{title}</p>
      <p className="mt-4 text-[40px] font-medium leading-none tracking-[-0.03em] text-ink">{value}</p>
      {subtitle && <p className="mt-3 text-[13px] text-muted-light">{subtitle}</p>}
    </div>
  );
}

import React from 'react';

// Monochrome pills; colour appears only as a small dot so verdicts stay legible
// without breaking the page's colour discipline.
const STYLES = {
  verified:  { dot: 'bg-ok',     label: 'Verified intact' },
  confirmed: { dot: 'bg-ink',    label: 'Anchored on-chain' },
  tampered:  { dot: 'bg-bad',    label: 'Tampering detected' },
  failed:    { dot: 'bg-bad',    label: 'Anchor failed' },
  simulated: { dot: 'bg-warn',   label: 'Simulated · not on-chain', title: 'No blockchain configured: this batch was NOT anchored on-chain' },
  offline:   { dot: 'bg-warn',   label: 'Not verified · offline' },
  pending:   { dot: 'bg-ink/30', label: 'Pending' },
};

export default function StatusBadge({ status, tone = 'light' }) {
  const key = (status || '').toLowerCase();
  const s = STYLES[key] || { dot: 'bg-ink/30', label: status || 'Unknown' };
  const shell = tone === 'dark'
    ? 'border-white/15 text-paper/80'
    : 'border-black/10 bg-white text-ink';
  return (
    <span title={s.title} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[12px] font-medium ${shell}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

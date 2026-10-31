import React from 'react';
import { Link } from '../router';
import { LogoMark, Wordmark } from './brand';

const TABS = [
  { to: '/app', label: 'Overview' },
  { to: '/app/batches', label: 'Batches' },
  { to: '/app/verify', label: 'Verify' },
  { to: '/app/lab', label: 'Tamper lab' },
];

function connection(health) {
  if (!health) return { dot: 'bg-white/30', text: 'Connecting…' };
  if (health.is_fallback) return { dot: 'bg-warn', text: 'Backend offline · preview data' };
  if (health.anchor_mode === 'live' && health.blockchain_connected) return { dot: 'bg-ok', text: 'Live · MST testnet' };
  return { dot: 'bg-warn', text: `Mode: ${health.anchor_mode || 'unknown'}` };
}

export default function Navbar({ path, health }) {
  const active = path.replace(/\/+$/, '') || '/app';
  const conn = connection(health);

  return (
    <header className="sticky top-0 z-40 bg-ink/95 text-paper backdrop-blur">
      <div className="shell flex h-16 items-center justify-between gap-4">
        <Link to="/" className="shrink-0" aria-label="TraceLedger home">
          <LogoMark className="h-5 w-5 sm:hidden" />
          <Wordmark className="hidden sm:inline-flex" />
        </Link>

        <nav className="flex items-center gap-0.5 overflow-x-auto text-[14px] sm:gap-1" aria-label="Dashboard">
          {TABS.map((t) => {
            const isActive = active === t.to;
            return (
              <Link
                key={t.to}
                to={t.to}
                aria-current={isActive ? 'page' : undefined}
                className={`whitespace-nowrap rounded-full px-2.5 py-1.5 transition-colors sm:px-3.5 ${
                  isActive ? 'bg-white/10 text-paper' : 'text-paper/60 hover:text-paper'
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>

        <span className="hidden shrink-0 items-center gap-2 font-mono text-[11.5px] text-paper/60 md:inline-flex">
          <span className={`h-1.5 w-1.5 rounded-full ${conn.dot}`} />
          {conn.text}
        </span>
      </div>
    </header>
  );
}

import React from 'react';
import { Play, Check, Activity, Layers } from 'lucide-react';

/* All mockups are abstract and greyscale so they never compete with type. */

const short = (h) => `${h.slice(0, 6)}…${h.slice(-4)}`;

const EVENTS = [
  { src: 'auth-service', what: 'Sign-in succeeded for a***@corp.in', seq: 1041, hash: '9f3a1c7e22b04d6a8e5f1b2c3d4e5f60718293a4b5c6d7e8f9012ab34cd56ef7' },
  { src: 'iam', what: 'Role changed: editor → admin', seq: 1042, hash: '4b7e90d1aa63c2f5e81b07d94c3a2f6e5d8c7b6a5f4e3d2c1b0a998877665544' },
  { src: 'config-manager', what: 'session_timeout 30 → 15', seq: 1043, hash: 'c1d8e2f3a4b5c6d7e8f90a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d' },
];

function TreeArt() {
  // Leaves → root, drawn as hairlines; desaturated to sit behind floating UI
  const leaves = [90, 210, 330, 450, 570, 690, 810, 930];
  const mids = [150, 390, 630, 870];
  const tops = [270, 750];
  return (
    <svg viewBox="0 0 1020 420" className="h-full w-full" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <radialGradient id="tl-glow" cx="50%" cy="20%" r="70%">
          <stop offset="0%" stopColor="#3a3a3a" />
          <stop offset="100%" stopColor="#0d0d0d" />
        </radialGradient>
      </defs>
      <rect width="1020" height="420" fill="url(#tl-glow)" />
      <g stroke="rgba(255,255,255,0.16)" strokeWidth="1.2" fill="none">
        {mids.map((x, i) => (
          <React.Fragment key={x}>
            <path d={`M${leaves[i * 2]} 330 C ${leaves[i * 2]} 290, ${x} 300, ${x} 250`} />
            <path d={`M${leaves[i * 2 + 1]} 330 C ${leaves[i * 2 + 1]} 290, ${x} 300, ${x} 250`} />
          </React.Fragment>
        ))}
        {tops.map((x, i) => (
          <React.Fragment key={x}>
            <path d={`M${mids[i * 2]} 250 C ${mids[i * 2]} 210, ${x} 220, ${x} 170`} />
            <path d={`M${mids[i * 2 + 1]} 250 C ${mids[i * 2 + 1]} 210, ${x} 220, ${x} 170`} />
          </React.Fragment>
        ))}
        <path d="M270 170 C 270 130, 510 140, 510 95" />
        <path d="M750 170 C 750 130, 510 140, 510 95" />
      </g>
      {leaves.map((x) => <rect key={x} x={x - 26} y="330" width="52" height="22" rx="6" fill="#1c1c1c" stroke="rgba(255,255,255,0.14)" />)}
      {mids.map((x) => <circle key={x} cx={x} cy="250" r="7" fill="#262626" stroke="rgba(255,255,255,0.22)" />)}
      {tops.map((x) => <circle key={x} cx={x} cy="170" r="8" fill="#2a2a2a" stroke="rgba(255,255,255,0.28)" />)}
      <circle cx="510" cy="88" r="13" fill="#f5f4f0" opacity="0.92" />
      <circle cx="510" cy="88" r="24" fill="none" stroke="rgba(245,244,240,0.25)" />
    </svg>
  );
}

export function HeroPanel({ health }) {
  const live = health && !health.is_fallback && health.status === 'ok';
  const latest = live ? health.latest_batch_id : 128;
  return (
    <div className="relative mx-auto max-w-[1180px] rounded-[22px] border border-white/[0.09] bg-white/[0.03] p-1.5 sm:p-2">
      <div className="relative aspect-[16/10] overflow-hidden rounded-[18px] bg-ink-900 sm:aspect-[16/8]">
        <TreeArt />

        {/* Play chip */}
        <a href="#how" className="glass absolute left-1/2 top-[44%] flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full px-4 py-2 text-[13px] text-paper transition-colors hover:bg-white/10">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-paper text-ink"><Play className="h-3 w-3 fill-current" /></span>
          How it works
        </a>

        {/* Floating ingested-event cards */}
        <div className="absolute left-3 top-4 hidden w-[300px] space-y-3 sm:block">
          {EVENTS.map((e, i) => (
            <div key={e.seq} className={`glass rounded-2xl p-3.5 ${i === 1 ? 'ml-8 animate-float-slow' : 'animate-float'}`}
              style={{ animationDelay: `${i * 0.8}s` }}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-muted-dark">{e.src}</span>
                <span className="font-mono text-[11px] text-muted-dark">seq {e.seq}</span>
              </div>
              <p className="mt-1 text-[13px] text-paper/90">{e.what}</p>
              <p className="mt-2 font-mono text-[11px] text-white/40">sha256 {short(e.hash)}</p>
            </div>
          ))}
        </div>

        {/* Activity sidebar */}
        <div className="absolute bottom-3 right-3 top-3 hidden w-[260px] flex-col rounded-2xl border border-white/[0.08] bg-ink/85 p-3 backdrop-blur md:flex">
          <div className="flex items-center gap-4 border-b border-white/[0.08] pb-2.5 text-[13px]">
            <span className="flex items-center gap-1.5 text-paper"><Activity className="h-3.5 w-3.5" /> Activity</span>
            <span className="flex items-center gap-1.5 text-muted-dark"><Layers className="h-3.5 w-3.5" /> Batches</span>
          </div>
          <div className="mt-3 space-y-2.5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2.5">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-paper">Batch #{Math.max(1, latest - i)}</span>
                  <span className="flex items-center gap-1 font-mono text-[10px] text-muted-dark">
                    <span className="h-1.5 w-1.5 rounded-full bg-paper/70" /> anchored
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-[70%] rounded bg-white/10" />
                <div className="mt-1.5 h-1.5 w-[45%] rounded bg-white/[0.06]" />
              </div>
            ))}
          </div>
          <div className="mt-auto rounded-xl border border-white/[0.08] p-2.5">
            <p className="label-mono text-muted-dark">Last verification</p>
            <p className="mt-1 flex items-center gap-1.5 text-[13px] text-paper">
              <Check className="h-3.5 w-3.5" /> Root matches chain
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Feature row illustrations (light, beige cards) ───────────────────────── */

function BeigeCard({ children }) {
  return (
    <div className="relative aspect-[6/5] overflow-hidden rounded-card hairline-light bg-paper-card">
      {children}
    </div>
  );
}

export function SealIllustration() {
  return (
    <BeigeCard>
      <div className="absolute left-6 right-6 top-8 rounded-2xl hairline-light bg-white p-5 shadow-[0_1px_0_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between">
          <span className="label-mono text-muted-light">event · authentication</span>
          <span className="font-mono text-[11px] text-muted-light">seq 1041</span>
        </div>
        <div className="mt-4 space-y-2.5 font-mono text-[12px]">
          <div className="flex justify-between"><span className="text-muted-light">user</span><span className="text-ink">alice</span></div>
          <div className="flex justify-between"><span className="text-muted-light">email</span><span className="text-ink">a***@example.com</span></div>
          <div className="flex justify-between"><span className="text-muted-light">ip</span><span className="text-ink">192.168.1.xxx</span></div>
          <div className="flex justify-between"><span className="text-muted-light line-through decoration-ink/40">password</span><span className="rounded bg-ink px-1.5 text-[10px] text-paper">DROPPED</span></div>
        </div>
      </div>
      <div className="absolute bottom-6 left-6 right-6 flex items-center gap-2 rounded-xl bg-ink px-3.5 py-2.5 font-mono text-[11px] text-paper">
        <span className="text-muted-dark">sha256</span>
        <span className="truncate">9f3a1c7e22b04d6a8e5f1b2c3d4e5f60718293a4</span>
      </div>
    </BeigeCard>
  );
}

export function TreeIllustration() {
  const L = [52, 116, 180, 244];
  return (
    <BeigeCard>
      <svg viewBox="0 0 296 246" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g stroke="#bdbab0" strokeWidth="1.2" fill="none">
          <path d="M52 180 L84 120 M116 180 L84 120 M180 180 L212 120 M244 180 L212 120 M84 120 L148 62 M212 120 L148 62" />
        </g>
        {L.map((x, i) => (
          <g key={x}>
            <rect x={x - 24} y="180" width="48" height="26" rx="7" fill="#fff" stroke="#d6d3c8" />
            <text x={x} y="197" textAnchor="middle" fontFamily="Geist Mono, monospace" fontSize="10" fill="#555">h{i + 1}</text>
          </g>
        ))}
        {[84, 212].map((x) => <circle key={x} cx={x} cy="120" r="9" fill="#fff" stroke="#bdbab0" />)}
        <circle cx="148" cy="56" r="15" fill="#0a0a0a" />
        <text x="148" y="60" textAnchor="middle" fontFamily="Geist Mono, monospace" fontSize="9" fill="#f5f4f0">root</text>
      </svg>
    </BeigeCard>
  );
}

export function AnchorIllustration() {
  return (
    <BeigeCard>
      <div className="absolute inset-x-6 top-1/2 flex -translate-y-1/2 items-center">
        {[126, 127, 128].map((n, i) => (
          <React.Fragment key={n}>
            <div className={`flex-1 rounded-2xl hairline-light p-3.5 ${i === 2 ? 'bg-ink text-paper' : 'bg-white text-ink'}`}>
              <p className={`label-mono ${i === 2 ? 'text-muted-dark' : 'text-muted-light'}`}>batch</p>
              <p className="mt-1 text-[22px] font-medium tracking-[-0.02em]">#{n}</p>
              <div className={`mt-3 h-1.5 rounded ${i === 2 ? 'bg-white/25' : 'bg-black/10'}`} />
              <div className={`mt-1.5 h-1.5 w-2/3 rounded ${i === 2 ? 'bg-white/15' : 'bg-black/[0.06]'}`} />
            </div>
            {i < 2 && <div className="h-px w-4 shrink-0 bg-ink/30 sm:w-6" />}
          </React.Fragment>
        ))}
      </div>
      <p className="absolute bottom-5 left-6 font-mono text-[11px] text-muted-light">previous_root → merkle_root → previous_root</p>
    </BeigeCard>
  );
}

/* ── Dark band: verification terminal ─────────────────────────────────────── */

export function TerminalMock() {
  const steps = [
    'Recomputed 5 record hashes from raw events',
    'Rebuilt Merkle root 9f3a…56ef',
    'Read commitment for batch #128 from contract',
    'Root, range and count match on-chain values',
    'Ed25519 signature valid for sidecar key',
  ];
  return (
    <div className="overflow-hidden rounded-card border border-white/[0.09] bg-ink-900">
      <div className="flex items-center justify-between border-b border-white/[0.07] px-4 py-3">
        <span className="flex items-center gap-2 text-[13px] text-paper">
          <span className="h-2 w-2 rounded-full bg-paper/70" /> Auditor terminal
        </span>
        <span className="font-mono text-[11px] text-muted-dark">~/evidence</span>
      </div>
      <div className="space-y-3 p-4 font-mono text-[12.5px]">
        <p className="text-muted-dark">&gt; <span className="text-paper">POST /api/batches/128/verify</span></p>
        <p className="text-paper/80">verification_source <span className="text-muted-dark">·</span> provided_records</p>
        <div className="divide-y divide-white/[0.06] rounded-xl border border-white/[0.07]">
          {steps.map((s) => (
            <div key={s} className="flex items-center gap-3 px-3 py-2.5">
              <span className="grid h-4 w-4 shrink-0 place-items-center rounded border border-white/30">
                <Check className="h-3 w-3 text-paper" />
              </span>
              <span className="text-paper/70">{s}</span>
            </div>
          ))}
        </div>
        <p className="text-paper">verified: <span className="rounded bg-paper px-1.5 text-ink">true</span></p>
      </div>
    </div>
  );
}

/* ── Bento ────────────────────────────────────────────────────────────────── */

export function TamperBento() {
  const rows = [
    { seq: 1041, label: 'Sign-in succeeded', state: 'ok' },
    { seq: 1042, label: 'Role changed: editor → admin', state: 'altered', note: 'details rewritten' },
    { seq: 1043, label: 'Export of 120 rows', state: 'deleted', note: 'record removed' },
    { seq: 1045, label: 'Config change', state: 'reordered', note: 'appears before 1044' },
    { seq: 1045, label: 'Config change', state: 'duplicated', note: 'replayed' },
  ];
  return (
    <div className="grid h-full grid-cols-1 items-start gap-3 p-5 sm:grid-cols-[1.15fr_1fr] sm:p-6">
      <div className="rounded-2xl hairline-light bg-white p-4">
        <p className="label-mono text-muted-light">Retained logs</p>
        <div className="mt-3 space-y-2">
          {rows.map((r, i) => (
            <div key={i} className={`flex items-center gap-3 rounded-lg px-2.5 py-2 text-[12.5px] ${r.state === 'ok' ? '' : 'bg-paper'}`}>
              <span className="w-10 font-mono text-[11px] text-muted-light">{r.seq}</span>
              <span className={`flex-1 truncate ${r.state === 'deleted' ? 'text-muted-light line-through' : 'text-ink'}`}>{r.label}</span>
              {r.state !== 'ok' && <span className="rounded-full border border-ink/15 px-2 py-0.5 font-mono text-[10px] text-ink">{r.state}</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl bg-ink p-4 text-paper">
        <p className="label-mono text-muted-dark">Verifier report</p>
        <ul className="mt-3 space-y-2.5 font-mono text-[11.5px] leading-[1.45] text-paper/75">
          <li>✕ 1042 hash mismatch</li>
          <li>✕ 1043 missing</li>
          <li>✕ 1045 before 1044</li>
          <li>✕ 1045 duplicated</li>
          <li>✕ root ≠ on-chain</li>
        </ul>
        <p className="mt-5 border-t border-white/10 pt-3 font-mono text-[12px]">verified: false</p>
      </div>
    </div>
  );
}

export function CodeBento() {
  return (
    <div className="p-5 sm:p-6">
      <div className="rounded-2xl hairline-light bg-white">
        <div className="flex items-center gap-2 border-b border-black/[0.06] px-3.5 py-2.5 font-mono text-[11px] text-muted-light">
          <span className="h-1.5 w-1.5 rounded-full bg-ink/40" /> sidecar :8001
        </div>
        <pre className="overflow-x-auto px-3.5 py-3 font-mono text-[11.5px] leading-[1.7] text-ink">
{`POST /events
X-API-Key: ••••••••
{ "event_type": "authentication",
  "source": "auth-service",
  "details": { "user": "alice" } }`}
        </pre>
        <div className="flex items-center justify-between border-t border-black/[0.06] px-3.5 py-2.5 text-[11px]">
          <span className="font-mono text-muted-light">→ seq 1046 · sha256 7c1e…a09b</span>
          <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[10px] text-paper">200</span>
        </div>
      </div>
    </div>
  );
}

export function ChainBento() {
  return (
    <div className="relative p-5 sm:p-6">
      {/* Opaque cards stacked back-to-front; depth comes from scale and text tone, not opacity */}
      {[0, 1, 2].map((i) => (
        <div key={i} className={`relative rounded-2xl hairline-light px-4 py-3 ${i === 2 ? 'bg-white' : 'bg-[#f7f6f2]'}`}
          style={{ marginTop: i ? -34 : 0, transform: `scale(${1 - (2 - i) * 0.045})`, zIndex: i }}>
          <div className="flex items-center justify-between">
            <span className={`text-[14px] font-medium ${i === 2 ? 'text-ink' : 'text-ink/45'}`}>Batch #{126 + i}</span>
            <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${i === 2 ? 'border-ink/15 text-ink' : 'border-ink/10 text-ink/40'}`}>block 6,734,{700 + i * 3}</span>
          </div>
          <p className="mt-1 font-mono text-[11px] text-muted-light">prev {['0000…0000', 'fa8c…91d2', '3be0…77ac'][i]}</p>
        </div>
      ))}
    </div>
  );
}

export function CtaWatermark() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true"
      className="pointer-events-none absolute -right-[12%] top-1/2 h-[150%] -translate-y-1/2 text-white/[0.045] sm:-right-[6%]">
      <path d="M6 9.5h20M16 9.5v13" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <circle cx="24" cy="23" r="3" fill="currentColor" />
    </svg>
  );
}

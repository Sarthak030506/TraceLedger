import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="display text-[44px] text-ink sm:text-[56px]">{title}</h1>
        {subtitle && <p className="mt-3 max-w-[560px] text-[16px] leading-[1.55] text-muted-light">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ className = '', children }) {
  return <div className={`rounded-card hairline-light bg-white ${className}`}>{children}</div>;
}

export function Notice({ tone = 'warn', children }) {
  const dot = { warn: 'bg-warn', bad: 'bg-bad', ok: 'bg-ok', info: 'bg-ink/40' }[tone];
  return (
    <div className="flex items-start gap-3 rounded-2xl hairline-light bg-white px-4 py-3 text-[14px] text-ink">
      <span className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
      <div className="leading-[1.55]">{children}</div>
    </div>
  );
}

export function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false);
  if (!text) return null;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        navigator.clipboard?.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      aria-label="Copy to clipboard"
      className={`text-muted-light transition-colors hover:text-ink ${className}`}
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

export function shortHash(h = '', n = 8) {
  if (!h) return '—';
  const raw = h.startsWith('0x') ? h.slice(2) : h;
  if (raw.length <= n * 2 + 1) return h;
  return `${h.startsWith('0x') ? '0x' : ''}${raw.slice(0, n)}…${raw.slice(-n)}`;
}

export function HashField({ label, value, dark = false, onPaper = false }) {
  const surface = dark ? 'bg-ink text-paper' : onPaper ? 'hairline-light bg-white text-ink' : 'bg-paper text-ink';
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className={`label-mono ${dark ? 'text-muted-dark' : 'text-muted-light'}`}>{label}</span>
        <CopyButton text={value} />
      </div>
      <div className={`break-all rounded-xl px-3 py-2.5 font-mono text-[12px] ${surface}`}>
        {value || '—'}
      </div>
    </div>
  );
}

const SOURCE_LABEL = {
  provided_records: 'Raw records supplied by the caller were re-hashed',
  sidecar_store: 'Raw records from the sidecar store were re-hashed',
  leaf_hashes: 'Only stored leaf hashes were checked — raw logs were not available',
  none: 'No records were available to check',
  local_browser: 'Checked in your browser only — not against the chain',
};

/** Shows exactly what a verification did and did not establish. */
export function Verdict({ result, batchId }) {
  if (!result) return null;
  const v = result.verified;
  const headline = v === true ? 'Integrity verified' : v === false ? 'Tampering detected' : 'Not verified';
  const dot = v === true ? 'bg-ok' : v === false ? 'bg-bad' : 'bg-warn';

  const facts = [
    result.verification_source && ['Evidence', SOURCE_LABEL[result.verification_source] || result.verification_source],
    result.onchain_checked !== undefined && ['On-chain check', result.onchain_checked ? 'Commitment re-read from the contract' : 'Not checked against the chain'],
    result.signature_valid !== undefined && result.signature_valid !== null && ['Signature', result.signature_valid ? 'Valid Ed25519 signature' : 'Invalid or missing'],
  ].filter(Boolean);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start justify-between gap-4 bg-ink px-6 py-5 text-paper">
        <div>
          <p className="label-mono text-muted-dark">{batchId ? `Batch #${batchId}` : 'Result'}</p>
          <p className="mt-2 flex items-center gap-2.5 text-[26px] font-medium tracking-[-0.02em]">
            <span className={`h-2.5 w-2.5 rounded-full ${dot}`} /> {headline}
          </p>
          {result.message && <p className="mt-1.5 text-[14px] text-muted-dark">{result.message}</p>}
        </div>
      </div>

      <div className="space-y-5 p-6">
        {facts.length > 0 && (
          <dl className="grid gap-3 sm:grid-cols-3">
            {facts.map(([k, val]) => (
              <div key={k} className="rounded-xl bg-paper px-3.5 py-3">
                <dt className="label-mono text-muted-light">{k}</dt>
                <dd className="mt-1.5 text-[13px] leading-[1.45] text-ink">{val}</dd>
              </div>
            ))}
          </dl>
        )}

        {(result.expected_root || result.computed_root) && (
          <div className="grid gap-4 md:grid-cols-2">
            <HashField label="Expected root (anchored)" value={result.expected_root} />
            <HashField label="Computed root (from records)" value={result.computed_root} dark={v === false} />
          </div>
        )}

        {result.errors?.length > 0 && (
          <div>
            <p className="label-mono text-muted-light">Findings ({result.errors.length})</p>
            <ul className="mt-2 divide-y divide-black/[0.06] rounded-xl hairline-light">
              {result.errors.map((err, i) => (
                <li key={i} className="flex gap-3 px-3.5 py-2.5 font-mono text-[12px] leading-[1.5] text-ink">
                  <span className="text-bad">✕</span>
                  <span className="break-words">{err}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}

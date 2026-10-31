import React, { useEffect, useState } from 'react';
import { X, ShieldCheck, RefreshCw } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { HashField, Verdict } from './ui';
import { verifyBatch } from '../services/api';

export default function BatchDetailModal({ batch, onClose, onVerified }) {
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!batch) return null;

  const verify = async () => {
    setVerifying(true);
    setResult(null);
    setError(null);
    try {
      const res = await verifyBatch(batch.batch_id);
      setResult(res);
      onVerified?.(res);
    } catch (err) {
      setError(err.message || 'Verification request failed');
    } finally {
      setVerifying(false);
    }
  };

  const status = result
    ? (result.verified === true ? 'verified' : result.verified === false ? 'tampered' : 'offline')
    : batch.status;

  const facts = [
    ['Records', `${batch.record_count}`],
    ['Sequence', `${batch.first_sequence} → ${batch.last_sequence}`],
    ['Block', batch.block_number ? `${batch.block_number}` : '—'],
    ['Anchored', new Date(batch.timestamp ? batch.timestamp * 1000 : batch.created_at).toLocaleDateString()],
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex animate-fade-in items-end justify-center bg-ink/60 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="batch-title"
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-[24px] bg-paper text-ink sm:rounded-[24px]"
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-black/[0.06] bg-paper/95 px-6 py-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <h2 id="batch-title" className="text-[20px] font-medium tracking-[-0.02em]">Batch #{batch.batch_id}</h2>
            <StatusBadge status={status} />
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-full p-1.5 text-muted-light hover:bg-black/5 hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 p-6">
          {result && <Verdict result={result} batchId={batch.batch_id} />}
          {error && <p className="text-[14px] text-bad">{error}</p>}

          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {facts.map(([k, v]) => (
              <div key={k} className="rounded-xl hairline-light bg-white px-3.5 py-3">
                <dt className="label-mono text-muted-light">{k}</dt>
                <dd className="mt-1.5 truncate font-mono text-[13px] text-ink" title={v}>{v}</dd>
              </div>
            ))}
          </dl>

          <HashField onPaper label="Merkle root" value={batch.merkle_root} />
          <HashField onPaper label="Previous batch root" value={batch.previous_root} />
          <HashField onPaper label="Transaction hash" value={batch.transaction_hash} />
          {batch.signature && <HashField onPaper label="Ed25519 signature" value={batch.signature} />}
          {batch.status === 'simulated' && (
            <p className="text-[13px] text-muted-light">
              This batch was created without a blockchain configured. Its transaction hash is simulated and not on any chain.
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-black/[0.06] px-6 py-4">
          <button type="button" onClick={onClose} className="btn-ghost-light">Close</button>
          <button type="button" onClick={verify} disabled={verifying} className="btn-ink">
            {verifying ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            {verifying ? 'Recomputing…' : 'Verify integrity'}
          </button>
        </div>
      </div>
    </div>
  );
}

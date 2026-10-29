import React, { useState } from 'react';
import { X, Copy, Check, ExternalLink, ShieldCheck, AlertOctagon, Terminal } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { verifyBatch } from '../services/api';

export default function BatchDetailModal({ batch, onClose, onVerified }) {
  const [copiedKey, setCopiedKey] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  if (!batch) return null;

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await verifyBatch(batch.batch_id);
      setVerifyResult(res);
      if (onVerified) onVerified(res);
    } catch (err) {
      setVerifyResult({
        verified: false,
        message: err.message || 'Verification request failed',
        errors: [err.message],
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-700/80 shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-5">
          <div className="flex items-center gap-3">
            <div className="px-2.5 py-1 rounded bg-cyan-500/10 text-cyan-400 font-mono text-sm font-bold border border-cyan-500/20">
              Batch #{batch.batch_id}
            </div>
            <StatusBadge status={verifyResult ? (verifyResult.verified ? 'verified' : 'tampered') : batch.status} />
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Verification Alert Banner if checked */}
        {verifyResult && (
          <div
            className={`p-4 rounded-xl border mb-5 flex items-start gap-3 ${
              verifyResult.verified
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-950/40 border-rose-500/40 text-rose-300 glow-red'
            }`}
          >
            {verifyResult.verified ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5 animate-bounce" />
            )}
            <div className="text-xs">
              <p className="font-semibold text-sm">
                {verifyResult.verified ? 'Cryptographic Proof Verified' : 'Integrity Mismatch Detected!'}
              </p>
              <p className="text-slate-300 mt-0.5">{verifyResult.message}</p>
              {verifyResult.errors?.length > 0 && (
                <ul className="mt-2 list-disc list-inside space-y-1 text-rose-300/90 font-mono">
                  {verifyResult.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* Commitment Metadata Grid */}
        <div className="space-y-4 text-xs">
          
          {/* Merkle Root */}
          <div>
            <div className="text-slate-400 mb-1 flex items-center justify-between">
              <span>Anchored Merkle Root (Commitment)</span>
              <button
                onClick={() => copyToClipboard(batch.merkle_root, 'root')}
                className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
              >
                {copiedKey === 'root' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                Copy
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-navy-900 border border-slate-800 font-mono text-cyan-300 break-all">
              {batch.merkle_root}
            </div>
          </div>

          {/* Previous Root */}
          <div>
            <div className="text-slate-400 mb-1 flex items-center justify-between">
              <span>Previous Batch Root (Chain Parent)</span>
              <button
                onClick={() => copyToClipboard(batch.previous_root, 'prev')}
                className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
              >
                {copiedKey === 'prev' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                Copy
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-navy-900 border border-slate-800 font-mono text-slate-300 break-all">
              {batch.previous_root}
            </div>
          </div>

          {/* Sequence & Record Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-navy-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Records</span>
              <span className="text-white font-mono font-bold text-sm">{batch.record_count} events</span>
            </div>
            <div className="p-3 rounded-lg bg-navy-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Sequence Range</span>
              <span className="text-white font-mono font-bold text-sm">#{batch.first_sequence} → #{batch.last_sequence}</span>
            </div>
            <div className="p-3 rounded-lg bg-navy-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">MST Block #</span>
              <span className="text-white font-mono font-bold text-sm">{batch.block_number || 'Simulated'}</span>
            </div>
            <div className="p-3 rounded-lg bg-navy-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Timestamp</span>
              <span className="text-white font-mono font-bold text-sm">
                {new Date(batch.timestamp ? batch.timestamp * 1000 : batch.created_at).toLocaleTimeString()}
              </span>
            </div>
          </div>

          {/* Transaction Hash */}
          <div>
            <div className="text-slate-400 mb-1 flex items-center justify-between">
              <span>MST Blockchain Transaction Hash</span>
              <button
                onClick={() => copyToClipboard(batch.transaction_hash, 'tx')}
                className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
              >
                {copiedKey === 'tx' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                Copy
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-navy-900 border border-slate-800 font-mono text-slate-300 break-all flex items-center justify-between">
              <span>{batch.transaction_hash || '0x...'}</span>
              <a
                href={`https://explorer.testnet.mst.org/tx/${batch.transaction_hash}`}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:text-cyan-300 shrink-0 ml-2"
                title="View on MST Block Explorer"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Ed25519 Signature */}
          {batch.signature && (
            <div>
              <div className="text-slate-400 mb-1">Sidecar Ed25519 Signature</div>
              <div className="p-2 rounded-lg bg-navy-900/80 border border-slate-800 font-mono text-slate-400 text-[11px] break-all max-h-16 overflow-y-auto">
                {batch.signature}
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-navy-950 shadow-md shadow-cyan-500/20 transition-all disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            {verifying ? 'Recomputing Merkle Tree...' : 'Verify Batch Integrity'}
          </button>
        </div>

      </div>
    </div>
  );
}


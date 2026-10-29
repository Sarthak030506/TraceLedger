import React, { useState } from 'react';
import {
  Play, Zap, ShieldAlert, ShieldCheck, RotateCcw,
  AlertTriangle, ChevronRight, Lock
} from 'lucide-react';
import { submitBatch, verifyBatch } from '../services/api';

// ── deterministic fake hash ──────────────────────────────────────────────────
function makeHash(seed) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) { h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0; }
  const hex = (Math.abs(h) >>> 0).toString(16).padStart(8, '0');
  return hex.repeat(8); // 64 chars
}

// ── initial sample events ────────────────────────────────────────────────────
const INITIAL_RECORDS = [
  { seq: 1, event_type: 'AUTH_SUCCESS', actor: 'alice@corp.com', resource: '/api/login',    details: 'IP 10.0.0.5' },
  { seq: 2, event_type: 'DATA_READ',   actor: 'alice@corp.com', resource: '/api/users',    details: 'returned 42 rows' },
  { seq: 3, event_type: 'DATA_WRITE',  actor: 'bob@corp.com',   resource: '/api/orders',   details: 'order_id=9981 modified' },
  { seq: 4, event_type: 'PRIV_ESCALATE',actor: 'bob@corp.com', resource: '/admin/roles',   details: 'added role=superuser' },
  { seq: 5, event_type: 'DATA_DELETE', actor: 'eve@corp.com',   resource: '/api/audit_log',details: 'deleted 120 rows' },
];

const STEPS = ['load', 'anchor', 'tamper', 'verify', 'done'];

const stepLabel = { load: 'Load Events', anchor: 'Anchor Batch', tamper: 'Simulate Tampering', verify: 'Run Verification', done: 'Result' };

export default function Demo() {
  const [step, setStep]           = useState('load');
  const [records, setRecords]     = useState(INITIAL_RECORDS);
  const [batch, setBatch]         = useState(null);
  const [tampered, setTampered]   = useState(false);
  const [result, setResult]       = useState(null);
  const [busy, setBusy]           = useState(false);
  const [errorMsg, setErrorMsg]   = useState(null);

  const reset = () => {
    setStep('load'); setRecords(INITIAL_RECORDS);
    setBatch(null); setTampered(false); setResult(null); setErrorMsg(null);
  };

  // Step 1 → 2: anchor
  const anchorBatch = async () => {
    setBusy(true); setErrorMsg(null);
    try {
      const hashes = records.map(r => makeHash(JSON.stringify(r)));
      const res = await submitBatch({ record_hashes: hashes, records });
      setBatch(res);
      setStep('tamper');
    } catch (e) {
      setErrorMsg(e.message);
    } finally { setBusy(false); }
  };

  // Step 2 → 3: tamper
  const simulateTamper = () => {
    setRecords(prev => prev.map(r =>
      r.seq === 5
        ? { ...r, details: '⚠️ [DEMO TAMPERED] deleted 0 rows' }
        : r
    ));
    setTampered(true);
    setStep('verify');
  };

  // Step 3 → 4: verify
  const runVerify = async () => {
    setBusy(true); setErrorMsg(null);
    try {
      // If backend available, call real verify endpoint
      if (batch?.batch_id) {
        const r = await verifyBatch(batch.batch_id);
        setResult(r);
      } else {
        // Fallback: local simulation — tampered ≠ original hashes
        const origHashes = INITIAL_RECORDS.map(r => makeHash(JSON.stringify(r)));
        const curHashes  = records.map(r => makeHash(JSON.stringify(r)));
        const mismatches = origHashes
          .map((h, i) => h !== curHashes[i] ? `Record seq=${i + 1}: hash mismatch (tampered)` : null)
          .filter(Boolean);
        setResult({
          verified: mismatches.length === 0,
          errors: mismatches,
          expected_root: makeHash(origHashes.join('')),
          computed_root: makeHash(curHashes.join('')),
          _simulated: true,
        });
      }
      setStep('done');
    } catch (e) {
      setErrorMsg(e.message);
    } finally { setBusy(false); }
  };

  const isVerified = result?.verified === true;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Demo</h1>
          <p className="text-gray-400 text-sm mt-1">
            End-to-end walkthrough: anchor a log batch, simulate tampering, run detection.
          </p>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-400 hover:text-white text-sm transition-all self-start"
        >
          <RotateCcw size={13} /> Reset Demo
        </button>
      </div>

      {/* SIMULATION WARNING */}
      <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-xs">
        <AlertTriangle size={15} className="flex-shrink-0 mt-0.5" />
        <span>
          <strong>DEMO SIMULATION</strong> — Tampering is simulated locally in the browser. No real data is modified.
          TraceLedger <em>detects</em> tampering; it does not prevent attacks.
        </span>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-1 text-xs">
        {STEPS.map((s, i) => (
          <React.Fragment key={s}>
            <span className={`px-2.5 py-1 rounded-full font-medium transition-colors ${
              step === s ? 'bg-cyan-500 text-navy-950' :
              STEPS.indexOf(step) > i ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
              'bg-white/5 text-gray-500'
            }`}>
              {stepLabel[s]}
            </span>
            {i < STEPS.length - 1 && <ChevronRight size={12} className="text-gray-600" />}
          </React.Fragment>
        ))}
      </div>

      {errorMsg && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Events table */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
          <p className="text-sm font-semibold text-white">Sample Security Events</p>
          {tampered && (
            <span className="text-xs bg-red-500/20 border border-red-500/30 text-red-300 px-2 py-0.5 rounded-full">
              ⚠ Record #5 tampered (DEMO)
            </span>
          )}
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              {['Seq', 'Event', 'Actor', 'Resource', 'Details'].map(h => (
                <th key={h} className="px-4 py-2 text-left text-gray-500 font-semibold uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {records.map(r => {
              const isTampered = tampered && r.seq === 5;
              return (
                <tr key={r.seq} className={isTampered ? 'bg-red-500/10' : ''}>
                  <td className={`px-4 py-2 font-mono font-bold ${isTampered ? 'text-red-400' : 'text-cyan-400'}`}>
                    {r.seq}
                  </td>
                  <td className="px-4 py-2 text-gray-300">{r.event_type}</td>
                  <td className="px-4 py-2 text-gray-400">{r.actor}</td>
                  <td className="px-4 py-2 font-mono text-gray-400">{r.resource}</td>
                  <td className={`px-4 py-2 ${isTampered ? 'text-red-300 font-semibold' : 'text-gray-500'}`}>
                    {r.details}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Anchored batch info */}
      {batch && (
        <div className="glass-panel rounded-xl p-5 space-y-2">
          <p className="text-sm font-semibold text-cyan-400 flex items-center gap-2">
            <Lock size={14} /> Batch Anchored on MST Blockchain
          </p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-gray-500">Batch ID</p>
              <p className="font-mono text-white">#{batch.batch_id}</p>
            </div>
            <div>
              <p className="text-gray-500">Tx Hash</p>
              <p className="font-mono text-gray-300 break-all">{batch.tx_hash || '(simulated)'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-gray-500">Merkle Root</p>
              <p className="font-mono text-cyan-300 break-all">{batch.merkle_root}</p>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        {step === 'load' && (
          <button
            onClick={anchorBatch}
            disabled={busy}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-cyan-500 text-navy-950 font-bold text-sm hover:bg-cyan-400 disabled:opacity-50 transition-all"
          >
            <Play size={15} /> {busy ? 'Anchoring…' : 'Anchor Batch'}
          </button>
        )}

        {step === 'tamper' && (
          <button
            onClick={simulateTamper}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-red-500/20 border border-red-500/40 text-red-300 font-bold text-sm hover:bg-red-500/30 transition-all"
          >
            <Zap size={15} /> Simulate Tampering (Record #5)
          </button>
        )}

        {step === 'verify' && (
          <button
            onClick={runVerify}
            disabled={busy}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-cyan-500 text-navy-950 font-bold text-sm hover:bg-cyan-400 disabled:opacity-50 transition-all"
          >
            <ShieldCheck size={15} /> {busy ? 'Verifying…' : 'Run Verification'}
          </button>
        )}
      </div>

      {/* Result */}
      {result && step === 'done' && (
        <div className={`glass-panel rounded-xl p-6 border ${isVerified ? 'border-green-500/30' : 'border-red-500/40'}`}>
          <div className="flex items-center gap-3 mb-4">
            {isVerified
              ? <ShieldCheck size={32} className="text-green-400" />
              : <ShieldAlert size={32} className="text-red-400" />
            }
            <div>
              <p className={`text-xl font-bold ${isVerified ? 'text-green-300' : 'text-red-300'}`}>
                {isVerified ? '✓ Integrity Confirmed' : '✗ Tampering Detected!'}
              </p>
              <p className="text-gray-400 text-xs mt-0.5">
                {result._simulated ? 'Local simulation result' : 'Backend verification result'}
              </p>
            </div>
          </div>

          <div className="space-y-2 mb-4">
            <div className="bg-white/5 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Expected Merkle Root (anchored)</p>
              <p className="font-mono text-xs text-cyan-300 break-all">{result.expected_root || '—'}</p>
            </div>
            <div className={`rounded-lg p-3 ${isVerified ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              <p className="text-xs text-gray-500 mb-1">Computed Merkle Root (from current records)</p>
              <p className={`font-mono text-xs break-all ${isVerified ? 'text-green-300' : 'text-red-300'}`}>
                {result.computed_root || '—'}
              </p>
            </div>
          </div>

          {result.errors?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                Integrity Violations ({result.errors.length})
              </p>
              <ul className="space-y-1.5">
                {result.errors.map((e, i) => (
                  <li key={i} className="text-xs bg-red-500/10 border border-red-500/20 rounded px-3 py-1.5 text-red-200">
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


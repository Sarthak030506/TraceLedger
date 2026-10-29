import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, Play, RefreshCw } from 'lucide-react';
import { fetchBatches, verifyBatch } from '../services/api';

export default function Verification() {
  const [batches, setBatches]   = useState([]);
  const [batchId, setBatchId]   = useState('');
  const [result, setResult]     = useState(null);
  const [loading, setLoading]   = useState(false);
  const [loadingBatches, setLoadingBatches] = useState(true);

  useEffect(() => {
    fetchBatches()
      .then(d => {
        const list = d.batches || [];
        setBatches(list);
        if (list.length > 0) setBatchId(String(list[0].batch_id));
      })
      .finally(() => setLoadingBatches(false));
  }, []);

  const runVerification = async () => {
    if (!batchId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await verifyBatch(Number(batchId));
      setResult(r);
    } catch (e) {
      setResult({ verified: false, errors: [e.message] });
    } finally {
      setLoading(false);
    }
  };

  const isVerified = result?.verified === true;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Batch Verification</h1>
        <p className="text-gray-400 text-sm mt-1">
          Verify that a committed batch's Merkle root matches the on-chain anchor and detect any tampering.
        </p>
      </div>

      {/* Controls */}
      <div className="glass-panel rounded-xl p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Select Batch</label>
          {loadingBatches ? (
            <div className="text-gray-500 text-sm">Loading batches…</div>
          ) : batches.length === 0 ? (
            <div className="text-gray-500 text-sm">No batches available. Submit a batch first.</div>
          ) : (
            <select
              value={batchId}
              onChange={e => { setBatchId(e.target.value); setResult(null); }}
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-cyan-500/50 cursor-pointer"
            >
              {batches.map(b => (
                <option key={b.batch_id} value={b.batch_id} className="bg-gray-900">
                  Batch #{b.batch_id} — {b.record_count ?? '?'} records
                  {b.timestamp ? ` · ${new Date(b.timestamp * 1000).toLocaleDateString()}` : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        <button
          onClick={runVerification}
          disabled={loading || !batchId || batches.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-cyan-500 text-navy-950 font-semibold text-sm hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {loading
            ? <><RefreshCw size={15} className="animate-spin" /> Running…</>
            : <><Play size={15} /> Run Verification</>
          }
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className={`glass-panel rounded-xl p-6 border ${isVerified ? 'border-green-500/30' : 'border-red-500/30'}`}>
          <div className="flex items-center gap-3 mb-4">
            {isVerified
              ? <ShieldCheck size={28} className="text-green-400" />
              : <ShieldAlert size={28} className="text-red-400" />
            }
            <div>
              <p className={`text-lg font-bold ${isVerified ? 'text-green-300' : 'text-red-300'}`}>
                {isVerified ? 'Verification Passed' : 'Verification Failed'}
              </p>
              <p className="text-gray-400 text-xs">Batch #{batchId}</p>
            </div>
          </div>

          {/* Root comparison */}
          {(result.expected_root || result.computed_root) && (
            <div className="space-y-2 mb-4">
              <div className="bg-white/5 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">Expected Merkle Root (on-chain)</p>
                <p className="font-mono text-xs text-cyan-300 break-all">{result.expected_root || '—'}</p>
              </div>
              <div className={`rounded-lg p-3 ${isVerified ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                <p className="text-xs text-gray-500 mb-1">Computed Merkle Root</p>
                <p className={`font-mono text-xs break-all ${isVerified ? 'text-green-300' : 'text-red-300'}`}>
                  {result.computed_root || '—'}
                </p>
              </div>
            </div>
          )}

          {/* Errors */}
          {result.errors && result.errors.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-400 mb-2 uppercase tracking-wider">
                Issues Detected ({result.errors.length})
              </p>
              <ul className="space-y-1">
                {result.errors.map((err, i) => (
                  <li key={i} className="text-xs text-red-300 bg-red-500/10 rounded px-3 py-1.5 border border-red-500/20">
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {isVerified && (
            <p className="text-xs text-green-400 mt-2">
              ✓ Merkle root matches on-chain anchor. No tampering detected in this batch.
            </p>
          )}
        </div>
      )}

      {/* Info */}
      <div className="glass-panel rounded-xl p-5 text-sm text-gray-400 space-y-2">
        <p className="text-white font-medium text-sm">How verification works</p>
        <ol className="list-decimal list-inside space-y-1 text-xs">
          <li>Retrieve all records stored for the selected batch from the local database.</li>
          <li>Recompute the Merkle root from those records using SHA-256 pair hashing.</li>
          <li>Compare the computed root against the root anchored on the MST Blockchain.</li>
          <li>Report any hash mismatches, missing records, reordering, or duplicates.</li>
        </ol>
        <p className="text-xs text-gray-500 pt-1">
          TraceLedger <em>detects</em> tampering — it cannot prevent it. Results reflect the integrity of stored records.
        </p>
      </div>
    </div>
  );
}


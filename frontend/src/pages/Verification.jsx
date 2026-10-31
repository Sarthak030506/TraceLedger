import React, { useEffect, useState } from 'react';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { fetchBatches, verifyBatch } from '../services/api';
import { PageHeader, Card, Verdict } from '../components/ui';
import { Link } from '../router';

const STEPS = [
  ['Fetch the evidence', 'Raw records from the sidecar store, or the stored leaf hashes if raw logs are unavailable.'],
  ['Re-hash everything', 'Each record is re-serialised canonically and hashed with SHA-256, then folded into a Merkle root.'],
  ['Read the chain', 'The commitment — root, previous root, sequence range and count — is read back from the contract.'],
  ['Report precisely', 'Altered, missing, reordered and duplicated records are named by sequence number.'],
];

export default function Verification() {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingBatches, setLoadingBatches] = useState(true);

  useEffect(() => {
    fetchBatches(200, 0)
      .then((d) => {
        const list = d.is_fallback ? [] : d.batches || [];
        setBatches(list);
        if (list.length > 0) setBatchId(String(list[0].batch_id));
      })
      .finally(() => setLoadingBatches(false));
  }, []);

  const run = async () => {
    if (!batchId) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await verifyBatch(Number(batchId)));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-10">
      <PageHeader
        title="Verify a batch"
        subtitle="Recompute a batch from its evidence and compare it with what was anchored on-chain. TraceLedger detects tampering; it cannot prevent it."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
        <Card className="p-6 sm:p-7">
          <label htmlFor="batch" className="label-mono text-muted-light">Batch</label>
          {loadingBatches ? (
            <p className="mt-3 text-[14px] text-muted-light">Loading batches…</p>
          ) : batches.length === 0 ? (
            <p className="mt-3 text-[14px] text-muted-light">
              No batches available. Anchor one in the <Link to="/app/lab" className="underline underline-offset-2">tamper lab</Link>.
            </p>
          ) : (
            <select
              id="batch"
              value={batchId}
              onChange={(e) => { setBatchId(e.target.value); setResult(null); setError(null); }}
              className="mt-3 w-full cursor-pointer appearance-none rounded-xl hairline-light bg-paper px-4 py-3 text-[15px] text-ink focus:border-ink/30 focus:outline-none"
            >
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  Batch #{b.batch_id} · {b.record_count ?? '?'} records
                  {b.timestamp ? ` · ${new Date(b.timestamp * 1000).toLocaleDateString()}` : ''}
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            onClick={run}
            disabled={loading || !batchId}
            className="btn-ink mt-6"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            {loading ? 'Verifying…' : 'Run verification'}
          </button>

          {error && <p className="mt-4 text-[14px] text-bad">{error}</p>}
        </Card>

        <Card className="p-6 sm:p-7">
          <p className="label-mono text-muted-light">How it works</p>
          <ol className="mt-4 space-y-4">
            {STEPS.map(([title, body], i) => (
              <li key={title} className="flex gap-4">
                <span className="font-mono text-[12px] text-muted-light">0{i + 1}</span>
                <span>
                  <span className="block text-[15px] font-medium text-ink">{title}</span>
                  <span className="mt-0.5 block text-[13.5px] leading-[1.5] text-muted-light">{body}</span>
                </span>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {result && <Verdict result={result} batchId={batchId} />}
    </div>
  );
}

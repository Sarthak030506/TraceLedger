import React, { useState } from 'react';
import { RotateCcw, ShieldCheck, RefreshCw, Anchor } from 'lucide-react';
import { fetchBatches, submitBatch, verifyBatch, hashRecord, buildMerkleRoot } from '../services/api';
import { PageHeader, Card, Notice, Verdict, shortHash } from '../components/ui';
import StatusBadge from '../components/StatusBadge';

// Sample events in the real record schema, so the browser hashes exactly what the backend hashes.
const SAMPLE = [
  { event_type: 'authentication', source: 'auth-service', details: { user: 'alice', result: 'success', ip: '10.0.0.xxx' } },
  { event_type: 'data_read', source: 'api-gateway', details: { user: 'alice', resource: '/api/users', rows: 42 } },
  { event_type: 'data_write', source: 'orders', details: { user: 'bob', order_id: 9981, field: 'amount_minor' } },
  { event_type: 'permission_change', source: 'iam', details: { actor: 'bob', target: 'bob', new_role: 'superuser' } },
  { event_type: 'data_delete', source: 'audit-store', details: { actor: 'eve', table: 'audit_log', rows: 120 } },
];

const ATTACKS = [
  { id: 'none', label: 'Leave untouched', hint: 'Control run: should verify cleanly.' },
  { id: 'alter', label: 'Alter a record', hint: 'Rewrite what eve deleted (seq 5).' },
  { id: 'delete', label: 'Delete a record', hint: 'Remove the privilege change (seq 4).' },
  { id: 'reorder', label: 'Reorder records', hint: 'Swap the write and the read.' },
  { id: 'replay', label: 'Replay a record', hint: 'Duplicate the sign-in event.' },
];

function applyAttack(records, attack) {
  const r = records.map((x) => ({ ...x, details: { ...x.details } }));
  switch (attack) {
    case 'alter':
      r[4].details.rows = 0; // record_hash is kept, so the change is caught per record
      return r;
    case 'delete':
      return r.filter((_, i) => i !== 3);
    case 'reorder':
      return [r[0], r[2], r[1], r[3], r[4]];
    case 'replay':
      return [r[0], { ...r[0] }, ...r.slice(1)];
    default:
      return r;
  }
}

/** In-browser fallback when the backend is unreachable. Mirrors integrity/verifier.py. */
async function localVerify(records, expectedRoot, first, last) {
  const errors = [];
  const leaves = [];
  let prev = null;
  for (const rec of records) {
    const seq = rec.sequence_number;
    if (prev !== null) {
      if (seq === prev) errors.push(`Duplicate sequence number detected: ${seq}`);
      else if (seq < prev) errors.push(`Records reordered: sequence ${seq} appeared after sequence ${prev}`);
      else if (seq > prev + 1) errors.push(`Missing sequence number(s) between ${prev} and ${seq}`);
    }
    prev = seq;
    const h = await hashRecord(rec);
    leaves.push(h);
    if (rec.record_hash && rec.record_hash !== h) errors.push(`Record sequence ${seq} (event ${rec.event_id}) tampered: stored hash != recomputed hash`);
  }
  if (records.length !== last - first + 1) errors.push(`Record count mismatch: commitment covers ${last - first + 1}, got ${records.length}`);
  const computed = await buildMerkleRoot(leaves);
  if (computed !== expectedRoot) errors.push(`Merkle root mismatch: expected ${expectedRoot}, computed ${computed}`);
  const verified = errors.length === 0;
  return {
    verified,
    expected_root: expectedRoot,
    computed_root: computed,
    record_count: records.length,
    errors,
    verification_source: 'local_browser',
    message: verified ? 'Verified in your browser (backend unreachable)' : `Integrity verification failed with ${errors.length} error(s)`,
  };
}

export default function Demo() {
  const [records, setRecords] = useState(null); // sealed originals (with record_hash)
  const [batch, setBatch] = useState(null);
  const [localOnly, setLocalOnly] = useState(false);
  const [attack, setAttack] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const step = result ? 4 : attack ? 3 : batch ? 2 : 1;
  const shown = records && attack ? applyAttack(records, attack) : records;

  const reset = () => {
    setRecords(null); setBatch(null); setLocalOnly(false);
    setAttack(null); setResult(null); setError(null);
  };

  const sealAndAnchor = async () => {
    setBusy(true);
    setError(null);
    try {
      // Continue the chain from the latest committed batch
      const latestRes = await fetchBatches(1, 0);
      const latest = latestRes.is_fallback ? null : latestRes.batches?.[0] || null;
      const firstSeq = latest ? latest.last_sequence + 1 : 1;
      const stamp = Date.now();
      const now = new Date(stamp).toISOString().replace(/\.\d{3}Z$/, 'Z');

      const sealed = [];
      for (let i = 0; i < SAMPLE.length; i++) {
        const rec = { event_id: `lab-${stamp}-${i + 1}`, sequence_number: firstSeq + i, timestamp: now, ...SAMPLE[i] };
        sealed.push({ ...rec, record_hash: await hashRecord(rec) });
      }
      const hashes = sealed.map((r) => r.record_hash);
      const root = await buildMerkleRoot(hashes);
      setRecords(sealed);

      if (latestRes.is_fallback) {
        setLocalOnly(true);
        setBatch({ batch_id: null, merkle_root: root, first_sequence: firstSeq, last_sequence: firstSeq + sealed.length - 1, status: 'offline' });
        return;
      }

      const res = await submitBatch({
        batch_id: latest ? latest.batch_id + 1 : 1,
        merkle_root: root,
        previous_root: latest ? latest.merkle_root : '0'.repeat(64),
        first_sequence: firstSeq,
        last_sequence: firstSeq + sealed.length - 1,
        record_count: sealed.length,
        record_hashes: hashes,
      });
      setBatch(res);
    } catch (e) {
      setError(e.message);
      setRecords(null);
    } finally {
      setBusy(false);
    }
  };

  const runVerify = async () => {
    setBusy(true);
    setError(null);
    try {
      const tampered = applyAttack(records, attack);
      let res = null;
      if (!localOnly) res = await verifyBatch(batch.batch_id, tampered);
      if (localOnly || res?.offline) {
        res = await localVerify(tampered, batch.merkle_root, batch.first_sequence, batch.last_sequence);
      }
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const tamperedSeqs = new Set();
  if (attack === 'alter') tamperedSeqs.add(records?.[4]?.sequence_number);

  return (
    <div className="space-y-10">
      <PageHeader
        title="Tamper lab"
        subtitle="Seal five events, anchor them, attack the stored copy, then watch the verifier catch it."
        actions={<button type="button" onClick={reset} className="btn-ghost-light"><RotateCcw className="h-3.5 w-3.5" /> Start over</button>}
      />

      <ol className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {['Seal & anchor', 'Choose an attack', 'Verify', 'Read the report'].map((label, i) => {
          const n = i + 1;
          const state = n < step ? 'done' : n === step ? 'now' : 'later';
          return (
            <li key={label} className={`rounded-2xl px-4 py-3 ${state === 'now' ? 'bg-ink text-paper' : 'hairline-light bg-white text-ink'} ${state === 'later' ? 'opacity-50' : ''}`}>
              <span className={`font-mono text-[11px] ${state === 'now' ? 'text-muted-dark' : 'text-muted-light'}`}>0{n}{state === 'done' ? ' · done' : ''}</span>
              <span className="mt-1 block text-[14px] font-medium">{label}</span>
            </li>
          );
        })}
      </ol>

      {error && <Notice tone="bad">{error}</Notice>}
      {localOnly && (
        <Notice>
          <strong className="font-medium">Backend unreachable.</strong> Running entirely in your browser: nothing is anchored and the check is not against the chain.
        </Notice>
      )}

      {!records && (
        <Card className="p-7">
          <p className="max-w-[560px] text-[15px] leading-[1.6] text-muted-light">
            Anchoring writes a real commitment to the configured chain, continuing from the latest batch.
            On a live deployment you will be asked once for the operator API key.
          </p>
          <button type="button" onClick={sealAndAnchor} disabled={busy} className="btn-ink mt-6">
            {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Anchor className="h-4 w-4" />}
            {busy ? 'Sealing and anchoring…' : 'Seal & anchor 5 events'}
          </button>
        </Card>
      )}

      {shown && (
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/[0.06] px-6 py-4">
            <h2 className="text-[17px] font-medium tracking-[-0.01em]">
              {attack && attack !== 'none' ? 'Stored copy after the attack' : 'Sealed events'}
            </h2>
            {batch && (
              <span className="flex flex-wrap items-center gap-3 font-mono text-[12px] text-muted-light">
                {batch.batch_id && <span>Batch #{batch.batch_id}</span>}
                <span>root {shortHash(batch.merkle_root, 6)}</span>
                <StatusBadge status={batch.status} />
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-[13.5px]">
              <thead>
                <tr className="border-b border-black/[0.06] text-left">
                  {['Seq', 'Event', 'Source', 'Details', 'Record hash'].map((h) => (
                    <th key={h} scope="col" className="label-mono px-5 py-3 font-normal text-muted-light">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.06]">
                {shown.map((r, i) => {
                  const hot = tamperedSeqs.has(r.sequence_number);
                  return (
                    <tr key={`${r.event_id}-${i}`} className={hot ? 'bg-paper' : ''}>
                      <td className="px-5 py-3 font-mono text-ink">{r.sequence_number}</td>
                      <td className="px-5 py-3 text-ink">{r.event_type}</td>
                      <td className="px-5 py-3 font-mono text-[12.5px] text-muted-light">{r.source}</td>
                      <td className={`px-5 py-3 font-mono text-[12px] ${hot ? 'text-bad' : 'text-muted-light'}`}>
                        {Object.entries(r.details).map(([k, v]) => `${k}=${v}`).join(' ')}
                      </td>
                      <td className="px-5 py-3 font-mono text-[12px] text-muted-light">{shortHash(r.record_hash, 5)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {batch && !result && (
        <Card className="p-6 sm:p-7">
          <p className="label-mono text-muted-light">Attack the stored copy</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-5">
            {ATTACKS.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => setAttack(a.id)}
                aria-pressed={attack === a.id}
                className={`rounded-2xl px-4 py-3 text-left transition-colors ${attack === a.id ? 'bg-ink text-paper' : 'hairline-light bg-paper text-ink hover:bg-paper-card'}`}
              >
                <span className="block text-[14px] font-medium">{a.label}</span>
                <span className={`mt-1 block text-[12px] leading-[1.4] ${attack === a.id ? 'text-muted-dark' : 'text-muted-light'}`}>{a.hint}</span>
              </button>
            ))}
          </div>
          <button type="button" onClick={runVerify} disabled={!attack || busy} className="btn-ink mt-6">
            {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            {busy ? 'Verifying…' : 'Run verification'}
          </button>
          <p className="mt-3 text-[12.5px] text-muted-light">
            The attack happens only to the copy in your browser. The anchored commitment is never touched.
          </p>
        </Card>
      )}

      {result && <Verdict result={result} batchId={batch?.batch_id} />}
    </div>
  );
}

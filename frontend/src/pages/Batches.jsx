import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Plus, Search, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-react';
import { fetchBatches, submitBatch } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import BatchDetailModal from '../components/BatchDetailModal';

const MOCK_RECORDS = [
  { seq: 1, event_type: 'LOGIN', actor: 'alice', resource: 'auth', timestamp: Date.now() / 1000 },
  { seq: 2, event_type: 'READ',  actor: 'alice', resource: '/api/users', timestamp: Date.now() / 1000 },
  { seq: 3, event_type: 'WRITE', actor: 'bob',   resource: '/api/orders', timestamp: Date.now() / 1000 },
];

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button onClick={copy} className="ml-1 text-gray-500 hover:text-cyan-400 transition-colors">
      {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
    </button>
  );
}

function truncate(str, n = 12) {
  if (!str) return '—';
  return str.length > n ? str.slice(0, n) + '…' : str;
}

export default function Batches() {
  const [batches, setBatches]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [search, setSearch]       = useState('');
  const [page, setPage]           = useState(1);
  const [selected, setSelected]   = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState(null);
  const PAGE_SIZE = 10;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBatches();
      setBatches(data.batches || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = batches.filter(b =>
    search === '' || String(b.batch_id).includes(search)
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSubmitDemo = async () => {
    setSubmitting(true);
    setSubmitMsg(null);
    try {
      const hashes = MOCK_RECORDS.map((_, i) =>
        Array.from({ length: 64 }, (__, j) => ((i * 7 + j * 13) % 16).toString(16)).join('')
      );
      await submitBatch({ record_hashes: hashes, records: MOCK_RECORDS });
      setSubmitMsg({ ok: true, text: 'Demo batch submitted successfully!' });
      await load();
    } catch (e) {
      setSubmitMsg({ ok: false, text: e.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Batch Explorer</h1>
          <p className="text-gray-400 text-sm mt-1">Browse all anchored log batches</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={load}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:text-white hover:border-cyan-500/40 transition-all text-sm"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button
            onClick={handleSubmitDemo}
            disabled={submitting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/30 transition-all text-sm disabled:opacity-50"
          >
            <Plus size={14} /> {submitting ? 'Submitting…' : 'Submit Demo Batch'}
          </button>
        </div>
      </div>

      {submitMsg && (
        <div className={`px-4 py-3 rounded-lg text-sm border ${submitMsg.ok ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
          {submitMsg.text}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          placeholder="Filter by Batch ID…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="w-full pl-9 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
        />
      </div>

      {/* Table */}
      <div className="glass-panel rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">Loading batches…</div>
        ) : error ? (
          <div className="flex items-center justify-center h-40 text-red-400 text-sm">{error}</div>
        ) : paged.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-500 text-sm gap-2">
            <span>No batches found.</span>
            <span className="text-xs">Submit a demo batch to get started.</span>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                {['Batch ID', 'Timestamp', 'Records', 'Seq Range', 'Merkle Root', 'Tx Hash', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {paged.map(b => (
                <tr
                  key={b.batch_id}
                  onClick={() => setSelected(b)}
                  className="hover:bg-white/5 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-cyan-400">#{b.batch_id}</td>
                  <td className="px-4 py-3 text-gray-300 whitespace-nowrap">
                    {b.timestamp ? new Date(b.timestamp * 1000).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{b.record_count ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                    {b.seq_start ?? '—'}–{b.seq_end ?? '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-300">
                    <span className="flex items-center">
                      {truncate(b.merkle_root, 14)}
                      {b.merkle_root && <CopyButton text={b.merkle_root} />}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">
                    <span className="flex items-center">
                      {truncate(b.tx_hash, 14)}
                      {b.tx_hash && <CopyButton text={b.tx_hash} />}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.chain_status || 'pending'} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!loading && filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>{filtered.length} batches · page {page}/{totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {selected && (
        <BatchDetailModal batch={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

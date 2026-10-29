import React, { useEffect, useState } from 'react';
import {
  Layers, ShieldCheck, Database, Link2, RefreshCw,
  TrendingUp, Clock, CheckCircle2
} from 'lucide-react';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import BatchDetailModal from '../components/BatchDetailModal';
import { fetchBatches, fetchHealth } from '../services/api';

function timeAgo(ts) {
  const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return date.toLocaleDateString();
}

function shortHash(h = '') {
  if (!h) return '—';
  const raw = h.startsWith('0x') ? h.slice(2) : h;
  return `${raw.slice(0, 8)}…${raw.slice(-8)}`;
}

export default function Dashboard({ health }) {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const data = await fetchBatches(10, 0);
      setBatches(data.batches || []);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const refresh = () => { setRefreshing(true); load(); };

  const stats = {
    total: health?.total_batches ?? batches.length,
    confirmed: batches.filter(b => b.status === 'confirmed').length,
    latest: health?.latest_batch_id ?? (batches[0]?.batch_id ?? 0),
    events: batches.reduce((acc, b) => acc + (b.record_count || 0), 0),
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Overview</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status of anchored security log batches on MST Blockchain
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-300 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Fallback Notice */}
      {health?.is_fallback && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
          <Clock className="w-4 h-4 shrink-0" />
          <span>
            <strong>Demo simulation mode</strong> — Backend API offline or unreachable.
            Showing deterministic mock data clearly labelled as simulated.
          </span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Batches Anchored"
          value={loading ? '…' : stats.total}
          subtitle="Cryptographic commitments on MST"
          icon={Layers}
          color="cyan"
        />
        <StatCard
          title="Events Sealed"
          value={loading ? '…' : stats.events}
          subtitle="Across all committed batches"
          icon={Database}
          color="indigo"
        />
        <StatCard
          title="On-Chain Confirmed"
          value={loading ? '…' : stats.confirmed}
          subtitle="Finalized on MST testnet"
          icon={Link2}
          color="emerald"
        />
        <StatCard
          title="Latest Batch"
          value={loading ? '…' : `#${stats.latest}`}
          subtitle="Most recent batch committed"
          icon={TrendingUp}
          color="amber"
        />
      </div>

      {/* Batch Timeline */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">Committed Batch Timeline</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {batches.length} batch{batches.length !== 1 ? 'es' : ''} shown
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-cyan-500" />
              <span className="text-sm">Loading batch commitments…</span>
            </div>
          </div>
        ) : batches.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-slate-400">
            <div className="text-center">
              <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No batches committed yet</p>
              <p className="text-xs mt-1">Run the sidecar to start anchoring events</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {batches.map((batch) => (
              <div
                key={batch.batch_id}
                onClick={() => setSelectedBatch(batch)}
                className="flex items-center px-6 py-4 gap-4 cursor-pointer hover:bg-slate-800/30 transition-colors group"
              >
                {/* Batch ID pill */}
                <div className="w-14 shrink-0 text-center">
                  <span className="inline-block px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-xs font-bold">
                    #{batch.batch_id}
                  </span>
                </div>

                {/* Merkle Root */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-400 mb-0.5">Merkle Root</p>
                  <p className="font-mono text-xs text-slate-200 truncate">
                    {shortHash(batch.merkle_root)}
                  </p>
                </div>

                {/* Records */}
                <div className="w-20 shrink-0 text-right">
                  <p className="text-xs text-slate-400 mb-0.5">Records</p>
                  <p className="font-mono text-xs text-white font-semibold">
                    {batch.record_count}
                  </p>
                </div>

                {/* Status */}
                <div className="shrink-0">
                  <StatusBadge status={batch.status} />
                </div>

                {/* Time */}
                <div className="w-20 shrink-0 text-right hidden sm:block">
                  <p className="text-xs text-slate-400">
                    {timeAgo(batch.timestamp || batch.created_at)}
                  </p>
                </div>

                <div className="text-slate-600 group-hover:text-slate-300 transition-colors text-xs hidden sm:block">
                  →
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chain Integrity Explanation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400">
        {[
          {
            icon: ShieldCheck,
            title: 'Cryptographic Sealing',
            desc: 'Each event is hashed with SHA-256. Hashes are combined into a Merkle tree — changing any event changes the root.',
          },
          {
            icon: Link2,
            title: 'Tamper-Evident Chaining',
            desc: 'Every batch includes the previous batch\'s Merkle root. Deleting or reordering a batch breaks the entire chain.',
          },
          {
            icon: CheckCircle2,
            title: 'Independent Verification',
            desc: 'Any party can recompute hashes and compare against the on-chain root without trusting the operator.',
          },
        ].map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.title} className="glass-panel rounded-xl p-4 flex items-start gap-3">
              <Icon className="w-5 h-5 text-cyan-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-white font-semibold text-sm mb-1">{card.title}</p>
                <p>{card.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {selectedBatch && (
        <BatchDetailModal
          batch={selectedBatch}
          onClose={() => setSelectedBatch(null)}
        />
      )}
    </div>
  );
}


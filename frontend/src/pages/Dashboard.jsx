import React, { useEffect, useState } from 'react';
import { RefreshCw, ArrowUpRight } from 'lucide-react';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import BatchDetailModal from '../components/BatchDetailModal';
import { PageHeader, Card, Notice, shortHash } from '../components/ui';
import { Link } from '../router';
import { fetchBatches } from '../services/api';

export function timeAgo(ts) {
  const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (Number.isNaN(diff)) return '—';
  if (diff < 60) return `${Math.max(diff, 0)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return date.toLocaleDateString();
}

export default function Dashboard({ health }) {
  const [batches, setBatches] = useState([]);
  const [isFallback, setIsFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState(null);

  const load = async () => {
    try {
      const data = await fetchBatches(10, 0);
      setBatches(data.batches || []);
      setIsFallback(Boolean(data.is_fallback));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const stats = {
    total: health?.total_batches ?? batches.length,
    confirmed: batches.filter((b) => b.status === 'confirmed').length,
    latest: health?.latest_batch_id ?? (batches[0]?.batch_id ?? 0),
    events: batches.reduce((acc, b) => acc + (b.record_count || 0), 0),
  };
  const dash = (v) => (loading ? '…' : v);

  return (
    <div className="space-y-10">
      <PageHeader
        title="Overview"
        subtitle="Every committed batch of security logs, and whether it is really anchored on MST Blockchain."
        actions={
          <button type="button" onClick={() => { setRefreshing(true); load(); }} disabled={refreshing} className="btn-ghost-light">
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        }
      />

      {(health?.is_fallback || isFallback) && (
        <Notice>
          <strong className="font-medium">Backend unreachable.</strong> Showing preview data that is not anchored anywhere.
        </Notice>
      )}
      {health && !health.is_fallback && health.anchor_mode === 'simulated' && (
        <Notice>
          <strong className="font-medium">Simulation mode.</strong> No blockchain is configured, so new batches are marked “simulated” and are not on-chain.
        </Notice>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard title="Batches" value={dash(stats.total)} subtitle="Commitments recorded" />
        <StatCard title="Events sealed" value={dash(stats.events)} subtitle="In the batches shown" />
        <StatCard title="On-chain" value={dash(stats.confirmed)} subtitle="Confirmed transactions" />
        <StatCard title="Latest" value={dash(`#${stats.latest}`)} subtitle="Most recent batch" />
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-black/[0.06] px-6 py-4">
          <h2 className="text-[17px] font-medium tracking-[-0.01em]">Recent batches</h2>
          <Link to="/app/batches" className="inline-flex items-center gap-1 text-[13px] text-muted-light hover:text-ink">
            View all <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loading ? (
          <p className="px-6 py-16 text-center text-[14px] text-muted-light">Loading commitments…</p>
        ) : batches.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-[15px] text-ink">No batches committed yet</p>
            <p className="mt-1 text-[13px] text-muted-light">
              Anchor your first batch from the <Link to="/app/lab" className="underline underline-offset-2">tamper lab</Link>.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-black/[0.06]">
            {batches.map((b) => (
              <li key={b.batch_id}>
                <button
                  type="button"
                  onClick={() => setSelected(b)}
                  className="flex w-full items-center gap-4 px-6 py-4 text-left transition-colors hover:bg-paper/60"
                >
                  <span className="w-14 shrink-0 font-mono text-[13px] text-ink">#{b.batch_id}</span>
                  <span className="min-w-0 flex-1">
                    <span className="label-mono block text-muted-light">Merkle root</span>
                    <span className="mt-0.5 block truncate font-mono text-[12.5px] text-ink">{shortHash(b.merkle_root, 10)}</span>
                  </span>
                  <span className="hidden w-20 shrink-0 text-right sm:block">
                    <span className="label-mono block text-muted-light">Records</span>
                    <span className="mt-0.5 block font-mono text-[13px] text-ink">{b.record_count}</span>
                  </span>
                  <span className="shrink-0"><StatusBadge status={b.status} /></span>
                  <span className="hidden w-20 shrink-0 text-right text-[13px] text-muted-light md:block">
                    {timeAgo(b.timestamp || b.created_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {health?.contract_address && !health.is_fallback && (
        <p className="font-mono text-[12px] text-muted-light">
          Contract {health.contract_address} · chain {health.chain_id ?? '—'} · mode {health.anchor_mode}
        </p>
      )}

      {selected && <BatchDetailModal batch={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

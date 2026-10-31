import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchBatches } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import BatchDetailModal from '../components/BatchDetailModal';
import { PageHeader, Card, Notice, CopyButton, shortHash } from '../components/ui';
import { Link } from '../router';

const PAGE_SIZE = 10;

export default function Batches() {
  const [batches, setBatches] = useState([]);
  const [isFallback, setIsFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchBatches(200, 0);
      setBatches(data.batches || []);
      setIsFallback(Boolean(data.is_fallback));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const q = search.trim().toLowerCase();
  const filtered = batches.filter((b) =>
    q === '' ||
    String(b.batch_id).includes(q) ||
    (b.merkle_root || '').includes(q) ||
    (b.transaction_hash || '').toLowerCase().includes(q)
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Batches"
        subtitle="Every commitment, its sequence range and the transaction that anchored it."
        actions={
          <button type="button" onClick={load} className="btn-ghost-light">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        }
      />

      {isFallback && <Notice><strong className="font-medium">Backend unreachable.</strong> Showing preview data.</Notice>}

      <label className="relative block">
        <span className="sr-only">Search batches</span>
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-light" />
        <input
          type="search"
          placeholder="Search by batch ID, Merkle root or transaction hash"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="w-full rounded-full hairline-light bg-white py-3 pl-11 pr-4 text-[14px] text-ink placeholder:text-muted-light focus:border-ink/30 focus:outline-none"
        />
      </label>

      <Card className="overflow-hidden">
        {loading ? (
          <p className="px-6 py-16 text-center text-[14px] text-muted-light">Loading batches…</p>
        ) : paged.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-[15px] text-ink">{batches.length ? 'No batches match your search' : 'No batches yet'}</p>
            {!batches.length && (
              <p className="mt-1 text-[13px] text-muted-light">
                Anchor one from the <Link to="/app/lab" className="underline underline-offset-2">tamper lab</Link>.
              </p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-[13.5px]">
              <thead>
                <tr className="border-b border-black/[0.06] text-left">
                  {['Batch', 'Anchored', 'Records', 'Sequence', 'Merkle root', 'Transaction', 'Status'].map((h) => (
                    <th key={h} scope="col" className="label-mono px-5 py-3.5 font-normal text-muted-light">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.06]">
                {paged.map((b) => (
                  <tr
                    key={b.batch_id}
                    onClick={() => setSelected(b)}
                    className="cursor-pointer transition-colors hover:bg-paper/60"
                  >
                    <td className="px-5 py-4 font-mono text-ink">#{b.batch_id}</td>
                    <td className="whitespace-nowrap px-5 py-4 text-muted-light">
                      {b.timestamp ? new Date(b.timestamp * 1000).toLocaleString() : '—'}
                    </td>
                    <td className="px-5 py-4 font-mono text-ink">{b.record_count ?? '—'}</td>
                    <td className="whitespace-nowrap px-5 py-4 font-mono text-muted-light">
                      {b.first_sequence ?? '—'}–{b.last_sequence ?? '—'}
                    </td>
                    <td className="px-5 py-4 font-mono text-[12.5px] text-ink">
                      <span className="inline-flex items-center gap-2">{shortHash(b.merkle_root, 6)} <CopyButton text={b.merkle_root} /></span>
                    </td>
                    <td className="px-5 py-4 font-mono text-[12.5px] text-muted-light">
                      <span className="inline-flex items-center gap-2">{shortHash(b.transaction_hash, 6)} <CopyButton text={b.transaction_hash} /></span>
                    </td>
                    <td className="px-5 py-4"><StatusBadge status={b.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {!loading && filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between text-[13px] text-muted-light">
          <span>{filtered.length} batches · page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button type="button" aria-label="Previous page" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="btn-ghost-light px-2.5 disabled:opacity-30"><ChevronLeft className="h-4 w-4" /></button>
            <button type="button" aria-label="Next page" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="btn-ghost-light px-2.5 disabled:opacity-30"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
      )}

      {selected && <BatchDetailModal batch={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

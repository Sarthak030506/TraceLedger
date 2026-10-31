/**
 * TraceLedger Frontend API Client
 * Interfaces with FastAPI backend (http://localhost:8000).
 * Provides automatic graceful fallback to mock data if the backend is unreachable.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (_err) {
    return {
      status: 'offline_mode',
      blockchain_connected: false,
      contract_address: '0x32A8c57512F982C99D5Ec5174e9297686B1aFCE6',
      chain_id: 1337,
      latest_batch_id: 3,
      total_batches: 3,
      is_fallback: true,
    };
  }
}

export async function fetchBatches(limit = 50, offset = 0) {
  try {
    const res = await fetch(`${API_BASE}/api/batches?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (_err) {
    return {
      batches: [
        {
          batch_id: 3,
          merkle_root: "9c3e41b2f8a70512e6d9b4c3a1f8e70512e6d9b4c3a1f8e70512e6d9b4c3a1f8",
          previous_root: "8b2d30a1e7f60401d5c8a3b2f0e7d60401d5c8a3b2f0e7d60401d5c8a3b2f0e7",
          first_sequence: 11, last_sequence: 15, record_count: 5,
          timestamp: 1729000200, status: "simulated",
          transaction_hash: "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90",
          block_number: 10003,
          created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        },
        {
          batch_id: 2,
          merkle_root: "8b2d30a1e7f60401d5c8a3b2f0e7d60401d5c8a3b2f0e7d60401d5c8a3b2f0e7",
          previous_root: "7a1c29f0d6e50390c4b792a1e9d6c50390c4b792a1e9d6c50390c4b792a1e9d6",
          first_sequence: 6, last_sequence: 10, record_count: 5,
          timestamp: 1729000100, status: "simulated",
          transaction_hash: "0x6e7d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d",
          block_number: 10002,
          created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
        },
        {
          batch_id: 1,
          merkle_root: "7a1c29f0d6e50390c4b792a1e9d6c50390c4b792a1e9d6c50390c4b792a1e9d6",
          previous_root: "0000000000000000000000000000000000000000000000000000000000000000",
          first_sequence: 1, last_sequence: 5, record_count: 5,
          timestamp: 1729000000, status: "simulated",
          transaction_hash: "0x5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c",
          block_number: 10001,
          created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
        },
      ],
      total: 3,
      is_fallback: true,
    };
  }
}

export async function fetchBatch(batchId) {
  try {
    const res = await fetch(`${API_BASE}/api/batches/${batchId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (_err) {
    const all = await fetchBatches();
    const found = all.batches.find((b) => b.batch_id === Number(batchId));
    if (!found) throw new Error(`Batch ${batchId} not found`);
    return found;
  }
}

// ── Merkle root computation (mirrors Python integrity/merkle.py) ──────────────
async function sha256hex(data) {
  const buf = typeof data === 'string' ? new TextEncoder().encode(data) : data;
  const digest = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function hashPair(leftHex, rightHex) {
  const left = Uint8Array.from(leftHex.match(/.{2}/g).map(b => parseInt(b, 16)));
  const right = Uint8Array.from(rightHex.match(/.{2}/g).map(b => parseInt(b, 16)));
  const combined = new Uint8Array(left.length + right.length);
  combined.set(left); combined.set(right, left.length);
  return sha256hex(combined);
}

// Canonical record form — must match sidecar/hasher.py exactly:
// keys sorted at every level, no whitespace, non-ASCII kept as-is.
const RECORD_FIELDS = ['event_id', 'sequence_number', 'timestamp', 'event_type', 'source', 'details'];

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export async function hashRecord(record) {
  const data = Object.fromEntries(RECORD_FIELDS.map((k) => [k, record[k]]));
  return sha256hex(canonicalJson(data));
}

export async function buildMerkleRoot(hashes) {
  if (hashes.length === 0) return '0'.repeat(64);
  if (hashes.length === 1) return hashes[0];
  let level = [...hashes];
  while (level.length > 1) {
    if (level.length % 2 === 1) level.push(level[level.length - 1]);
    const next = [];
    for (let i = 0; i < level.length; i += 2) next.push(await hashPair(level[i], level[i + 1]));
    level = next;
  }
  return level[0];
}

const API_KEY_STORAGE = 'traceledger_api_key';

function readApiKey() {
  try { return sessionStorage.getItem(API_KEY_STORAGE); } catch (_) { return null; }
}

function storeApiKey(key) {
  try { sessionStorage.setItem(API_KEY_STORAGE, key); } catch (_) { /* storage unavailable */ }
}

// ── submitBatch: auto-fills required fields if not provided ──────────────────
export async function submitBatch(batchData) {
  // If the caller provides raw record_hashes but not merkle_root/batch_id, compute them
  let payload = { ...batchData };

  if (!payload.merkle_root && payload.record_hashes?.length) {
    payload.merkle_root = await buildMerkleRoot(payload.record_hashes);
  }

  if (!payload.batch_id || !payload.first_sequence) {
    // Ask backend for latest batch to compute next id and sequence
    let nextId = 1;
    let firstSeq = 1;
    let prevRoot = '0'.repeat(64);
    try {
      const latestRes = await fetch(`${API_BASE}/api/batches?limit=1&offset=0`);
      if (latestRes.ok) {
        const latestData = await latestRes.json();
        if (latestData.batches?.length) {
          const latest = latestData.batches[0];
          nextId = latest.batch_id + 1;
          firstSeq = latest.last_sequence + 1;
          prevRoot = latest.merkle_root;
        }
      }
    } catch (_) { /* use defaults */ }

    const count = payload.record_hashes?.length ?? payload.record_count ?? 1;
    payload.batch_id = payload.batch_id ?? nextId;
    payload.previous_root = payload.previous_root ?? prevRoot;
    payload.first_sequence = payload.first_sequence ?? firstSeq;
    payload.last_sequence = payload.last_sequence ?? (firstSeq + count - 1);
    payload.record_count = payload.record_count ?? count;
  }

  // Strip non-schema fields (records is just for local use)
  const { records: _records, ...body } = payload;

  const post = (apiKey) => fetch(`${API_BASE}/api/batches`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    },
    body: JSON.stringify(body),
  });

  // The operator key is never bundled into the build; it is entered once per tab.
  let apiKey = readApiKey();
  let res = await post(apiKey);
  if (res.status === 401) {
    apiKey = window.prompt('Batch submission requires the backend operator API key (X-API-Key):');
    if (apiKey) {
      res = await post(apiKey.trim());
      if (res.ok) storeApiKey(apiKey.trim());
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit batch: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function verifyBatch(batchId, records = null) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/batches/${batchId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records }),
    });
  } catch (_err) {
    // Never invent a verdict: an unreachable verifier means "not verified", not "verified".
    return {
      batch_id: Number(batchId),
      verified: null,
      offline: true,
      expected_root: '',
      computed_root: '',
      record_count: records ? records.length : 0,
      errors: [],
      message: 'Backend unreachable — verification was not performed.',
    };
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

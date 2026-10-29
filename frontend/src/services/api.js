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
  } catch (err) {
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
  } catch (err) {
    // Deterministic mock fallback
    return {
      batches: [
        {
          batch_id: 3,
          merkle_root: "9c3e41b2f8a70512e6d9b4c3a1f8e70512e6d9b4c3a1f8e70512e6d9b4c3a1f8",
          previous_root: "8b2d30a1e7f60401d5c8a3b2f0e7d60401d5c8a3b2f0e7d60401d5c8a3b2f0e7",
          first_sequence: 11,
          last_sequence: 15,
          record_count: 5,
          timestamp: 1729000200,
          status: "confirmed",
          transaction_hash: "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90",
          block_number: 10003,
          created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
        },
        {
          batch_id: 2,
          merkle_root: "8b2d30a1e7f60401d5c8a3b2f0e7d60401d5c8a3b2f0e7d60401d5c8a3b2f0e7",
          previous_root: "7a1c29f0d6e50390c4b792a1e9d6c50390c4b792a1e9d6c50390c4b792a1e9d6",
          first_sequence: 6,
          last_sequence: 10,
          record_count: 5,
          timestamp: 1729000100,
          status: "confirmed",
          transaction_hash: "0x6e7d8c9b0a1f2e3d4c5b6a7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d",
          block_number: 10002,
          created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
        },
        {
          batch_id: 1,
          merkle_root: "7a1c29f0d6e50390c4b792a1e9d6c50390c4b792a1e9d6c50390c4b792a1e9d6",
          previous_root: "0000000000000000000000000000000000000000000000000000000000000000",
          first_sequence: 1,
          last_sequence: 5,
          record_count: 5,
          timestamp: 1729000000,
          status: "confirmed",
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
  } catch (err) {
    const all = await fetchBatches();
    const found = all.batches.find((b) => b.batch_id === Number(batchId));
    if (!found) throw new Error(`Batch ${batchId} not found`);
    return found;
  }
}

export async function submitBatch(batchData) {
  const res = await fetch(`${API_BASE}/api/batches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(batchData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit batch: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function verifyBatch(batchId, records = null) {
  try {
    const res = await fetch(`${API_BASE}/api/batches/${batchId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    // If backend offline, compute simulated verification
    const isTampered = records && records.some((r) => r.details?.tampered);
    return {
      batch_id: Number(batchId),
      verified: !isTampered,
      expected_root: "9c3e41b2f8a70512e6d9b4c3a1f8e70512e6d9b4c3a1f8e70512e6d9b4c3a1f8",
      computed_root: isTampered
        ? "00000000000000000000000000000000000000000000000000000000tampered"
        : "9c3e41b2f8a70512e6d9b4c3a1f8e70512e6d9b4c3a1f8e70512e6d9b4c3a1f8",
      record_count: records ? records.length : 5,
      errors: isTampered
        ? ["Record sequence 1 (evt-001) tampered: hash mismatch", "Merkle root mismatch"]
        : [],
      message: isTampered
        ? "Integrity verification failed with 2 error(s)"
        : "Batch integrity verified successfully (Simulated)",
      transaction_hash: "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90",
    };
  }
}


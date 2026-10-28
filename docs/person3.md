# Person 3 — Blockchain Anchoring & Backend API

**Branch:** `feature/blockchain-backend`  
**Focus:** Store batch commitments on-chain and expose them through a backend API.

> The React dashboard is intentionally postponed. For this phase, Person 3 owns the important blockchain and backend work so the three team members have comparable core engineering responsibilities.

## Goal

Build the Solidity contract and FastAPI service that accept a Merkle root and batch metadata, anchor the commitment to an EVM-compatible testnet, store supporting metadata in SQLite, and expose batch status to the rest of the system.

## Tasks

1. Define the batch-commitment schema with the team. Proposed fields:
   - `batch_id`
   - `merkle_root`
   - `record_count`
   - `timestamp`
   - `signature` or signature reference, if required by the agreed design
2. Write a Solidity contract to store batch roots and monotonic batch IDs.
3. Add appropriate access control to prevent unauthorized submissions.
4. Set up Hardhat, contract tests and a deployment script.
5. Select a suitable EVM-compatible testnet after checking current availability and requirements.
6. Build FastAPI endpoints to submit commitments, list batches, retrieve batch details, and expose verification status.
7. Store off-chain metadata and transaction details in SQLite.
8. Handle pending, confirmed and failed transactions plus RPC/API errors.
9. Integrate Person 1's batch data and Person 2's Merkle root/verifier through agreed interfaces.
10. Provide a mock or sample API response so the future dashboard can be built without changing the API contract.

## Suggested files

```text
blockchain/
├── contracts/
│   └── TraceLedger.sol
├── scripts/
│   └── deploy.js
├── test/
└── hardhat.config.js

backend/
├── main.py
├── routes/
│   ├── batches.py
│   └── verification.py
├── services/
│   ├── blockchain.py
│   └── storage.py
├── schemas.py
└── database.py

tests/
└── test_api.py
```

## Proposed API

Confirm endpoint names and response fields with the team before implementation.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/batches` | List batch metadata and anchor status |
| `GET` | `/api/batches/{batch_id}` | Retrieve batch details |
| `POST` | `/api/batches` | Submit a prepared commitment |
| `POST` | `/api/batches/{batch_id}/verify` | Verify available records/proofs against the commitment |

Example response:

```json
{
  "batch_id": "1",
  "merkle_root": "0x...",
  "record_count": 5,
  "transaction_hash": "0x...",
  "block_number": 12345,
  "status": "confirmed"
}
```

The API must not expose private keys or put raw logs/personal information on-chain.

## Acceptance checklist

- [ ] Contract stores a root and monotonic batch identifier.
- [ ] Unauthorized submissions are rejected.
- [ ] Contract tests and deployment script work.
- [ ] API can submit a commitment and report transaction status.
- [ ] Batch metadata is stored in SQLite.
- [ ] API returns predictable JSON and useful errors.
- [ ] API can expose verification results from Person 2's module.
- [ ] Raw security logs remain off-chain.

## Five-day plan

| Day | Deliverable |
|---|---|
| 1 | Define schemas, FastAPI skeleton, SQLite and contract skeleton |
| 2 | Contract functions, access control and tests |
| 3 | Deployment setup and blockchain anchoring service |
| 4 | API endpoints and integration with Persons 1 and 2 |
| 5 | End-to-end testing, transaction/error handling and demo-ready API |

## Git workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/blockchain-backend

git add blockchain backend tests
git commit -m "Implement blockchain anchoring and FastAPI service"
git push -u origin feature/blockchain-backend
```

## Boundaries

Do **not** build the React dashboard yet. Focus on the blockchain contract, API, persistence, and integration. The dashboard will be a separate later phase.

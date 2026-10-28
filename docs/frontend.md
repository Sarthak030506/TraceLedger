# Frontend Developer — React Dashboard & End-to-End Demo

**Branch:** `feature/frontend-dashboard`  
**Project:** TraceLedger — Decentralized, Tamper-Evident Security Logging  
**Phase:** Build after the three core modules are integrated; UI scaffolding and mock-data work may start earlier.

## 1. Objective

Build the React + Tailwind CSS dashboard that lets a user inspect committed log batches, see blockchain anchoring status, run or review integrity verification, and understand tampering alerts. The dashboard must clearly distinguish real backend/testnet data from mock or demo data.

## 2. Responsibilities

### A. Frontend foundation
- Set up or continue the React application using the repository's existing toolchain.
- Configure Tailwind CSS and reusable UI components.
- Set up routing for the dashboard, batch details, verification results, and demo page.
- Create a shared API service layer rather than putting `fetch` calls directly in every component.
- Add `.env.example` with the backend base URL; do not commit secrets.

### B. Dashboard overview
- Show total batches, confirmed blockchain anchors, verification successes, and failed verifications.
- Display recent batches and recent integrity alerts.
- Use clear status labels such as `Pending`, `Confirmed`, `Verified`, `Tampered`, and `Error`.
- Include loading, empty, and API-error states.

### C. Batch explorer
- List batches with batch ID, timestamp, record count, shortened Merkle root, transaction status, and transaction hash.
- Add a batch details view.
- Provide a copy action for roots and transaction hashes.
- Link to the relevant block explorer only when the backend provides a valid transaction hash and configured explorer URL.

### D. Integrity verification view
- Show the expected/anchored root and the computed root returned by the verifier.
- Show pass/fail status and a plain-language explanation.
- Display the affected batch or record identifier when available.
- Never claim verification passed until the backend returns a successful result.

### E. Controlled tampering demonstration
Prepare a safe, reproducible demo using only the project's local test dataset:
1. Generate or load five sample security events.
2. Create and anchor a batch using the integrated backend.
3. Show the batch as committed/confirmed when the backend confirms it.
4. Use the backend's controlled demo mechanism—or a documented local test fixture—to modify or delete one local record.
5. Request verification again.
6. Display a clear integrity-failure alert when the verifier reports a mismatch.
7. Provide a reset option that restores the sample dataset for another demo run.

Do not create a browser-only fake failure that could be mistaken for a real verification result. If the attack endpoint is not implemented yet, label the flow **Demo simulation** and use clearly marked mock responses.

### F. Integration and reliability
- Integrate with Person 3's FastAPI endpoints using the agreed API schema.
- Coordinate with the backend developer before changing endpoint names or response fields.
- Support pagination or basic filtering only if time permits after the core flow works.
- Ensure the UI works at the buildathon presentation resolution and on a typical laptop screen.
- Add basic component/service tests and verify the production build.

## 3. Suggested page structure

```text
frontend/
└── src/
    ├── components/
    │   ├── AppShell.jsx
    │   ├── StatCard.jsx
    │   ├── BatchTable.jsx
    │   ├── StatusBadge.jsx
    │   ├── TransactionLink.jsx
    │   ├── IntegrityAlert.jsx
    │   └── VerificationResult.jsx
    ├── pages/
    │   ├── Dashboard.jsx
    │   ├── Batches.jsx
    │   ├── BatchDetails.jsx
    │   ├── Verification.jsx
    │   └── Demo.jsx
    ├── services/
    │   └── api.js
    ├── hooks/
    ├── types/                 # if using TypeScript
    ├── App.jsx
    └── main.jsx
```

Adapt this to the existing repository instead of duplicating files or replacing the current project structure unnecessarily.

## 4. API integration contract

Use the actual endpoints and schemas agreed with the backend developer. The following is a suggested contract, not a guarantee that these routes already exist.

| Method | Endpoint | UI use |
|---|---|---|
| `GET` | `/api/health` | Backend connection indicator |
| `GET` | `/api/batches` | Batch list and overview metrics |
| `GET` | `/api/batches/{batch_id}` | Batch detail page |
| `POST` | `/api/batches` | Submit a prepared commitment if permitted |
| `POST` | `/api/batches/{batch_id}/verify` | Show verification results |

Example environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Example service function:

```javascript
const API_BASE = import.meta.env.VITE_API_BASE_URL;

export async function getBatches() {
  const response = await fetch(`${API_BASE}/api/batches`);

  if (!response.ok) {
    throw new Error(`Unable to load batches (${response.status})`);
  }

  return response.json();
}
```

Adapt this example to the backend's final schema. Handle network errors and do not hardcode transaction hashes, Merkle roots, or success results as if they were real.

## 5. Design guidance

- Use a clean security-operations dashboard style with dark navy, white typography, and cyan accents, consistent with the proposal.
- Prioritize legibility and quick status recognition over decorative effects.
- Make failed integrity checks visually distinct and explain what failed.
- Use consistent formatting for timestamps, hashes, and transaction status.
- Avoid exposing raw sensitive log contents in the dashboard.
- Clearly label mock data, testnet data, and controlled attack simulation.

## 6. Acceptance checklist

- [ ] Dashboard loads and displays batches.
- [ ] Mock mode is clearly labelled and can be used before the API is ready.
- [ ] Real API data is used once the backend is integrated.
- [ ] Batch details show root, record count, and anchoring status.
- [ ] Verification page accurately reflects the backend result.
- [ ] Controlled demo shows a mismatch after a record is modified/deleted.
- [ ] Loading, empty, and error states are implemented.
- [ ] No private keys or raw sensitive logs are exposed.
- [ ] Frontend tests pass and production build succeeds.
- [ ] The demo can be reset and repeated during judging.

## 7. Suggested schedule

| Stage | Deliverable |
|---|---|
| Stage 1 | App shell, routes, dashboard layout and labelled mock data |
| Stage 2 | Batch explorer and details page |
| Stage 3 | API service layer and backend integration |
| Stage 4 | Verification page, alerts and controlled demo flow |
| Stage 5 | Responsive polish, tests and final buildathon walkthrough |

## 8. Git workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/frontend-dashboard

# Implement frontend changes, then:
git add frontend
git commit -m "Build TraceLedger React dashboard and demo"
git push -u origin feature/frontend-dashboard
```

Open a pull request after the build and tests pass. Do not commit `.env` files containing secrets.

## 9. End-to-end demo checklist

- [ ] Start the backend and confirm the health endpoint responds.
- [ ] Open the dashboard and show a committed batch.
- [ ] Explain that raw log data stays off-chain.
- [ ] Open batch details and show the Merkle root and transaction status.
- [ ] Trigger verification and show the successful result.
- [ ] Run the controlled local tampering simulation.
- [ ] Trigger verification again and show the failure alert.
- [ ] Explain the system's limitation: it can identify discrepancies in committed history, but cannot guarantee that a compromised host captured every event.

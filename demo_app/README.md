# Demo Expense Tracker App

A minimal, audited expense tracker demonstrating end-to-end integration with the **TraceLedger** sidecar receiver.

---

## Features

- **Users**: Hard-coded demo accounts:
  - `alice` (password: `password123`)
  - `bob` (password: `builder456`)
- **Operations**:
  - Authenticate (successful login or audit-logged failure)
  - Add expense (category, integer paise amount, description)
  - Edit expense amount
  - Delete expense
  - Set monthly budget limit
  - Export expenses to CSV
- **Deterministic Currency Handling**:
  - All monetary values are integers in **paise** (1 INR = 100 paise; e.g. ₹150.50 = `15050` paise).
  - Floating-point values are strictly forbidden across models, database, and event payloads.
- **Reliable Audit Outbox**:
  - Every action emits a signed/hashed audit event to the sidecar receiver (`POST /events`).
  - Emitted asynchronously in background threads with a **2-second timeout**.
  - If the receiver is unreachable, events append to `data/outbox.jsonl` without failing user operations.
  - An automatic background worker drains the outbox every 10 seconds (and on every subsequent user action).
  - The UI displays a live status line: `events sent: N, queued: M`.

---

## Running the Demo App

### 1. Start the Sidecar Event Receiver
Open a terminal and launch the authenticated receiver (default `127.0.0.1:8001`):

```bash
# Windows (PowerShell)
$env:SIDECAR_API_KEY = "demo-sidecar-key"
python -m sidecar.receiver --db data/records.db

# Linux / macOS
export SIDECAR_API_KEY="demo-sidecar-key"
python -m sidecar.receiver --db data/records.db
```

### 2. Start the Demo Expense Application
In a second terminal, launch the FastAPI demo app (runs on `127.0.0.1:8002`):

```bash
# Windows (PowerShell)
$env:SIDECAR_API_KEY = "demo-sidecar-key"
python -m demo_app.main

# Linux / macOS
export SIDECAR_API_KEY="demo-sidecar-key"
python -m demo_app.main
```

### 3. Open the Web Interface
Navigate to [http://127.0.0.1:8002](http://127.0.0.1:8002) in your browser.

---

## Emitted Audit Event Types

| User Action | Event Type | Details Schema |
|---|---|---|
| Successful Login | `authentication` | `{"user": "alice", "result": "success"}` |
| Failed Login | `authentication` | `{"user": "alice", "result": "failure", "reason": "invalid_credentials"}` |
| Add Expense | `expense_created` | `{"expense_id": "...", "amount_minor": 15000, "category": "travel", "user": "alice"}` |
| Edit Expense | `expense_updated` | `{"expense_id": "...", "old_amount_minor": 15000, "new_amount_minor": 20000, "user": "alice"}` |
| Delete Expense | `expense_deleted` | `{"expense_id": "...", "amount_minor": 20000, "user": "alice"}` |
| Update Budget | `budget_changed` | `{"old_budget_minor": 5000000, "new_budget_minor": 6000000, "user": "alice"}` |
| Export Data | `data_exported` | `{"record_count": 5, "format": "csv", "user": "alice"}` |

*(Sensitive data, user passwords, tokens, and free-text description notes are never included in audit payloads.)*

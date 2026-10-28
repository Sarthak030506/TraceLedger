# TraceLedger

**Trust the evidence, not just the server.**

TraceLedger is a tamper-evident security-log integrity system. It seals security events into cryptographic Merkle trees and anchors the batch commitments onto an EVM-compatible blockchain (MST Blockchain). An independent verifier later validates off-chain logs against the on-chain commitments to detect any log tampering, alteration, deletion, or reordering.

---

## Architecture Overview

```
[Sidecar Collector] -> [Event Sanitizer & SHA-256 Hasher] -> [Off-Chain Storage]
                                 │
                                 ▼
                     [Merkle Tree & Ed25519 Signer]
                                 │
                                 ▼
                     [Backend API & Blockchain Anchor]
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
            [EVM Smart Contract]     [SQLite Metadata]
                     │
                     ▼
             [Verifier Engine] <---> [Frontend Dashboard]
```

Detailed specification documents are located in the [`docs/`](file:///docs/) directory:
- [`docs/readme.md`](file:///docs/readme.md) — Full specification and problem statement
- [`docs/person1.md`](file:///docs/person1.md) — Event collection, sanitization, and hashing specification
- [`docs/person2.md`](file:///docs/person2.md) — Merkle proofs, signatures, and batch verification specification
- [`docs/person3.md`](file:///docs/person3.md) — Blockchain smart contract and FastAPI backend specification
- [`docs/frontend.md`](file:///docs/frontend.md) — Dashboard and visualization specification
- [`INTERFACES.md`](file:///INTERFACES.md) — Inter-module interface contracts and data schemas

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for blockchain tooling / Hardhat)
- Git

### Python Virtual Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

### Blockchain Setup (Hardhat)

```bash
cd blockchain
npm install
npx hardhat test
```

---

## Project Structure

```
TraceLedger/
├── sidecar/        # Event collector, sanitizer, SHA-256 hasher, off-chain storage
├── integrity/      # Merkle tree builder, proof generator, Ed25519 signer & verifier
├── backend/        # FastAPI application, database layer, routes, and services
├── blockchain/     # Solidity smart contract, deployment scripts, tests, Hardhat config
├── frontend/       # React dashboard placeholder (later phase)
├── tests/          # Pytest test suite for collection, integrity, api, and integration
├── docs/           # Specifications and architectural documentation
├── data/           # Off-chain data store and SQLite files (gitignored)
├── INTERFACES.md   # Agreed cross-module contracts and schema definitions
├── requirements.txt
├── .env.example
└── .gitignore
```

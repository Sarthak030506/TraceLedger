"""Tests for anchoring honesty, write auth, signatures, and on-chain cross-checks."""
import pytest
from fastapi.testclient import TestClient

from backend.database import init_db
from backend.main import app
from backend.services.blockchain import AnchorError, BlockchainService, default_blockchain_service
from integrity.merkle import build_merkle_tree
from integrity.signer import commitment_signing_payload, generate_keypair, sign_batch
from sidecar.collector import ingest_many, sample_events
from sidecar.storage import RecordStore

GENESIS = {
    "batch_id": 1,
    "merkle_root": "a" * 64,
    "previous_root": "0" * 64,
    "first_sequence": 1,
    "last_sequence": 5,
    "record_count": 5,
    "timestamp": 1729000000,
}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    db = str(tmp_path / "backend.db")
    monkeypatch.setenv("BACKEND_DB_PATH", db)
    monkeypatch.setenv("SIDECAR_DB_PATH", str(tmp_path / "missing-records.db"))
    for var in ("BACKEND_API_KEY", "BATCH_SIGNER_PUBLIC_KEY"):
        monkeypatch.delenv(var, raising=False)
    init_db(db)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _go_live(monkeypatch):
    svc = default_blockchain_service
    monkeypatch.setattr(svc, "rpc_url", "http://rpc.invalid")
    monkeypatch.setattr(svc, "contract_address", "0x" + "1" * 40)
    monkeypatch.setattr(svc, "private_key", "0x" + "2" * 64)
    monkeypatch.setattr(svc, "config_errors", [])
    return svc


# ── 1. failed anchoring is never reported as confirmed ───────────────────────
def test_live_anchor_failure_returns_502_and_stores_nothing(client, monkeypatch):
    svc = _go_live(monkeypatch)
    monkeypatch.setenv("BACKEND_API_KEY", "k")

    def boom():
        raise AnchorError("Cannot reach blockchain RPC")

    monkeypatch.setattr(svc, "_get_contract", boom)
    resp = client.post("/api/batches", json=GENESIS, headers={"X-API-Key": "k"})
    assert resp.status_code == 502
    assert "Cannot reach" in resp.json()["detail"]
    assert client.get("/api/batches").json()["total"] == 0


def test_partial_blockchain_config_is_rejected(monkeypatch):
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.delenv("MST_RPC_URL", raising=False)
    monkeypatch.delenv("SEPOLIA_RPC_URL", raising=False)
    svc = BlockchainService(private_key="0x" + "2" * 64)
    assert svc.mode == "misconfigured"
    with pytest.raises(AnchorError):
        svc.anchor_batch(GENESIS)


def test_bad_chain_id_does_not_crash_import(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "not-a-number")
    svc = BlockchainService()
    assert svc.mode == "misconfigured"
    assert "CHAIN_ID" in svc.config_errors[0]


# ── 2. write authentication ──────────────────────────────────────────────────
def test_submit_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("BACKEND_API_KEY", "s3cret")
    assert client.post("/api/batches", json=GENESIS).status_code == 401
    assert client.post("/api/batches", json=GENESIS, headers={"X-API-Key": "nope"}).status_code == 401
    assert client.post("/api/batches", json=GENESIS, headers={"X-API-Key": "s3cret"}).status_code == 201


def test_live_mode_without_api_key_refuses_writes(client, monkeypatch):
    _go_live(monkeypatch)
    resp = client.post("/api/batches", json=GENESIS)
    assert resp.status_code == 503
    assert "BACKEND_API_KEY" in resp.json()["detail"]


def test_reads_stay_public(client, monkeypatch):
    monkeypatch.setenv("BACKEND_API_KEY", "s3cret")
    assert client.get("/api/batches").status_code == 200
    assert client.get("/api/health").json()["anchor_mode"] == "simulated"


# ── 3. verification is anchored to the chain and labels its evidence ────────
def _sample_batch():
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    store.close()
    payload = dict(GENESIS, merkle_root=build_merkle_tree(hashes)["merkle_root"], record_hashes=hashes)
    return payload, records


def _mark_confirmed(batch_id):
    from backend.database import get_connection
    conn = get_connection()
    conn.execute("UPDATE batches SET status = 'confirmed' WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()


def test_verify_uses_onchain_root_and_detects_metadata_tampering(client, monkeypatch):
    payload, records = _sample_batch()
    assert client.post("/api/batches", json=payload).status_code == 201
    _mark_confirmed(1)

    svc = _go_live(monkeypatch)
    monkeypatch.setattr(svc, "private_key", None)  # read_only
    onchain = {k: payload[k] for k in ("merkle_root", "previous_root", "first_sequence", "last_sequence", "record_count")}
    monkeypatch.setattr(svc, "get_onchain_batch", lambda bid: dict(onchain, batch_id=bid))

    ok = client.post("/api/batches/1/verify", json={"records": records}).json()
    assert ok["verified"] is True
    assert ok["onchain_checked"] is True
    assert ok["verification_source"] == "provided_records"

    # Chain says a different root: off-chain metadata can no longer vouch for itself
    monkeypatch.setattr(svc, "get_onchain_batch", lambda bid: dict(onchain, batch_id=bid, merkle_root="f" * 64))
    bad = client.post("/api/batches/1/verify", json={"records": records}).json()
    assert bad["verified"] is False
    assert bad["expected_root"] == "f" * 64
    assert any("disagrees with chain" in e for e in bad["errors"])


def test_verify_reports_missing_onchain_batch(client, monkeypatch):
    payload, records = _sample_batch()
    client.post("/api/batches", json=payload)
    _mark_confirmed(1)
    svc = _go_live(monkeypatch)
    monkeypatch.setattr(svc, "get_onchain_batch", lambda bid: None)
    res = client.post("/api/batches/1/verify", json={"records": records}).json()
    assert res["verified"] is False
    assert any("not committed on-chain" in e for e in res["errors"])


def test_leaf_hash_fallback_is_labelled(client):
    payload, _ = _sample_batch()
    client.post("/api/batches", json=payload)
    res = client.post("/api/batches/1/verify", json={}).json()
    assert res["verified"] is True
    assert res["verification_source"] == "leaf_hashes"
    assert res["onchain_checked"] is False
    assert "not" in res["message"]


# ── 4. signatures ────────────────────────────────────────────────────────────
def test_signature_enforced_when_public_key_configured(client, monkeypatch):
    priv, pub = generate_keypair()
    monkeypatch.setenv("BATCH_SIGNER_PUBLIC_KEY", pub)

    assert client.post("/api/batches", json=GENESIS).status_code == 400  # unsigned
    forged = dict(GENESIS, signature=sign_batch(commitment_signing_payload(dict(GENESIS, record_count=6)), priv))
    assert client.post("/api/batches", json=forged).status_code == 400

    signed = dict(GENESIS, signature=sign_batch(commitment_signing_payload(GENESIS), priv))
    assert client.post("/api/batches", json=signed).status_code == 201

    res = client.post("/api/batches/1/verify", json={"records": []}).json()
    assert res["signature_valid"] is True


def test_signature_must_be_hex(client):
    resp = client.post("/api/batches", json=dict(GENESIS, signature="not-hex"))
    assert resp.status_code == 422


# ── 6. leaf count is bound to the commitment ─────────────────────────────────
def test_record_hashes_must_match_count_and_root(client):
    payload, _ = _sample_batch()
    short = dict(payload, record_hashes=payload["record_hashes"][:4])
    assert client.post("/api/batches", json=short).status_code == 400
    wrong_root = dict(payload, merkle_root="b" * 64)
    assert client.post("/api/batches", json=wrong_root).status_code == 400


def test_duplicated_last_leaf_does_not_verify(client):
    payload, records = _sample_batch()
    client.post("/api/batches", json=payload)
    # 5 leaves duplicate the last at the bottom level; appending a copy keeps the root
    padded = records + [dict(records[-1])]
    res = client.post("/api/batches/1/verify", json={"records": padded}).json()
    assert res["verified"] is False
    assert any("count mismatch" in e.lower() or "duplicate" in e.lower() for e in res["errors"])


# ── 5. sequence continuity between batches ───────────────────────────────────
def test_sequence_gap_between_batches_rejected(client):
    client.post("/api/batches", json=GENESIS)
    gap = {
        "batch_id": 2, "merkle_root": "b" * 64, "previous_root": "a" * 64,
        "first_sequence": 8, "last_sequence": 10, "record_count": 3,
    }
    resp = client.post("/api/batches", json=gap)
    assert resp.status_code == 400
    assert "sequence gap" in resp.json()["detail"].lower()


# ── 7. the chain is the source of truth for the batch sequence ──────────────
class _FakeChain:
    """Stands in for a live contract that already holds some batches."""

    def __init__(self, batches):
        self.batches = {b["batch_id"]: b for b in batches}

    def install(self, svc, monkeypatch):
        monkeypatch.setattr(svc, "latest_onchain_batch_id", lambda: max(self.batches, default=0))
        monkeypatch.setattr(svc, "get_onchain_batch", lambda bid: self.batches.get(bid))
        monkeypatch.setattr(svc, "get_onchain_tx_hash", lambda bid, block: "0x" + f"{bid:064x}")

        def anchor(batch):
            self.batches[batch["batch_id"]] = {k: batch[k] for k in (
                "batch_id", "merkle_root", "previous_root", "first_sequence", "last_sequence", "record_count", "timestamp")}
            return {"transaction_hash": "0x" + "ab" * 32, "block_number": 99, "status": "confirmed"}

        monkeypatch.setattr(svc, "anchor_batch", anchor)


def _onchain(bid, root, prev, first, last):
    return {"batch_id": bid, "merkle_root": root, "previous_root": prev, "first_sequence": first,
            "last_sequence": last, "record_count": last - first + 1, "timestamp": 1729000000 + bid,
            "signature": "", "block_number": 100 + bid}


def test_wiped_database_continues_from_chain(client, monkeypatch):
    """An empty database must not try to re-submit batch #1 to a contract already at #2."""
    svc = _go_live(monkeypatch)
    monkeypatch.setenv("BACKEND_API_KEY", "k")
    chain = _FakeChain([_onchain(1, "a" * 64, "0" * 64, 1, 5), _onchain(2, "b" * 64, "a" * 64, 6, 10)])
    chain.install(svc, monkeypatch)
    h = {"X-API-Key": "k"}

    # Re-submitting #1 is correctly refused: the chain already has it
    retry = client.post("/api/batches", json=GENESIS, headers=h)
    assert retry.status_code == 400 and "expected 3" in retry.json()["detail"]

    nxt = {"batch_id": 3, "merkle_root": "c" * 64, "previous_root": "b" * 64,
           "first_sequence": 11, "last_sequence": 15, "record_count": 5}
    ok = client.post("/api/batches", json=nxt, headers=h)
    assert ok.status_code == 201 and ok.json()["status"] == "confirmed"

    listed = client.get("/api/batches").json()
    assert listed["total"] == 3
    imported = {b["batch_id"]: b for b in listed["batches"]}
    assert imported[1]["transaction_hash"] == "0x" + f"{1:064x}" and imported[1]["merkle_root"] == "a" * 64
    assert imported[3]["transaction_hash"].startswith("0x")


def test_head_endpoint_imports_and_reports(client, monkeypatch):
    svc = _go_live(monkeypatch)
    _FakeChain([_onchain(1, "a" * 64, "0" * 64, 1, 5)]).install(svc, monkeypatch)
    res = client.get("/api/batches/head").json()
    assert res["head"]["batch_id"] == 1 and res["imported_from_chain"] == 1
    assert res["anchor_mode"] == "live" and res["sync_error"] is None
    # Idempotent
    assert client.get("/api/batches/head").json()["imported_from_chain"] == 0


def test_head_endpoint_empty_when_nothing_anchored(client):
    res = client.get("/api/batches/head").json()
    assert res["head"] is None and res["anchor_mode"] == "simulated"


def test_database_ahead_of_chain_is_a_conflict(client, monkeypatch):
    """A database from another contract must not silently corrupt the chain."""
    client.post("/api/batches", json=GENESIS)  # simulated batch #1 in the db
    svc = _go_live(monkeypatch)
    monkeypatch.setenv("BACKEND_API_KEY", "k")
    _FakeChain([]).install(svc, monkeypatch)  # fresh contract at #0

    nxt = {"batch_id": 2, "merkle_root": "b" * 64, "previous_root": "a" * 64,
           "first_sequence": 6, "last_sequence": 10, "record_count": 5}
    res = client.post("/api/batches", json=nxt, headers={"X-API-Key": "k"})
    assert res.status_code == 409 and "different contract" in res.json()["detail"]

    head = client.get("/api/batches/head").json()
    assert "different contract" in head["sync_error"]


def test_chain_outage_blocks_submit_but_not_reads(client, monkeypatch):
    svc = _go_live(monkeypatch)
    monkeypatch.setenv("BACKEND_API_KEY", "k")

    def down():
        raise AnchorError("RPC unreachable")

    monkeypatch.setattr(svc, "latest_onchain_batch_id", down)
    assert client.post("/api/batches", json=GENESIS, headers={"X-API-Key": "k"}).status_code == 502
    assert client.get("/api/batches").status_code == 200
    head = client.get("/api/batches/head")
    assert head.status_code == 200 and "RPC unreachable" in head.json()["sync_error"]

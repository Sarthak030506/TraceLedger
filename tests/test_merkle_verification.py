"""Unit tests for Merkle tree generation, inclusion proofs, Ed25519 signatures, and batch verification (Person 2)."""
import copy
import hashlib
import pytest

from integrity.merkle import build_merkle_tree, hash_pair, validate_hash_hex
from integrity.proofs import generate_proof, verify_inclusion
from integrity.signer import generate_keypair, sign_batch, verify_signature
from integrity.verifier import verify_batch
from sidecar.collector import ingest_many, sample_events
from sidecar.hasher import hash_record
from sidecar.storage import RecordStore


def _sample_hashes(count: int) -> list[str]:
    """Helper generating deterministic SHA-256 test hashes."""
    return [hashlib.sha256(f"record-{i}".encode("utf-8")).hexdigest() for i in range(count)]


# ==============================================================================
# Merkle Tree Construction Tests
# ==============================================================================

def test_merkle_tree_empty_and_single_leaf():
    """Empty list and single leaf edge cases."""
    empty_tree = build_merkle_tree([])
    assert empty_tree["merkle_root"] == "0" * 64
    assert empty_tree["leaves"] == []
    assert empty_tree["proofs"] == []

    single = _sample_hashes(1)
    single_tree = build_merkle_tree(single)
    assert single_tree["merkle_root"] == single[0]
    assert single_tree["leaves"] == single
    assert single_tree["proofs"] == [[]]


def test_merkle_tree_deterministic():
    """Same input produces identical root; changes alter root completely."""
    hashes = _sample_hashes(5)
    tree1 = build_merkle_tree(hashes)
    tree2 = build_merkle_tree(hashes)
    assert tree1["merkle_root"] == tree2["merkle_root"]

    # Altering one hash alters root
    tampered_hashes = list(hashes)
    tampered_hashes[2] = hashlib.sha256(b"tampered").hexdigest()
    tampered_tree = build_merkle_tree(tampered_hashes)
    assert tampered_tree["merkle_root"] != tree1["merkle_root"]

    # Reordering hashes alters root
    reordered_hashes = list(reversed(hashes))
    reordered_tree = build_merkle_tree(reordered_hashes)
    assert reordered_tree["merkle_root"] != tree1["merkle_root"]


def test_merkle_tree_formatting_and_pair_hashing():
    """Check standard internal pair hashing: SHA256(left_node_bytes + right_node_bytes)."""
    h0 = hashlib.sha256(b"left").hexdigest()
    h1 = hashlib.sha256(b"right").hexdigest()
    expected_pair = hashlib.sha256(bytes.fromhex(h0) + bytes.fromhex(h1)).hexdigest()

    assert hash_pair(h0, h1) == expected_pair

    tree = build_merkle_tree([h0, h1])
    assert tree["merkle_root"] == expected_pair
    assert not tree["merkle_root"].startswith("0x")
    assert len(tree["merkle_root"]) == 64


def test_merkle_tree_odd_leaf_duplication():
    """Verify odd leaf counts duplicate the last leaf at that level."""
    h = _sample_hashes(3)
    # Level 0: [h0, h1, h2] -> padded to [h0, h1, h2, h2]
    p0 = hash_pair(h[0], h[1])
    p1 = hash_pair(h[2], h[2])
    expected_root = hash_pair(p0, p1)

    tree = build_merkle_tree(h)
    assert tree["merkle_root"] == expected_root


def test_validate_hash_hex_rejects_malformed_inputs():
    """Verify strict validation of 64-char hex strings."""
    with pytest.raises(ValueError, match="0x"):
        validate_hash_hex("0x" + "a" * 64)
    with pytest.raises(ValueError):
        validate_hash_hex("short")
    with pytest.raises(ValueError):
        validate_hash_hex("g" * 64)
    with pytest.raises(TypeError):
        validate_hash_hex(12345)


# ==============================================================================
# Inclusion Proof Tests
# ==============================================================================

@pytest.mark.parametrize("leaf_count", [1, 2, 3, 4, 5, 7, 8, 9, 16, 17])
def test_all_leaves_inclusion_proofs_verify(leaf_count):
    """Every leaf in any size Merkle tree must produce a valid inclusion proof."""
    hashes = _sample_hashes(leaf_count)
    tree = build_merkle_tree(hashes)
    root = tree["merkle_root"]

    for idx, leaf_hash in enumerate(hashes):
        proof = tree["proofs"][idx]
        assert verify_inclusion(leaf_hash, proof, root) is True

        # generate_proof helper
        proof_direct = generate_proof(hashes, idx)
        assert proof_direct == proof


def test_inclusion_proof_fails_on_tampered_leaf_or_root():
    """Invalid leaf hash, altered root, or broken proof step must fail verification."""
    hashes = _sample_hashes(5)
    tree = build_merkle_tree(hashes)
    root = tree["merkle_root"]
    proof = tree["proofs"][0]

    # Tampered leaf
    bad_leaf = hashlib.sha256(b"wrong").hexdigest()
    assert verify_inclusion(bad_leaf, proof, root) is False

    # Tampered root
    bad_root = hashlib.sha256(b"fake-root").hexdigest()
    assert verify_inclusion(hashes[0], proof, bad_root) is False

    # Tampered proof step hash
    tampered_proof = copy.deepcopy(proof)
    tampered_proof[0]["hash"] = "f" * 64
    assert verify_inclusion(hashes[0], tampered_proof, root) is False

    # Tampered proof step position
    inverted_proof = copy.deepcopy(proof)
    inverted_proof[0]["position"] = "left" if inverted_proof[0]["position"] == "right" else "right"
    assert verify_inclusion(hashes[0], inverted_proof, root) is False


# ==============================================================================
# Ed25519 Digital Signature Tests
# ==============================================================================

def test_ed25519_keypair_generation_and_signing():
    """Keypair generation, batch signing, and public key verification."""
    priv_hex, pub_hex = generate_keypair()
    assert len(priv_hex) == 64
    assert len(pub_hex) == 64

    batch_metadata = {
        "batch_id": 1,
        "merkle_root": "a" * 64,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 10,
        "record_count": 10,
        "timestamp": 1729000000,
    }

    sig_hex = sign_batch(batch_metadata, priv_hex)
    assert len(sig_hex) == 128
    assert all(c in "0123456789abcdef" for c in sig_hex)

    # Valid verification
    assert verify_signature(batch_metadata, sig_hex, pub_hex) is True


def test_ed25519_signature_detects_metadata_tampering():
    """Modifying any signed field in the batch commitment causes signature rejection."""
    priv_hex, pub_hex = generate_keypair()
    batch_metadata = {
        "batch_id": 1,
        "merkle_root": "a" * 64,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 10,
        "record_count": 10,
        "timestamp": 1729000000,
    }
    sig_hex = sign_batch(batch_metadata, priv_hex)

    # Tamper with batch_id
    tampered_meta = dict(batch_metadata, batch_id=2)
    assert verify_signature(tampered_meta, sig_hex, pub_hex) is False

    # Tamper with merkle_root
    tampered_meta = dict(batch_metadata, merkle_root="b" * 64)
    assert verify_signature(tampered_meta, sig_hex, pub_hex) is False

    # Tamper with record_count
    tampered_meta = dict(batch_metadata, record_count=9)
    assert verify_signature(tampered_meta, sig_hex, pub_hex) is False

    # Corrupted signature string
    corrupted_sig = "0" * 128
    assert verify_signature(batch_metadata, corrupted_sig, pub_hex) is False

    # Different public key
    _, other_pub_hex = generate_keypair()
    assert verify_signature(batch_metadata, sig_hex, other_pub_hex) is False


# ==============================================================================
# Batch Verifier & Tamper Detection Tests
# ==============================================================================

def test_verify_batch_success():
    """Unmodified records matching expected root verify cleanly."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    root = build_merkle_tree(hashes)["merkle_root"]

    res = verify_batch(records, root)
    assert res["verified"] is True
    assert res["expected_root"] == root
    assert res["computed_root"] == root
    assert res["record_count"] == 5
    assert res["errors"] == []


def test_verify_batch_detects_altered_content():
    """Altering details inside a record changes its hash and triggers a root mismatch."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    root = build_merkle_tree(hashes)["merkle_root"]

    # Tamper with record 2 details
    tampered_records = copy.deepcopy(records)
    tampered_records[1]["details"]["user"] = "attacker"

    res = verify_batch(tampered_records, root)
    assert res["verified"] is False
    assert res["computed_root"] != root
    assert any("tampered" in err.lower() or "mismatch" in err.lower() for err in res["errors"])


def test_verify_batch_detects_missing_records():
    """Deleting a record creates a sequence number gap and triggers verification failure."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    root = build_merkle_tree(hashes)["merkle_root"]

    # Drop record sequence 3 (leaving sequences 1, 2, 4, 5)
    gapped_records = [r for r in records if r["sequence_number"] != 3]

    res = verify_batch(gapped_records, root)
    assert res["verified"] is False
    assert any("missing" in err.lower() for err in res["errors"])


def test_verify_batch_detects_reordered_records():
    """Reordering records fails sequence ordering and alters tree root."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    root = build_merkle_tree(hashes)["merkle_root"]

    # Swap record 1 and 2
    swapped_records = list(records)
    swapped_records[0], swapped_records[1] = swapped_records[1], swapped_records[0]

    res = verify_batch(swapped_records, root)
    assert res["verified"] is False
    assert any("reordered" in err.lower() for err in res["errors"])


def test_verify_batch_detects_duplicate_records():
    """Duplicate sequence numbers trigger duplicate detection error."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    records = store.get_records()
    root = "a" * 64

    # Duplicate sequence 2
    dup_records = list(records)
    dup_records[2] = copy.deepcopy(dup_records[1])

    res = verify_batch(dup_records, root)
    assert res["verified"] is False
    assert any("duplicate" in err.lower() for err in res["errors"])


def test_verify_batch_handles_empty_and_bad_roots():
    """Invalid expected root format or empty list gracefully report errors."""
    res_bad = verify_batch([], "invalid_root")
    assert res_bad["verified"] is False
    assert any("invalid" in err.lower() for err in res_bad["errors"])

    # Empty list with 64 zeros matches empty root
    res_empty_match = verify_batch([], "0" * 64)
    assert res_empty_match["verified"] is True

    # Empty list with non-zero root fails
    res_empty_mismatch = verify_batch([], "a" * 64)
    assert res_empty_mismatch["verified"] is False

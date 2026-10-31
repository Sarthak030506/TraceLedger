"""Blockchain service for anchoring Merkle roots to MST Blockchain via Web3.py.

Conforms to the INTERFACES.md cross-module contract:
- Prepend '0x' to 64-char hex strings at the blockchain boundary for bytes32 compatibility.
- Strips '0x' when exposing data back to internal Python services and REST API.
- Supports live EVM testnet (MST) as well as offline simulation mode for local testing.

Modes (see ``BlockchainService.mode``):
- ``live``:      RPC_URL, CONTRACT_ADDRESS and PRIVATE_KEY are all set -> real transactions.
- ``read_only``: RPC_URL and CONTRACT_ADDRESS set, no key -> on-chain reads only, writes fail.
- ``simulated``: nothing configured -> deterministic fake anchors, marked status="simulated".
Any other combination (or an unparsable CHAIN_ID) is a configuration error and anchoring
fails loudly instead of silently falling back to a fake anchor.
"""
import hashlib
import os
import time
from typing import Any

from web3 import Web3

# Minimal ABI for TraceLedger.sol
TRACELEDGER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "batchId", "type": "uint256"},
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "bytes32", "name": "previousRoot", "type": "bytes32"},
            {"internalType": "uint256", "name": "firstSequence", "type": "uint256"},
            {"internalType": "uint256", "name": "lastSequence", "type": "uint256"},
            {"internalType": "uint256", "name": "recordCount", "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
        ],
        "name": "commitBatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "batchId", "type": "uint256"}],
        "name": "getBatch",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "batchId", "type": "uint256"},
                    {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "previousRoot", "type": "bytes32"},
                    {"internalType": "uint256", "name": "firstSequence", "type": "uint256"},
                    {"internalType": "uint256", "name": "lastSequence", "type": "uint256"},
                    {"internalType": "uint256", "name": "recordCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                    {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
                ],
                "internalType": "struct TraceLedger.Batch",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "latestBatchId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def to_bytes32(hex_str: str) -> bytes:
    """Format a 64-char hex string as 32 bytes for Solidity."""
    clean = hex_str.strip().lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    return bytes.fromhex(clean.zfill(64))


def _to_hex(value: Any) -> str:
    """Bytes-like -> lowercase hex without '0x' (HexBytes.hex() prefixing varies by version)."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    return str(value).lower().removeprefix("0x")


class AnchorError(RuntimeError):
    """Raised when a batch cannot be anchored on-chain. Never silently simulated."""


class BlockchainService:
    """Service to anchor commitments to the blockchain with an explicit simulation mode."""

    def __init__(
        self,
        rpc_url: str | None = None,
        contract_address: str | None = None,
        private_key: str | None = None,
        chain_id: int | None = None,
    ):
        self.config_errors: list[str] = []
        self.rpc_url = (
            rpc_url
            or os.environ.get("MST_RPC_URL")
            or os.environ.get("RPC_URL")
            or os.environ.get("SEPOLIA_RPC_URL")
        )
        self.contract_address = contract_address or os.environ.get("CONTRACT_ADDRESS")
        self.private_key = private_key or os.environ.get("PRIVATE_KEY") or os.environ.get("TESTNET_PRIVATE_KEY")
        self.chain_id = chain_id or self._env_chain_id()

        self.w3: Web3 | None = None
        self.contract: Any = None
        self._mock_batches: dict[int, dict[str, Any]] = {}

        if self.private_key and not (self.rpc_url and self.contract_address):
            self.config_errors.append("PRIVATE_KEY is set but RPC_URL and/or CONTRACT_ADDRESS are missing")
        elif self.contract_address and not self.rpc_url:
            self.config_errors.append("CONTRACT_ADDRESS is set but RPC_URL is missing")

    def _env_chain_id(self) -> int | None:
        raw = os.environ.get("CHAIN_ID") or os.environ.get("MST_CHAIN_ID")
        if not raw or raw.strip() == "0":
            return None
        try:
            return int(raw.strip(), 0)
        except ValueError:
            self.config_errors.append(f"CHAIN_ID is not an integer: {raw!r}")
            return None

    @property
    def mode(self) -> str:
        """One of: live, read_only, simulated, misconfigured."""
        if self.config_errors:
            return "misconfigured"
        if self.rpc_url and self.contract_address:
            return "live" if self.private_key else "read_only"
        return "simulated"

    @property
    def can_write(self) -> bool:
        return self.mode == "live"

    def _get_contract(self) -> Any:
        """Connect lazily so a transient RPC outage at startup is not permanent."""
        if self.contract is not None and self.w3 is not None:
            return self.contract
        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        # MST chains are proof-of-authority (long extraData)
        try:
            from web3.middleware import ExtraDataToPOAMiddleware as poa
        except ImportError:  # web3 < 7
            from web3.middleware import geth_poa_middleware as poa
        w3.middleware_onion.inject(poa, layer=0)
        if not w3.is_connected():
            raise AnchorError(f"Cannot reach blockchain RPC at {self.rpc_url}")
        self.w3 = w3
        self.contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address), abi=TRACELEDGER_ABI
        )
        return self.contract

    def is_connected(self) -> bool:
        """Check if connected to a live Web3 node."""
        if self.mode not in ("live", "read_only"):
            return False
        try:
            self._get_contract()
            return self.w3 is not None and self.w3.is_connected()
        except Exception:
            return False

    def anchor_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        """Submit batch commitment to the blockchain.

        In live mode, broadcasts a transaction and raises AnchorError on any failure.
        In simulated mode, creates a deterministic mock anchor with status="simulated".
        """
        batch_id = batch["batch_id"]
        merkle_root = batch["merkle_root"]
        previous_root = batch.get("previous_root", "0" * 64)
        first_seq = batch["first_sequence"]
        last_seq = batch["last_sequence"]
        record_count = batch["record_count"]
        timestamp = batch.get("timestamp") or int(time.time())
        signature = batch.get("signature") or ""

        mode = self.mode
        if mode == "misconfigured":
            raise AnchorError("Blockchain misconfigured: " + "; ".join(self.config_errors))
        if mode == "read_only":
            raise AnchorError("PRIVATE_KEY is not set; cannot sign anchoring transactions")

        if mode == "live":
            try:
                contract = self._get_contract()
                account = self.w3.eth.account.from_key(self.private_key)
                sig_bytes = bytes.fromhex(signature) if signature else b""

                tx = contract.functions.commitBatch(
                    batch_id,
                    to_bytes32(merkle_root),
                    to_bytes32(previous_root),
                    first_seq,
                    last_seq,
                    record_count,
                    timestamp,
                    sig_bytes,
                ).build_transaction({
                    "from": account.address,
                    "nonce": self.w3.eth.get_transaction_count(account.address, "pending"),
                    "chainId": self.chain_id or self.w3.eth.chain_id,
                })

                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
                raw_tx = getattr(signed_tx, "raw_transaction", None) or signed_tx.rawTransaction
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            except AnchorError:
                raise
            except Exception as exc:
                raise AnchorError(f"On-chain anchoring failed: {exc}") from exc

            tx_hex = "0x" + _to_hex(tx_hash)
            if receipt.status != 1:
                raise AnchorError(f"Anchoring transaction {tx_hex} reverted")
            return {
                "transaction_hash": tx_hex,
                "block_number": receipt.blockNumber,
                "status": "confirmed",
            }

        # Explicit simulation mode (no blockchain configured at all)
        tx_seed = f"mst-tx:{batch_id}:{merkle_root}:{timestamp}".encode("utf-8")
        simulated_tx_hash = "0x" + hashlib.sha256(tx_seed).hexdigest()
        simulated_block = 10000 + batch_id

        self._mock_batches[batch_id] = {
            "batch_id": batch_id,
            "merkle_root": merkle_root.lower(),
            "previous_root": previous_root.lower(),
            "first_sequence": first_seq,
            "last_sequence": last_seq,
            "record_count": record_count,
            "timestamp": timestamp,
            "signature": signature,
            "block_number": simulated_block,
        }

        return {
            "transaction_hash": simulated_tx_hash,
            "block_number": simulated_block,
            "status": "simulated",
        }

    def get_onchain_batch(self, batch_id: int) -> dict[str, Any] | None:
        """Fetch a batch commitment from the contract (or the simulation cache).

        Returns None if the batch does not exist on-chain. Raises AnchorError if the
        chain is configured but cannot be read, so an outage is never mistaken for
        a missing batch.
        """
        if self.mode == "simulated":
            return self._mock_batches.get(batch_id)
        if self.mode == "misconfigured":
            raise AnchorError("Blockchain misconfigured: " + "; ".join(self.config_errors))

        contract = self._get_contract()
        try:
            if batch_id > contract.functions.latestBatchId().call():
                return None
            res = contract.functions.getBatch(batch_id).call()
        except Exception as exc:
            raise AnchorError(f"Failed to read batch {batch_id} from chain: {exc}") from exc
        # res: (batchId, merkleRoot, previousRoot, firstSeq, lastSeq, recordCount, timestamp, signature, blockNumber)
        return {
            "batch_id": res[0],
            "merkle_root": _to_hex(res[1]),
            "previous_root": _to_hex(res[2]),
            "first_sequence": res[3],
            "last_sequence": res[4],
            "record_count": res[5],
            "timestamp": res[6],
            "signature": _to_hex(res[7]),
            "block_number": res[8],
        }


# Default singleton instance
default_blockchain_service = BlockchainService()


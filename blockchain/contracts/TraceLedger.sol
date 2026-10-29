// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TraceLedger
 * @dev Smart contract for anchoring Merkle roots and batch metadata on-chain.
 * Part of the TraceLedger tamper-evident security logging infrastructure.
 */
contract TraceLedger {
    address public owner;

    struct Batch {
        uint256 batchId;
        bytes32 merkleRoot;
        bytes32 previousRoot;
        uint256 firstSequence;
        uint256 lastSequence;
        uint256 recordCount;
        uint256 timestamp;
        bytes signature;
        uint256 blockNumber;
    }

    // batchId => Batch mapping
    mapping(uint256 => Batch) private batches;

    // Track the latest committed batch ID
    uint256 public latestBatchId;

    // Events
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event BatchCommitted(
        uint256 indexed batchId,
        bytes32 indexed merkleRoot,
        bytes32 previousRoot,
        uint256 firstSequence,
        uint256 lastSequence,
        uint256 recordCount,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "TraceLedger: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "TraceLedger: new owner is the zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /**
     * @notice Commits a new batch root to the blockchain.
     * @dev Enforces monotonic batchId, previousRoot chaining, and sequence consistency.
     */
    function commitBatch(
        uint256 batchId,
        bytes32 merkleRoot,
        bytes32 previousRoot,
        uint256 firstSequence,
        uint256 lastSequence,
        uint256 recordCount,
        uint256 timestamp,
        bytes calldata signature
    ) external onlyOwner {
        require(batchId == latestBatchId + 1, "TraceLedger: non-monotonic batchId");
        require(merkleRoot != bytes32(0), "TraceLedger: empty merkleRoot");
        require(recordCount > 0, "TraceLedger: empty batch recordCount");
        require(
            lastSequence - firstSequence + 1 == recordCount,
            "TraceLedger: sequence range does not match recordCount"
        );

        if (batchId == 1) {
            require(previousRoot == bytes32(0), "TraceLedger: genesis batch previousRoot must be zero");
        } else {
            require(
                previousRoot == batches[latestBatchId].merkleRoot,
                "TraceLedger: previousRoot does not match preceding batch root"
            );
        }

        batches[batchId] = Batch({
            batchId: batchId,
            merkleRoot: merkleRoot,
            previousRoot: previousRoot,
            firstSequence: firstSequence,
            lastSequence: lastSequence,
            recordCount: recordCount,
            timestamp: timestamp,
            signature: signature,
            blockNumber: block.number
        });

        latestBatchId = batchId;

        emit BatchCommitted(
            batchId,
            merkleRoot,
            previousRoot,
            firstSequence,
            lastSequence,
            recordCount,
            timestamp
        );
    }

    /**
     * @notice Retrieves batch details by batchId.
     */
    function getBatch(uint256 batchId) external view returns (Batch memory) {
        require(batchId > 0 && batchId <= latestBatchId, "TraceLedger: batch does not exist");
        return batches[batchId];
    }

    /**
     * @notice Retrieves the latest committed batch.
     */
    function getLatestBatch() external view returns (Batch memory) {
        require(latestBatchId > 0, "TraceLedger: no batches committed yet");
        return batches[latestBatchId];
    }

    /**
     * @notice Checks if a batch ID has been committed.
     */
    function isBatchCommitted(uint256 batchId) external view returns (bool) {
        return (batchId > 0 && batchId <= latestBatchId);
    }
}

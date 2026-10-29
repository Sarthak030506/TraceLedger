const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("TraceLedger Smart Contract", function () {
  let traceLedger;
  let owner, user;

  const ZERO_BYTES32 = "0x0000000000000000000000000000000000000000000000000000000000000000";
  const ROOT_1 = "0x1111111111111111111111111111111111111111111111111111111111111111";
  const ROOT_2 = "0x2222222222222222222222222222222222222222222222222222222222222222";
  const DUMMY_SIG = "0xabcdef";

  beforeEach(async function () {
    [owner, user] = await ethers.getSigners();
    const TraceLedger = await ethers.getContractFactory("TraceLedger");
    traceLedger = await TraceLedger.deploy();
    await traceLedger.waitForDeployment();
  });

  it("sets the deployer as owner", async function () {
    expect(await traceLedger.owner()).to.equal(owner.address);
    expect(await traceLedger.latestBatchId()).to.equal(0);
  });

  it("commits a genesis batch successfully", async function () {
    const tx = await traceLedger.commitBatch(
      1,
      ROOT_1,
      ZERO_BYTES32,
      1,
      5,
      5,
      1729000000,
      DUMMY_SIG
    );
    await tx.wait();

    expect(await traceLedger.latestBatchId()).to.equal(1);
    expect(await traceLedger.isBatchCommitted(1)).to.be.true;

    const batch = await traceLedger.getBatch(1);
    expect(batch.batchId).to.equal(1);
    expect(batch.merkleRoot).to.equal(ROOT_1);
    expect(batch.previousRoot).to.equal(ZERO_BYTES32);
    expect(batch.firstSequence).to.equal(1);
    expect(batch.lastSequence).to.equal(5);
    expect(batch.recordCount).to.equal(5);
    expect(batch.signature).to.equal(DUMMY_SIG);
  });

  it("commits chained batches successfully", async function () {
    await traceLedger.commitBatch(1, ROOT_1, ZERO_BYTES32, 1, 5, 5, 1729000000, DUMMY_SIG);
    await traceLedger.commitBatch(2, ROOT_2, ROOT_1, 6, 10, 5, 1729000100, DUMMY_SIG);

    expect(await traceLedger.latestBatchId()).to.equal(2);
    const latest = await traceLedger.getLatestBatch();
    expect(latest.batchId).to.equal(2);
    expect(latest.merkleRoot).to.equal(ROOT_2);
    expect(latest.previousRoot).to.equal(ROOT_1);
  });

  it("rejects non-owner submissions", async function () {
    await expect(
      traceLedger.connect(user).commitBatch(
        1,
        ROOT_1,
        ZERO_BYTES32,
        1,
        5,
        5,
        1729000000,
        DUMMY_SIG
      )
    ).to.be.revertedWith("TraceLedger: caller is not the owner");
  });

  it("rejects non-monotonic batch IDs", async function () {
    // Skipping batch 1
    await expect(
      traceLedger.commitBatch(2, ROOT_1, ZERO_BYTES32, 1, 5, 5, 1729000000, DUMMY_SIG)
    ).to.be.revertedWith("TraceLedger: non-monotonic batchId");

    // Commit batch 1
    await traceLedger.commitBatch(1, ROOT_1, ZERO_BYTES32, 1, 5, 5, 1729000000, DUMMY_SIG);

    // Duplicate batch 1
    await expect(
      traceLedger.commitBatch(1, ROOT_2, ROOT_1, 6, 10, 5, 1729000100, DUMMY_SIG)
    ).to.be.revertedWith("TraceLedger: non-monotonic batchId");
  });

  it("rejects broken previousRoot chain", async function () {
    await traceLedger.commitBatch(1, ROOT_1, ZERO_BYTES32, 1, 5, 5, 1729000000, DUMMY_SIG);

    const WRONG_ROOT = "0x9999999999999999999999999999999999999999999999999999999999999999";
    await expect(
      traceLedger.commitBatch(2, ROOT_2, WRONG_ROOT, 6, 10, 5, 1729000100, DUMMY_SIG)
    ).to.be.revertedWith("TraceLedger: previousRoot does not match preceding batch root");
  });

  it("rejects invalid sequence count consistency", async function () {
    // firstSequence=1, lastSequence=5 => count must be 5, not 4
    await expect(
      traceLedger.commitBatch(1, ROOT_1, ZERO_BYTES32, 1, 5, 4, 1729000000, DUMMY_SIG)
    ).to.be.revertedWith("TraceLedger: sequence range does not match recordCount");
  });
});

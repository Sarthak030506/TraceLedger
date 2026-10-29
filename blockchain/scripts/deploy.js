const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log(`Deploying TraceLedger with account: ${deployer.address}`);

  const TraceLedger = await hre.ethers.getContractFactory("TraceLedger");
  const traceLedger = await TraceLedger.deploy();

  await traceLedger.waitForDeployment();
  const address = await traceLedger.getAddress();

  console.log(`TraceLedger successfully deployed to: ${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

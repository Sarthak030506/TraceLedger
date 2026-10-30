require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../.env" });

const accounts = process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [];

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    hardhat: {},
    mstCoral: {
      url: "https://coralrpc.mstblockchain.com",
      chainId: 54635,
      accounts: accounts,
    },
    mstLegacy: {
      url: "https://testnetrpc.mstblockchain.com",
      chainId: 91562037,
      accounts: accounts,
    },
    mstTestnet: {
      url: process.env.RPC_URL || "https://coralrpc.mstblockchain.com",
      chainId: Number(process.env.CHAIN_ID) || 54635,
      accounts: accounts,
    },
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      chainId: 11155111,
      accounts: accounts,
    },
  },
};

import { defineChain } from "viem";

export const monadTestnet = defineChain({
  id: 10143,
  name: "Monad Testnet",
  nativeCurrency: { name: "Monad", symbol: "MON", decimals: 18 },
  rpcUrls: { default: { http: ["https://testnet-rpc.monad.xyz"] } },
  blockExplorers: { default: { name: "MonadVision", url: "https://testnet.monadvision.com" } },
  testnet: true,
});

export const monadMainnet = defineChain({
  id: 143,
  name: "Monad",
  nativeCurrency: { name: "Monad", symbol: "MON", decimals: 18 },
  rpcUrls: { default: { http: ["https://rpc.monad.xyz"] } },
  blockExplorers: { default: { name: "MonadVision", url: "https://monadvision.com" } },
});

// Anvil started with `anvil --chain-id 10143` for local end-to-end testing.
export const localMonad = defineChain({
  ...monadTestnet,
  name: "Local Monad (Anvil)",
  rpcUrls: { default: { http: ["http://127.0.0.1:8545"] } },
});

const network = process.env.NEXT_PUBLIC_NETWORK ?? "testnet";
export const activeChain = network === "mainnet" ? monadMainnet : network === "local" ? localMonad : monadTestnet;

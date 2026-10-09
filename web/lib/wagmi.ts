import { getDefaultConfig } from "@rainbow-me/rainbowkit";
import {
  backpackWallet,
  injectedWallet,
  metaMaskWallet,
  phantomWallet,
  rabbyWallet,
  walletConnectWallet,
} from "@rainbow-me/rainbowkit/wallets";
import { http } from "wagmi";
import { activeChain } from "./chains";

export const wagmiConfig = getDefaultConfig({
  appName: "ChogHub",
  // Injected wallets work without a real ID; WalletConnect needs one from cloud.reown.com.
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "choghub-dev",
  chains: [activeChain],
  transports: { [activeChain.id]: http() },
  // Wallets Monad users actually use, plus a catch-all for any injected wallet.
  wallets: [
    { groupName: "Popular on Monad", wallets: [backpackWallet, phantomWallet, rabbyWallet, metaMaskWallet] },
    { groupName: "Other", wallets: [injectedWallet, walletConnectWallet] },
  ],
  ssr: true,
});

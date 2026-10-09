"use client";

import "@rainbow-me/rainbowkit/styles.css";
import { RainbowKitProvider, lightTheme } from "@rainbow-me/rainbowkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { WagmiProvider } from "wagmi";
import { SessionProvider } from "@/lib/session";
import { wagmiConfig } from "@/lib/wagmi";

const theme = lightTheme({ accentColor: "#6C3BFF", accentColorForeground: "#FFFFFF", borderRadius: "large", fontStack: "system" });
theme.fonts.body = "Outfit, system-ui, sans-serif";
theme.colors.modalBorder = "#1B0B3A";
theme.colors.connectButtonBackground = "#FFFFFF";
theme.colors.connectButtonText = "#1B0B3A";
theme.shadows.connectButton = "4px 4px 0 0 #1B0B3A";
theme.shadows.dialog = "10px 10px 0 0 #1B0B3A";

export function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(() => new QueryClient());
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={qc}>
        <RainbowKitProvider theme={theme}>
          <SessionProvider>{children}</SessionProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

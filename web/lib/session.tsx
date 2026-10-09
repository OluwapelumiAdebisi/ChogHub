"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAccount, useDisconnect, useSignMessage } from "wagmi";
import { createSiweMessage } from "viem/siwe";
import { api } from "./api";
import { activeChain } from "./chains";
import type { ChogSummary, PublicConfig } from "./types";

type Session = {
  token: string | null;
  wallet: string | null;
  isAdmin: boolean;
  chogs: ChogSummary[];
  activeTokenId: number | null;
  config: PublicConfig | null;
  signingIn: boolean;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => void;
  setActiveTokenId: (id: number) => void;
  refreshChogs: () => Promise<void>;
};

const Ctx = createContext<Session | null>(null);
const KEY = "choghub.session";

function load(): { token: string; wallet: string; isAdmin: boolean; active?: number } | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
function save(v: object | null) {
  try {
    if (v) localStorage.setItem(KEY, JSON.stringify(v));
    else localStorage.removeItem(KEY);
  } catch {}
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const { address, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const { disconnect } = useDisconnect();
  const [token, setToken] = useState<string | null>(null);
  const [wallet, setWallet] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [chogs, setChogs] = useState<ChogSummary[]>([]);
  const [activeTokenId, setActive] = useState<number | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<PublicConfig>("/config").then(setConfig).catch(() => setConfig(null));
    const s = load();
    if (s) {
      setToken(s.token);
      setWallet(s.wallet);
      setIsAdmin(s.isAdmin);
      if (s.active) setActive(s.active);
    }
  }, []);

  // Switching wallet accounts ends the session for the old one.
  useEffect(() => {
    if (wallet && address && address.toLowerCase() !== wallet) {
      setToken(null);
      setWallet(null);
      setChogs([]);
      save(null);
    }
  }, [address, wallet]);

  const refreshChogs = useCallback(async () => {
    if (!token) return;
    try {
      const r = await api<{ chogs: ChogSummary[] }>("/me/chogs", { token });
      setChogs(r.chogs);
      setActive((cur) => (cur && r.chogs.some((c) => c.token_id === cur) ? cur : r.chogs[0]?.token_id ?? null));
    } catch (e) {
      if ((e as { status?: number }).status === 401) {
        setToken(null);
        save(null);
      }
    }
  }, [token]);

  useEffect(() => {
    refreshChogs();
  }, [refreshChogs]);

  const signIn = useCallback(async () => {
    if (!address || !isConnected) return;
    setSigningIn(true);
    setError(null);
    try {
      const { nonce, domain } = await api<{ nonce: string; domain: string }>("/auth/nonce");
      const now = new Date();
      const message = createSiweMessage({
        domain,
        address,
        statement: "Sign in to ChogHub. This does not cost anything or send a transaction.",
        uri: window.location.origin,
        version: "1",
        chainId: activeChain.id,
        nonce,
        issuedAt: now,
        expirationTime: new Date(now.getTime() + 5 * 60_000),
      });
      const signature = await signMessageAsync({ message });
      const r = await api<{ token: string; wallet: string; is_admin: boolean }>("/auth/verify", {
        body: { message, signature },
      });
      setToken(r.token);
      setWallet(r.wallet);
      setIsAdmin(r.is_admin);
      save({ token: r.token, wallet: r.wallet, isAdmin: r.is_admin });
    } catch (e) {
      setError(e instanceof Error ? e.message.split("\n")[0] : "Sign-in failed");
    } finally {
      setSigningIn(false);
    }
  }, [address, isConnected, signMessageAsync]);

  const signOut = useCallback(() => {
    setToken(null);
    setWallet(null);
    setChogs([]);
    save(null);
    disconnect();
  }, [disconnect]);

  const setActiveTokenId = useCallback(
    (id: number) => {
      setActive(id);
      if (token && wallet) save({ token, wallet, isAdmin, active: id });
    },
    [token, wallet, isAdmin],
  );

  const value = useMemo(
    () => ({ token, wallet, isAdmin, chogs, activeTokenId, config, signingIn, error, signIn, signOut, setActiveTokenId, refreshChogs }),
    [token, wallet, isAdmin, chogs, activeTokenId, config, signingIn, error, signIn, signOut, setActiveTokenId, refreshChogs],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession outside SessionProvider");
  return v;
}

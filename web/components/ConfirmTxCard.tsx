"use client";

import { useState } from "react";
import { useAccount, useSendTransaction, useSwitchChain } from "wagmi";
import { api } from "@/lib/api";
import { activeChain } from "@/lib/chains";
import { useSession } from "@/lib/session";
import type { ActionCard } from "@/lib/types";

/** The only way anything on-chain happens: the agent prepares, the owner confirms and signs. */
export function ConfirmTxCard({ action, onDone }: { action: ActionCard; onDone: (a: ActionCard) => void }) {
  const { token, config } = useSession();
  const { address, chainId } = useAccount();
  const { switchChainAsync } = useSwitchChain();
  const { sendTransactionAsync } = useSendTransaction();
  const [a, setA] = useState(action);
  const [phase, setPhase] = useState<"idle" | "signing" | "verifying">("idle");
  const [error, setError] = useState<string | null>(null);

  const fake = config?.chain_mode === "fake";

  async function confirm() {
    setError(null);
    try {
      setPhase("signing");
      let hash: string;
      if (fake) {
        // Local dev without a chain: the backend's in-memory chain stands in for the wallet.
        hash = (await api<{ tx_hash: string }>("/dev/send", { body: { wallet: address?.toLowerCase(), tx: a.tx } })).tx_hash;
      } else {
        if (chainId !== activeChain.id) await switchChainAsync({ chainId: activeChain.id });
        hash = await sendTransactionAsync({ to: a.tx.to, data: a.tx.data, value: BigInt(a.tx.value) });
      }
      setPhase("verifying");
      const done = await api<ActionCard>(`/actions/${a.id}/confirm`, { body: { tx_hash: hash }, token });
      setA(done);
      onDone(done);
    } catch (e) {
      const msg = e instanceof Error ? e.message.split("\n")[0] : "Something went wrong";
      setError(/rejected|denied/i.test(msg) ? "You cancelled in your wallet. Nothing was sent." : msg);
    } finally {
      setPhase("idle");
    }
  }

  const explorer = config?.explorer;
  const confirmed = a.status === "confirmed" && a.result;
  return (
    <div
      role="group"
      aria-label="Confirm transaction"
      className={`w-full max-w-[360px] rounded-[24px] border-4 border-ink p-[18px] shadow-hard-md ${confirmed ? "bg-mint" : "bg-sun"}`}
    >
      <p className="font-display text-[28px] leading-none">Buy {a.params.chog_amount.toLocaleString()} CHOG</p>
      <dl className="mt-2.5 grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 text-[15px]">
        <dt>You pay</dt>
        <dd className="font-extrabold">{a.params.mon_cost.toFixed(4)} MON</dd>
        <dt>At least</dt>
        <dd className="font-extrabold">{a.params.min_out.toLocaleString()} CHOG</dd>
        <dt>Network</dt>
        <dd className="font-extrabold">{activeChain.name}</dd>
      </dl>

      {confirmed ? (
        <p className="mt-3 font-extrabold">
          Got it! {a.result!.chog_received.toLocaleString()} CHOG landed in your wallet.{" "}
          {explorer && a.tx_hash && !fake && (
            <a className="underline" href={`${explorer}/tx/${a.tx_hash}`} target="_blank" rel="noreferrer">
              View transaction
            </a>
          )}
        </p>
      ) : a.status === "prepared" ? (
        <>
          <button className="btn-dark mt-3.5 w-full" onClick={confirm} disabled={phase !== "idle"}>
            {phase === "signing" ? "Check your wallet" : phase === "verifying" ? "Confirming on Monad" : "Confirm and sign"}
          </button>
          <p className="mt-2 text-sm font-semibold">Your wallet asks before anything is sent.</p>
        </>
      ) : (
        <p className="mt-3 font-extrabold text-alarm">This one {a.status}. Ask your Chog to prepare it again.</p>
      )}
      {error && (
        <p className="mt-2 rounded-xl bg-white px-3 py-2 text-[15px] font-semibold text-alarm" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

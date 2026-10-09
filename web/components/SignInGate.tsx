"use client";

import { useConnectModal } from "@rainbow-me/rainbowkit";
import { useAccount, useWaitForTransactionReceipt, useWriteContract } from "wagmi";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useEffect, type ReactNode } from "react";
import { ChogArt } from "./ChogArt";

/** Wraps holder-only screens: connect -> sign in -> have a Chog -> children. */
export function SignInGate({ children }: { children: ReactNode }) {
  const { isConnected, address } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { token, chogs, signIn, signingIn, error, config, refreshChogs } = useSession();

  if (!isConnected)
    return (
      <Gate title="Wake up your Chog" body="Your Chog lives in your wallet. Connect it and your Chog gets to work.">
        <button className="btn-primary" onClick={openConnectModal}>
          Connect wallet
        </button>
      </Gate>
    );

  if (!token)
    return (
      <Gate title="Sign in with your wallet" body="Sign a short message to prove the wallet is yours. It's free and sends nothing.">
        <button className="btn-primary" onClick={signIn} disabled={signingIn}>
          {signingIn ? "Check your wallet" : "Sign in"}
        </button>
        {error && <p className="mt-3 font-semibold text-alarm" role="alert">{error}</p>}
      </Gate>
    );

  if (chogs.length === 0) {
    const fake = config?.chain_mode === "fake";
    const testnet = config?.network === "testnet";
    return (
      <Gate
        title="No Chog in this wallet"
        body={
          testnet
            ? "ChogHub runs on Monad testnet with a test Chog collection. Mint one for free and it becomes your agent."
            : "You need a Chog to become a Chog agent. You can still browse events and quests."
        }
      >
        {fake && (
          <button
            className="btn-primary"
            onClick={async () => {
              await api("/dev/mint", { body: { wallet: address, token_id: Math.floor(100 + Math.random() * 900) } });
              await refreshChogs();
            }}
          >
            Mint a test Chog
          </button>
        )}
        {!fake && testnet && config && <MintOnChain nft={config.contracts.nft} onMinted={refreshChogs} />}
      </Gate>
    );
  }
  return <>{children}</>;
}

const MINT_ABI = [{ type: "function", name: "mint", stateMutability: "nonpayable", inputs: [], outputs: [{ type: "uint256" }] }] as const;

function MintOnChain({ nft, onMinted }: { nft: string; onMinted: () => void }) {
  const { writeContract, data: hash, isPending, error } = useWriteContract();
  const { isSuccess, isLoading } = useWaitForTransactionReceipt({ hash });
  useEffect(() => {
    if (isSuccess) onMinted();
  }, [isSuccess, onMinted]);
  return (
    <>
      <button
        className="btn-primary"
        disabled={isPending || isLoading}
        onClick={() => writeContract({ address: nft as `0x${string}`, abi: MINT_ABI, functionName: "mint" })}
      >
        {isPending ? "Check your wallet" : isLoading ? "Minting on Monad" : "Mint a test Chog"}
      </button>
      {error && <p className="mt-3 font-semibold text-alarm" role="alert">{error.message.split("\n")[0]}</p>}
    </>
  );
}

function Gate({ title, body, children }: { title: string; body: string; children: ReactNode }) {
  return (
    <div className="mx-auto mt-10 max-w-lg">
      <div className="mx-auto -mb-10 w-36 rotate-[-4deg] overflow-hidden rounded-[22px] border-4 border-ink shadow-hard-md">
        <ChogArt image={null} traits={{ mood: "Sleepy", hat: "None", background: "Purple" }} tokenId={0} />
      </div>
      <div className="rounded-[28px] border-4 border-ink bg-white px-8 pb-8 pt-16 text-center shadow-hard-lg">
        <h1 className="text-[40px]">{title}</h1>
        <p className="mx-auto mt-3 max-w-sm font-medium">{body}</p>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

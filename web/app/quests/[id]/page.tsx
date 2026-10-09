"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { BADGE_ICON } from "@/components/Icons";
import { api, qs } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Quest } from "@/lib/types";

export default function QuestDetail({ params }: { params: { id: string } }) {
  const { token, activeTokenId } = useSession();
  const [q, setQ] = useState<Quest | null>(null);
  const [proofUrl, setProofUrl] = useState("");
  const [proofText, setProofText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Quest>(`/quests/${params.id}${qs({ token_id: activeTokenId })}`).then(setQ).catch((e) => setError(e.message));
  }, [params.id, activeTokenId]);
  useEffect(load, [load]);

  async function submit(ev: React.FormEvent) {
    ev.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/quests/${params.id}/submit`, {
        token,
        body: { token_id: activeTokenId, proof_url: proofUrl || null, proof_text: proofText || null },
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't submit");
    } finally {
      setBusy(false);
    }
  }

  if (!q) return <p className="py-10 font-semibold">{error ?? "Loading…"}</p>;
  const canSubmit = q.verify_type === "manual" && ["available", "in_progress", "rejected"].includes(q.status);
  const Icon = BADGE_ICON[q.achievement.icon] ?? BADGE_ICON.trophy;

  return (
    <div className="max-w-2xl py-6">
      <Link href="/quests" className="font-extrabold underline decoration-[3px] underline-offset-4">
        All quests
      </Link>

      <article className="mt-6 rounded-[32px] border-4 border-ink bg-mint p-7 shadow-hard-lg sm:p-9">
        <span className="chip border-2 border-ink bg-white">Quest</span>
        <h1 className="mt-3 text-[clamp(44px,7vw,64px)]">{q.title}</h1>
        <p className="mt-4 text-[19px] font-medium">{q.description}</p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <span className="font-bold">Reward:</span>
          <span className="inline-flex -rotate-3 items-center gap-2 rounded-full border-3 border-ink bg-sun px-4 py-2 font-extrabold shadow-hard">
            <Icon />
            {q.achievement.name}
          </span>
        </div>
        {q.trait_requirement && (
          <p className="mt-4 font-bold">
            Only Chogs with {Object.entries(q.trait_requirement).map(([k, v]) => `${v} (${k})`).join(", ")} can take this one.
          </p>
        )}
      </article>

      <div className="mt-8">
        {q.status === "approved" && (
          <p className="card p-6 text-[19px] font-extrabold">Done! The {q.achievement.name} badge is stuck to your Chog.</p>
        )}
        {q.status === "submitted" && (
          <p className="card p-6 text-[19px] font-semibold">Your proof is in review. The badge lands on your Chog as soon as it's approved.</p>
        )}
        {q.verify_type === "auto_buy" && q.status !== "approved" && (
          <p className="card p-6 text-[19px] font-semibold">
            Ask your Chog to buy any amount of CHOG on the{" "}
            <Link href="/hub" className="underline decoration-[3px]">
              My Chog
            </Link>{" "}
            page. This completes the moment the buy confirms.
          </p>
        )}
        {q.verify_type === "auto_event" && q.status !== "approved" && q.event_id && (
          <p className="card p-6 text-[19px] font-semibold">
            <Link href={`/events/${q.event_id}`} className="underline decoration-[3px]">
              Join the event
            </Link>{" "}
            and this completes on its own.
          </p>
        )}

        {canSubmit &&
          (token && activeTokenId ? (
            <form onSubmit={submit} className="card space-y-5 p-6">
              <h2 className="text-[32px]">Prove it</h2>
              {q.status === "rejected" && <p className="font-semibold text-alarm">The last proof wasn't approved. Try again with a clearer link.</p>}
              <div>
                <label htmlFor="proof-url" className="font-extrabold">
                  Link to your proof
                </label>
                <input id="proof-url" type="url" className="field mt-1.5" placeholder="https://x.com/you/status/…" value={proofUrl} onChange={(e) => setProofUrl(e.target.value)} />
              </div>
              <div>
                <label htmlFor="proof-text" className="font-extrabold">
                  Anything the reviewers should know
                </label>
                <textarea id="proof-text" rows={3} className="field mt-1.5" value={proofText} onChange={(e) => setProofText(e.target.value)} />
              </div>
              <button className="btn-primary" disabled={busy || !(proofUrl || proofText)}>
                {busy ? "Submitting" : "Submit proof"}
              </button>
            </form>
          ) : (
            <Link href="/hub" className="btn-primary">
              Sign in to take this quest
            </Link>
          ))}
        {error && (
          <p className="mt-3 font-semibold text-alarm" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

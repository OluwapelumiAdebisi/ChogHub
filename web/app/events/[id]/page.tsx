"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CardGrid, QuestCard, startsIn, when } from "@/components/Cards";
import { api, qs } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ChogEvent } from "@/lib/types";

export default function EventDetail({ params }: { params: { id: string } }) {
  const { token, activeTokenId } = useSession();
  const [e, setE] = useState<ChogEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);

  const load = useCallback(() => {
    api<ChogEvent>(`/events/${params.id}${qs({ token_id: activeTokenId })}`)
      .then(setE)
      .catch((err) => setError(err.message));
  }, [params.id, activeTokenId]);
  useEffect(load, [load]);

  async function join() {
    if (!activeTokenId) return;
    setJoining(true);
    setError(null);
    try {
      await api(`/events/${params.id}/join`, { token, body: { token_id: activeTokenId } });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't join");
    } finally {
      setJoining(false);
    }
  }

  if (!e) return <p className="py-10 font-semibold">{error ?? "Loading…"}</p>;
  return (
    <div className="max-w-3xl py-6">
      <Link href="/events" className="font-extrabold underline decoration-[3px] underline-offset-4">
        All events
      </Link>

      <article className="relative mt-6 rounded-[32px] border-4 border-ink bg-white p-7 shadow-hard-lg sm:p-9">
        {e.prize && (
          <span className="absolute -right-3 -top-5 rotate-6 rounded-full border-3 border-ink bg-hot px-4 py-1.5 font-extrabold">
            {e.prize}
          </span>
        )}
        <p className="font-extrabold text-grape">{startsIn(e.starts_at)}</p>
        <h1 className="mt-2 text-[clamp(44px,7vw,72px)]">{e.title}</h1>
        <p className="mt-2 text-[18px] font-semibold">
          {when(e.starts_at)}
          {e.ends_at ? ` until ${when(e.ends_at)}` : ""}
        </p>
        <p className="mt-5 max-w-[60ch] text-[19px]">{e.description}</p>

        <div className="mt-6 flex flex-wrap gap-3">
          <span className="rounded-[18px] border-3 border-ink bg-sun px-4 py-2 font-extrabold">
            {e.visibility === "holder" ? "Chog holders only" : "Open to everyone"}
          </span>
          <span className="rounded-[18px] border-3 border-ink bg-white px-4 py-2 font-extrabold">
            {e.participants}
            {e.capacity ? ` of ${e.capacity}` : ""} going
          </span>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          {e.joined ? (
            <span className="rounded-full border-3 border-ink bg-mint px-5 py-2.5 text-[18px] font-extrabold">Chog #{activeTokenId} is in!</span>
          ) : token && activeTokenId ? (
            <button className="btn-primary" onClick={join} disabled={joining}>
              {joining ? "Joining" : `Join with Chog #${activeTokenId}`}
            </button>
          ) : (
            <Link href="/hub" className="btn-primary">
              Sign in to join
            </Link>
          )}
          {e.link && (
            <a href={e.link} target="_blank" rel="noreferrer" className="btn-quiet">
              Open event link
            </a>
          )}
        </div>
        {error && (
          <p className="mt-4 font-semibold text-alarm" role="alert">
            {error}
          </p>
        )}
      </article>

      {e.quests && e.quests.length > 0 && (
        <section className="mt-12">
          <h2 className="mb-5 text-[40px]">Quests in this event</h2>
          <CardGrid>
            {e.quests.map((q) => (
              <QuestCard key={q.id} q={q} />
            ))}
          </CardGrid>
        </section>
      )}
    </div>
  );
}

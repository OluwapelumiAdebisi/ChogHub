"use client";

import { useCallback, useEffect, useState } from "react";
import { CardGrid, EventCard, FeaturedEvent, QuestCard } from "@/components/Cards";
import { ChatPanel } from "@/components/ChatPanel";
import { ChogCard } from "@/components/ChogCard";
import { SignInGate } from "@/components/SignInGate";
import { api } from "@/lib/api";
import { useChogProfile } from "@/lib/hooks";
import { useSession } from "@/lib/session";
import type { ChogEvent, Quest } from "@/lib/types";

export default function Hub() {
  return (
    <SignInGate>
      <HubInner />
    </SignInGate>
  );
}

function HubInner() {
  const { token, chogs, activeTokenId, setActiveTokenId } = useSession();
  const tokenId = activeTokenId ?? chogs[0]?.token_id ?? null;
  const { profile, newest, reload } = useChogProfile(tokenId);
  const [events, setEvents] = useState<ChogEvent[]>([]);
  const [quests, setQuests] = useState<Quest[]>([]);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);

  const loadLists = useCallback(async () => {
    if (tokenId == null) return;
    const [e, q] = await Promise.all([
      api<{ events: ChogEvent[] }>(`/events?token_id=${tokenId}`),
      api<{ quests: Quest[] }>(`/quests?token_id=${tokenId}`),
    ]);
    setEvents(e.events);
    setQuests(q.quests);
  }, [tokenId]);

  useEffect(() => {
    loadLists().catch(() => {});
  }, [loadLists]);

  const refresh = useCallback(() => {
    reload();
    loadLists().catch(() => {});
  }, [reload, loadLists]);

  if (tokenId == null) return null;

  const featured = events.find((e) => e.prize && !e.joined) ?? events.find((e) => !e.joined) ?? events[0];
  const otherEvents = events.filter((e) => e !== featured).slice(0, 2);
  const open = quests.filter((q) => q.status !== "approved").slice(0, 4);

  async function join(e: ChogEvent) {
    setJoining(true);
    setJoinError(null);
    try {
      await api(`/events/${e.id}/join`, { token, body: { token_id: tokenId } });
      refresh();
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : "Couldn't join");
    } finally {
      setJoining(false);
    }
  }

  return (
    <div className="flex flex-wrap items-start gap-8 py-3">
      <div className="order-1 w-full max-w-[440px] flex-[1_1_360px]">
        {chogs.length > 1 && (
          <div className="mb-6 flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Choose your Chog">
            {chogs.map((c) => (
              <button
                key={c.token_id}
                role="radio"
                aria-checked={c.token_id === tokenId}
                onClick={() => setActiveTokenId(c.token_id)}
                className={`rounded-full border-3 border-ink px-4 py-1.5 font-extrabold ${
                  c.token_id === tokenId ? "bg-ink text-sun" : "bg-white"
                }`}
              >
                #{c.token_id}
              </button>
            ))}
          </div>
        )}
        {profile ? (
          <ChogCard profile={profile} newestSlug={newest} />
        ) : (
          <div className="h-[520px] -rotate-[1.5deg] animate-pulse rounded-[32px] border-4 border-ink bg-grape-light" />
        )}
      </div>

      <section aria-label="Today" className="order-3 min-w-0 flex-[999_1_380px] xl:order-2">
        <h2 className="mb-5 mt-1 text-[clamp(44px,5vw,64px)]">What's poppin' today</h2>
        {featured ? (
          <FeaturedEvent
            e={featured}
            action={
              <button className="btn-primary" onClick={() => join(featured)} disabled={joining}>
                {joining ? "Joining" : `Join with Chog #${tokenId}`}
              </button>
            }
          />
        ) : (
          <p className="card p-6 font-semibold">Quiet day in Chog land. New events land here first.</p>
        )}
        {joinError && (
          <p className="mt-3 rounded-2xl border-3 border-ink bg-white px-4 py-2 font-semibold text-alarm" role="alert">
            {joinError}
          </p>
        )}
        {(otherEvents.length > 0 || open.length > 0) && (
          <div className="mt-6">
            <CardGrid single>
              {otherEvents.map((e) => (
                <EventCard key={`e${e.id}`} e={e} />
              ))}
              {open.map((q) => (
                <QuestCard key={`q${q.id}`} q={q} />
              ))}
            </CardGrid>
          </div>
        )}
      </section>

      <div className="order-2 w-full max-w-[420px] flex-[1_1_340px] xl:sticky xl:top-6 xl:order-3">
        <ChatPanel tokenId={tokenId} onChange={refresh} />
      </div>
    </div>
  );
}

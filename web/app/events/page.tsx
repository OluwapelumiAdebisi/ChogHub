"use client";

import { useEffect, useState } from "react";
import { CardGrid, EventCard } from "@/components/Cards";
import { api, qs } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ChogEvent } from "@/lib/types";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "holder", label: "Holders only" },
  { id: "public", label: "Open to everyone" },
] as const;

export default function Events() {
  const { activeTokenId } = useSession();
  const [events, setEvents] = useState<ChogEvent[] | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");

  useEffect(() => {
    api<{ events: ChogEvent[] }>(`/events${qs({ token_id: activeTokenId })}`)
      .then((r) => setEvents(r.events))
      .catch(() => setEvents([]));
  }, [activeTokenId]);

  const shown = (events ?? []).filter((e) => filter === "all" || e.visibility === filter);
  return (
    <div className="max-w-4xl py-6">
      <h1 className="text-[clamp(56px,8vw,88px)]">Events</h1>
      <p className="mt-2 max-w-[52ch] text-[19px] font-medium">Official Chog events and community happenings. Your Chog is your ticket.</p>
      <div className="mt-6 flex flex-wrap gap-2.5" role="tablist" aria-label="Filter events">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-full border-3 border-ink px-4 py-1.5 font-extrabold ${filter === f.id ? "bg-ink text-sun" : "bg-white"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
      <div className="mt-6">
        {events === null ? (
          <p className="font-semibold">Loading events…</p>
        ) : shown.length === 0 ? (
          <p className="card p-6 font-semibold">No events match this filter yet.</p>
        ) : (
          <CardGrid>
            {shown.map((e) => (
              <EventCard key={e.id} e={e} />
            ))}
          </CardGrid>
        )}
      </div>
    </div>
  );
}

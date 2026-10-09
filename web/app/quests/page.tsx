"use client";

import { useEffect, useState } from "react";
import { CardGrid, QuestCard } from "@/components/Cards";
import { api, qs } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Quest } from "@/lib/types";

export default function Quests() {
  const { activeTokenId } = useSession();
  const [quests, setQuests] = useState<Quest[] | null>(null);

  useEffect(() => {
    api<{ quests: Quest[] }>(`/quests${qs({ token_id: activeTokenId })}`)
      .then((r) => setQuests(r.quests))
      .catch(() => setQuests([]));
  }, [activeTokenId]);

  const open = (quests ?? []).filter((q) => q.status !== "approved");
  const done = (quests ?? []).filter((q) => q.status === "approved");
  return (
    <div className="max-w-4xl py-6">
      <h1 className="text-[clamp(56px,8vw,88px)]">Quests</h1>
      <p className="mt-2 max-w-[52ch] text-[19px] font-medium">Finish a quest and its badge sticks to your Chog for good, on-chain.</p>
      <div className="mt-8">
        {quests === null ? (
          <p className="font-semibold">Loading quests…</p>
        ) : open.length ? (
          <CardGrid>
            {open.map((q) => (
              <QuestCard key={q.id} q={q} />
            ))}
          </CardGrid>
        ) : (
          <p className="card p-6 font-semibold">You've cleared every quest. New ones land here first.</p>
        )}
      </div>
      {done.length > 0 && (
        <section className="mt-12">
          <h2 className="mb-5 text-[40px]">Done and dusted</h2>
          <CardGrid>
            {done.map((q) => (
              <QuestCard key={q.id} q={q} />
            ))}
          </CardGrid>
        </section>
      )}
    </div>
  );
}

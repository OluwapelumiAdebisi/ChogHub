"use client";

import { when } from "@/components/Cards";
import { ChogCard } from "@/components/ChogCard";
import { useChogProfile } from "@/lib/hooks";

export default function ChogPage({ params }: { params: { tokenId: string } }) {
  const id = Number(params.tokenId);
  const { profile, error } = useChogProfile(Number.isFinite(id) ? id : null);

  if (error) return <p className="card mt-8 max-w-xl p-6 font-semibold text-alarm">{error}</p>;
  if (!profile) return <div className="mt-6 h-[520px] max-w-[440px] -rotate-[1.5deg] animate-pulse rounded-[32px] border-4 border-ink bg-grape-light" />;

  const onchain = profile.stats.onchain;
  return (
    <div className="grid gap-12 py-6 md:grid-cols-[minmax(0,440px)_1fr]">
      <ChogCard profile={profile} />
      <section>
        <h2 className="text-[clamp(44px,5vw,64px)]">{profile.name}'s story</h2>
        <p className="mt-3 max-w-[56ch] text-[18px] font-medium">
          This history belongs to the token. If {profile.name} changes hands, it goes with it.
          {onchain.quests !== undefined &&
            ` On Monad: ${onchain.quests} quests, ${onchain.events} events and ${onchain.wins} wins recorded.`}
        </p>
        {profile.history.length === 0 ? (
          <p className="card mt-8 p-6 font-semibold">Nothing yet. Join an event or start a quest to begin the story.</p>
        ) : (
          <ol className="mt-8 space-y-4">
            {profile.history.map((h, i) => (
              <li
                key={i}
                className={`flex items-center gap-4 rounded-[22px] border-3 border-ink p-4 shadow-hard ${h.type === "achievement" ? "bg-mint" : "bg-white"}`}
                style={{ transform: `rotate(${i % 2 ? 0.6 : -0.6}deg)` }}
              >
                <span className={`chip shrink-0 border-2 border-ink ${h.type === "achievement" ? "bg-white" : "bg-ink text-sun"}`}>
                  {h.type === "achievement" ? "Badge" : "Event"}
                </span>
                <div className="min-w-0">
                  <p className="text-[19px] font-extrabold leading-tight">{h.type === "achievement" ? `Earned ${h.title}` : `Joined ${h.title}`}</p>
                  <p className="text-[15px] font-medium">{when(h.at)}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

"use client";

import { useConnectModal } from "@rainbow-me/rainbowkit";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";
import { CardGrid, EventCard, FeaturedEvent, QuestCard } from "@/components/Cards";
import { ChogCard } from "@/components/ChogCard";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ChogEvent, ChogProfile, Quest } from "@/lib/types";

// A sample Chog on the landing page, so visitors see what theirs becomes.
const SAMPLE: ChogProfile = {
  token_id: 742,
  collection: "",
  name: "Chog #742",
  owner: "0x7a3fd1c0000000000000000000000000000c0de",
  owner_count: 2,
  traits: { hat: "Pirate Hat", mood: "Chaotic", background: "Purple" },
  image: null,
  stats: { quests_completed: 17, events_attended: 4, achievements: 3, onchain: {} },
  achievements: [
    { slug: "meme-warrior", name: "Meme Warrior", icon: "frog" },
    { slug: "caller", name: "On the Call", icon: "mic" },
    { slug: "first-chog", name: "First CHOG", icon: "coin" },
  ],
  history: [],
};

export default function Landing() {
  const { isConnected } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { token } = useSession();
  const [events, setEvents] = useState<ChogEvent[]>([]);
  const [quests, setQuests] = useState<Quest[]>([]);

  useEffect(() => {
    api<{ events: ChogEvent[] }>("/events").then((r) => setEvents(r.events)).catch(() => {});
    api<{ quests: Quest[] }>("/quests").then((r) => setQuests(r.quests)).catch(() => {});
  }, []);

  const featured = events.find((e) => e.prize) ?? events[0];
  const rest = events.filter((e) => e !== featured);

  return (
    <>
      <section className="grid items-center gap-12 py-8 md:grid-cols-[1.15fr_1fr] md:py-14">
        <div>
          <h1 className="text-[clamp(56px,9vw,112px)] leading-[0.9]">
            Your Chog has a <span className="title-pop inline-block -rotate-2 text-grape">job</span> now.
          </h1>
          <p className="mt-6 max-w-[36ch] text-[21px] font-medium">
            Connect your wallet and your Chog wakes up as your agent. It finds events, runs quests and buys CHOG for you.
            Everything it earns sticks to the NFT.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {token || isConnected ? (
              <Link href="/hub" className="btn-primary">
                {token ? "Open my Chog" : "Sign in"}
              </Link>
            ) : (
              <button className="btn-primary" onClick={openConnectModal}>
                Connect wallet
              </button>
            )}
            <Link href="/events" className="btn-quiet">
              Browse events
            </Link>
          </div>
        </div>
        <div className="mx-auto w-full max-w-[440px] md:rotate-[2deg]">
          <ChogCard profile={SAMPLE} tilt={false} />
        </div>
      </section>

      <section className="mt-6 grid gap-10 lg:grid-cols-2">
        <div>
          <h2 className="mb-6 text-[48px]">What's poppin'</h2>
          {featured ? (
            <FeaturedEvent
              e={featured}
              action={
                <Link href={`/events/${featured.id}`} className="btn-primary">
                  See the event
                </Link>
              }
            />
          ) : (
            <p className="card p-6 font-semibold">No events yet. The Chog team posts them here first.</p>
          )}
          {rest.length > 0 && (
            <div className="mt-5">
              <CardGrid>
                {rest.slice(0, 2).map((e) => (
                  <EventCard key={e.id} e={e} />
                ))}
              </CardGrid>
            </div>
          )}
        </div>
        <div>
          <h2 className="mb-6 text-[48px]">Open quests</h2>
          {quests.length ? (
            <CardGrid>
              {quests.slice(0, 4).map((q) => (
                <QuestCard key={q.id} q={q} />
              ))}
            </CardGrid>
          ) : (
            <p className="card p-6 font-semibold">No quests open yet.</p>
          )}
        </div>
      </section>

      <section className="mt-16 -rotate-[0.6deg] rounded-[32px] border-4 border-ink bg-ink px-8 py-10 text-sun shadow-[8px_8px_0_0_#6C3BFF]">
        <h2 className="text-[clamp(32px,4.5vw,48px)]">Sell your Chog, and its story goes with it.</h2>
        <p className="mt-3 max-w-[60ch] text-[19px] font-medium text-white">
          Quests, events and badges are recorded on Monad against the token, not your wallet. A new owner inherits the
          Chog's reputation. Your private chats with it stay yours.
        </p>
      </section>
    </>
  );
}

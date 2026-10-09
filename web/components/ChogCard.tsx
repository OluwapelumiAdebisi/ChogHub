import Link from "next/link";
import { ChogArt } from "./ChogArt";
import { BADGE_ICON } from "./Icons";
import type { ChogProfile } from "@/lib/types";

// Fixed tilts so badges look slapped on by hand but render the same every time.
const TILTS = [-6, 4, -2, 7, -8, 3];
const FILLS = ["bg-mint", "bg-white", "bg-bubble", "bg-sun", "bg-white", "bg-mint"];

function short(addr: string) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

/** The Chog card: the NFT tilted on the page, badges stuck underneath. */
export function ChogCard({ profile, newestSlug, tilt = true }: { profile: ChogProfile; newestSlug?: string | null; tilt?: boolean }) {
  const s = profile.stats;
  const t = profile.traits;
  const traitLine = [t.hat && t.hat !== "None" ? t.hat : null, t.mood ? `${t.mood} mood` : null].filter(Boolean).join(", ");
  return (
    <section aria-label={`${profile.name}`}>
      <div className={`rounded-[32px] border-4 border-ink bg-grape p-5 shadow-hard-lg sm:p-[22px] ${tilt ? "-rotate-[1.5deg]" : ""}`}>
        <div className="relative overflow-hidden rounded-[22px] border-4 border-ink">
          <ChogArt image={profile.image} traits={profile.traits} tokenId={profile.token_id} />
          <span className="absolute right-3 top-3 rotate-[8deg] rounded-full border-3 border-ink bg-sun px-3 py-0.5 font-extrabold">
            #{profile.token_id}
          </span>
        </div>
        <h1 className="title-pop mt-[18px] text-[clamp(40px,6vw,56px)] text-white">
          <Link href={`/chog/${profile.token_id}`} className="hover:text-sun">
            {profile.name}
          </Link>
        </h1>
        <p className="mt-1.5 font-semibold text-white">
          {traitLine}
          {traitLine ? ", " : ""}
          {profile.owner_count > 1 ? `owner number ${profile.owner_count}` : "first owner"}
        </p>
        <p className="mt-0.5 text-[15px] text-white/85">Held by {short(profile.owner)}</p>
      </div>

      <div aria-label="Badges" className="mt-7 flex min-h-[52px] flex-wrap gap-3 px-1.5">
        {profile.achievements.length === 0 && (
          <p className="font-semibold">No badges yet. Finish a quest and your first one sticks right here.</p>
        )}
        {profile.achievements.map((a, i) => {
          const Icon = BADGE_ICON[a.icon] ?? BADGE_ICON.trophy;
          const tiltDeg = TILTS[i % TILTS.length];
          return (
            <span
              key={a.slug}
              style={{ ["--tilt" as string]: `${tiltDeg}deg`, transform: `rotate(${tiltDeg}deg)` }}
              className={`inline-flex items-center gap-2 rounded-full border-3 border-ink px-4 py-2 font-extrabold shadow-hard ${FILLS[i % FILLS.length]} ${
                a.slug === newestSlug ? "badge-new" : ""
              }`}
            >
              <Icon />
              {a.name}
            </span>
          );
        })}
      </div>

      <div className="mt-6 flex flex-wrap gap-3 px-1.5">
        <Stat n={s.quests_completed} label={s.quests_completed === 1 ? "quest" : "quests"} />
        <Stat n={s.events_attended} label={s.events_attended === 1 ? "event" : "events"} />
      </div>
    </section>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="rounded-[18px] border-3 border-ink bg-white px-[18px] py-2 shadow-hard">
      <span className="font-display text-[34px] leading-none">{n}</span> <span className="font-bold">{label}</span>
    </div>
  );
}

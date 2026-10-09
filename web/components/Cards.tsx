import Link from "next/link";
import type { ChogEvent, Quest, QuestStatus } from "@/lib/types";

export function when(iso: string) {
  const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
  return d.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export function startsIn(iso: string) {
  const ms = new Date(iso + (iso.endsWith("Z") ? "" : "Z")).getTime() - Date.now();
  if (ms <= 0) return "Happening now";
  const h = Math.round(ms / 3_600_000);
  if (h < 1) return "Starts in under an hour";
  if (h < 24) return `Starts in ${h} hour${h === 1 ? "" : "s"}`;
  const d = Math.round(h / 24);
  return `Starts in ${d} day${d === 1 ? "" : "s"}`;
}

const WHERE: Record<string, string> = { online: "online", irl: "in person", spaces: "on X Spaces", discord: "on Discord" };

/** The big one: the next event, with a prize sticker hanging off its corner. */
export function FeaturedEvent({ e, action }: { e: ChogEvent; action?: React.ReactNode }) {
  return (
    <article className="relative rounded-[28px] border-4 border-ink bg-white p-6 shadow-[8px_8px_0_0_#1B0B3A]">
      {e.prize && (
        <span className="absolute -right-2.5 -top-[18px] rotate-6 rounded-full border-3 border-ink bg-hot px-3.5 py-1.5 font-extrabold text-ink">
          {e.prize}
        </span>
      )}
      <p className="font-extrabold text-grape">
        {startsIn(e.starts_at)}
        {e.visibility === "holder" ? ", holders only" : ", open to everyone"}
      </p>
      <h3 className="mt-1.5 text-[40px]">
        <Link href={`/events/${e.id}`} className="hover:text-grape">
          {e.title}
        </Link>
      </h3>
      <p className="mt-2 max-w-[46ch]">{e.description}</p>
      <div className="mt-[18px] flex flex-wrap items-center gap-3">
        {e.joined ? <span className="chip border-3 border-ink bg-mint px-4 py-2 text-[16px]">You're in</span> : action}
        <span className="font-semibold text-ink-soft">{e.participants} going</span>
      </div>
    </article>
  );
}

export function EventCard({ e }: { e: ChogEvent }) {
  return (
    <Link href={`/events/${e.id}`} className="card group block p-[18px] transition-transform hover:-translate-y-0.5">
      <div className="flex items-center justify-between gap-2">
        <span className="chip bg-ink text-sun">Event</span>
        {e.joined && <span className="chip border-2 border-ink bg-mint">Joined</span>}
      </div>
      <h3 className="mt-2.5 font-body text-[20px] font-extrabold leading-tight group-hover:text-grape">{e.title}</h3>
      <p className="mt-1 text-[15px]">
        {when(e.starts_at)}, {WHERE[e.kind] ?? e.kind}
        {e.visibility === "holder" ? ". Holders only." : "."}
      </p>
    </Link>
  );
}

const STATUS: Record<QuestStatus, { label: string; cls: string }> = {
  available: { label: "Open", cls: "bg-white" },
  in_progress: { label: "Started", cls: "bg-white" },
  submitted: { label: "In review", cls: "bg-sun" },
  approved: { label: "Done", cls: "bg-ink text-sun" },
  rejected: { label: "Try again", cls: "bg-white text-alarm" },
};

const VERIFY: Record<Quest["verify_type"], string> = {
  manual: "Drop a link to prove it",
  auto_buy: "Completes when you buy CHOG",
  auto_event: "Completes when you join the event",
};

export function QuestCard({ q }: { q: Quest }) {
  const st = STATUS[q.status];
  const done = q.status === "approved";
  return (
    <Link
      href={`/quests/${q.id}`}
      className={`group block rounded-[24px] border-3 border-ink p-[18px] shadow-hard-md transition-transform hover:-translate-y-0.5 ${done ? "bg-white" : "bg-mint"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="chip border-2 border-ink bg-white">Quest</span>
        <span className={`chip border-2 border-ink ${st.cls}`}>{st.label}</span>
      </div>
      <h3 className="mt-2.5 font-body text-[20px] font-extrabold leading-tight group-hover:underline">{q.title}</h3>
      <p className="mt-1 text-[15px]">
        {VERIFY[q.verify_type]}, earn {q.achievement.name}.
        {q.trait_requirement ? ` ${Object.values(q.trait_requirement).join(", ")} Chogs only.` : ""}
      </p>
    </Link>
  );
}

export function CardGrid({ children, single = false }: { children: React.ReactNode; single?: boolean }) {
  return <div className={`grid grid-cols-1 gap-4 ${single ? "" : "sm:grid-cols-2"}`}>{children}</div>;
}

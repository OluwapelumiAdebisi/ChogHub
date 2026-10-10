"use client";

import { useCallback, useEffect, useState } from "react";
import { BADGE_ICON } from "@/components/Icons";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ChogEvent, Quest } from "@/lib/types";

type Sub = { id: number; quest: string; token_id: number; wallet: string; proof_text: string | null; proof_url: string | null };
type AdminQuest = Quest & { active: boolean; completed: number; event_title: string | null };
type Notice = { tone: "ok" | "bad"; text: string } | null;

// The traits the Chog collection has. A quest can be limited to Chogs with one of them.
const TRAITS: Record<string, string[]> = {
  hat: ["Pirate Hat", "Crown", "Beanie", "Party Hat", "None"],
  mood: ["Chaotic", "Sleepy", "Hyped", "Mischievous"],
  background: ["Purple", "Night", "Mint", "Sunset"],
};
const ICONS: { id: string; label: string }[] = [
  { id: "frog", label: "Star" },
  { id: "mic", label: "Mic" },
  { id: "coin", label: "Coin" },
  { id: "anchor", label: "Anchor" },
  { id: "trophy", label: "Trophy" },
];
const HOW: Record<Quest["verify_type"], string> = {
  manual: "Holder submits proof, an admin approves it",
  auto_event: "Completes when the holder joins an event",
  auto_buy: "Completes when the holder buys CHOG",
};

const slugify = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "item";

export default function Admin() {
  const { token, isAdmin } = useSession();
  const [subs, setSubs] = useState<Sub[]>([]);
  const [quests, setQuests] = useState<AdminQuest[]>([]);
  const [events, setEvents] = useState<ChogEvent[]>([]);
  const [notice, setNotice] = useState<Notice>(null);

  const load = useCallback(() => {
    if (!token || !isAdmin) return;
    api<{ submissions: Sub[] }>("/admin/submissions", { token }).then((r) => setSubs(r.submissions)).catch(() => {});
    api<{ quests: AdminQuest[] }>("/admin/quests", { token }).then((r) => setQuests(r.quests)).catch(() => {});
    api<{ events: ChogEvent[] }>("/events?include_past=true").then((r) => setEvents(r.events)).catch(() => {});
  }, [token, isAdmin]);
  useEffect(load, [load]);

  if (!token || !isAdmin)
    return <p className="card mt-8 max-w-xl p-6 font-semibold">Sign in with an admin wallet to review quests and create events.</p>;

  const ok = (text: string) => setNotice({ tone: "ok", text });
  const bad = (e: unknown, fallback: string) => setNotice({ tone: "bad", text: e instanceof Error ? e.message : fallback });

  async function review(id: number, approve: boolean) {
    try {
      const r = await api<{ status: string; onchain_tx: string | null }>(`/admin/submissions/${id}/review`, { token, body: { approve } });
      ok(approve ? `Approved. ${r.onchain_tx ? "Badge recorded on Monad." : "Saved, but no attester key is set so nothing went on-chain."}` : "Rejected. The holder can try again.");
      load();
    } catch (e) {
      bad(e, "Review failed");
    }
  }

  async function toggle(q: AdminQuest) {
    try {
      await api(`/admin/quests/${q.id}`, { token, method: "PATCH", body: { active: !q.active } });
      ok(q.active ? `Paused ${q.title}. Holders can't see it now.` : `${q.title} is live again.`);
      load();
    } catch (e) {
      bad(e, "Couldn't update the quest");
    }
  }

  return (
    <div className="py-6">
      <h1 className="text-[clamp(48px,7vw,72px)]">Admin</h1>
      <p className="mt-1 max-w-[60ch] text-[18px] font-medium">Only admin wallets see this page. You create every event and quest, and approve every proof.</p>
      {notice && (
        <p
          role="status"
          className={`mt-5 max-w-3xl rounded-2xl border-3 border-ink px-4 py-2.5 font-bold ${notice.tone === "ok" ? "bg-mint" : "bg-white text-alarm"}`}
        >
          {notice.text}
        </p>
      )}

      <div className="mt-8 grid gap-12 lg:grid-cols-2">
        <section aria-labelledby="review-h">
          <h2 id="review-h" className="text-[40px]">Review proofs</h2>
          {subs.length === 0 ? (
            <p className="card mt-5 p-6 font-semibold">Nothing waiting for review.</p>
          ) : (
            <ul className="mt-5 space-y-4">
              {subs.map((s) => (
                <li key={s.id} className="card p-5">
                  <p className="text-[20px] font-extrabold">{s.quest}, Chog #{s.token_id}</p>
                  {s.proof_url && (
                    <a className="break-all font-semibold underline" href={s.proof_url} target="_blank" rel="noreferrer">
                      {s.proof_url}
                    </a>
                  )}
                  {s.proof_text && <p className="mt-1">{s.proof_text}</p>}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button className="btn-primary" onClick={() => review(s.id, true)}>Approve</button>
                    <button className="btn-quiet" onClick={() => review(s.id, false)}>Reject</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="quests-h">
          <h2 id="quests-h" className="text-[40px]">Your quests</h2>
          {quests.length === 0 ? (
            <p className="card mt-5 p-6 font-semibold">No quests yet. Create the first one below.</p>
          ) : (
            <ul className="mt-5 space-y-3">
              {quests.map((q) => {
                const Icon = BADGE_ICON[q.achievement.icon] ?? BADGE_ICON.trophy;
                return (
                  <li key={q.id} className={`flex flex-wrap items-center gap-3 rounded-[20px] border-3 border-ink p-4 shadow-hard ${q.active ? "bg-white" : "bg-white/60"}`}>
                    <div className="min-w-0 flex-1">
                      <p className="font-extrabold">
                        {q.title}
                        {!q.active && <span className="chip ml-2 border-2 border-ink bg-sun align-middle">Paused</span>}
                      </p>
                      <p className="text-[15px]">
                        <Icon className="mr-1 inline" />
                        {q.achievement.name}. {HOW[q.verify_type]}
                        {q.event_title ? ` (${q.event_title})` : ""}
                        {q.trait_requirement ? `. ${Object.values(q.trait_requirement).join(", ")} only` : ""}. Done by {q.completed}.
                      </p>
                    </div>
                    <button className="btn-quiet min-h-[44px] px-4 py-1.5 text-[15px]" onClick={() => toggle(q)}>
                      {q.active ? "Pause" : "Resume"}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <CreateQuest token={token} events={events} onDone={(m) => { ok(m); load(); }} onError={(e) => bad(e, "Couldn't create the quest")} />
        <CreateEvent token={token} onDone={(m) => { ok(m); load(); }} onError={(e) => bad(e, "Couldn't create the event")} />
      </div>
    </div>
  );
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="font-extrabold">{label}</label>
      {hint && <p className="text-[14px] font-medium text-ink-soft">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

const EMPTY_QUEST = { title: "", description: "", verify_type: "manual" as Quest["verify_type"], event_id: "", trait_key: "", trait_value: "", badge: "", icon: "trophy" };

function CreateQuest({ token, events, onDone, onError }: { token: string; events: ChogEvent[]; onDone: (m: string) => void; onError: (e: unknown) => void }) {
  const [f, setF] = useState(EMPTY_QUEST);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF((cur) => ({ ...cur, [k]: e.target.value, ...(k === "trait_key" ? { trait_value: "" } : {}) }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/admin/quests", {
        token,
        body: {
          slug: slugify(f.title),
          title: f.title,
          description: f.description,
          verify_type: f.verify_type,
          event_id: f.event_id ? Number(f.event_id) : null,
          trait_requirement: f.trait_key && f.trait_value ? { [f.trait_key]: f.trait_value } : null,
          achievement_slug: slugify(f.badge),
          achievement_name: f.badge,
          achievement_icon: f.icon,
        },
      });
      onDone(`Created the quest "${f.title}". Holders can see it now.`);
      setF(EMPTY_QUEST);
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }

  const needsEvent = f.verify_type === "auto_event";
  return (
    <section aria-labelledby="cq-h">
      <h2 id="cq-h" className="text-[40px]">Create a quest</h2>
      <form onSubmit={submit} className="mt-5 space-y-4 rounded-[24px] border-3 border-ink bg-mint p-6 shadow-hard-md">
        <Field id="q-title" label="Quest name">
          <input id="q-title" required minLength={3} className="field" placeholder="Post your Chog on X" value={f.title} onChange={set("title")} />
        </Field>
        <Field id="q-desc" label="What holders need to do">
          <textarea id="q-desc" rows={3} className="field" placeholder="Share a photo of your Chog with #ChogWorldOrder and drop the link." value={f.description} onChange={set("description")} />
        </Field>
        <Field id="q-how" label="How it's completed">
          <select id="q-how" className="field" value={f.verify_type} onChange={set("verify_type")}>
            <option value="manual">{HOW.manual}</option>
            <option value="auto_event">{HOW.auto_event}</option>
            <option value="auto_buy">{HOW.auto_buy}</option>
          </select>
        </Field>
        <Field id="q-event" label={needsEvent ? "Which event" : "Part of an event (optional)"}>
          <select id="q-event" required={needsEvent} className="field" value={f.event_id} onChange={set("event_id")}>
            <option value="">{needsEvent ? "Pick an event" : "Not tied to an event"}</option>
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>{ev.title}</option>
            ))}
          </select>
        </Field>
        <Field id="q-trait" label="Only for Chogs with (optional)" hint="Leave empty to open the quest to every holder.">
          <div className="flex flex-wrap gap-2">
            <select id="q-trait" aria-label="Trait" className="field w-auto flex-1" value={f.trait_key} onChange={set("trait_key")}>
              <option value="">Any Chog</option>
              <option value="hat">Hat</option>
              <option value="mood">Mood</option>
              <option value="background">Background</option>
            </select>
            {f.trait_key && (
              <select aria-label="Trait value" required className="field w-auto flex-1" value={f.trait_value} onChange={set("trait_value")}>
                <option value="">Pick one</option>
                {TRAITS[f.trait_key].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            )}
          </div>
        </Field>
        <Field id="q-badge" label="Badge it earns" hint="Each quest gets its own badge, recorded on Monad.">
          <input id="q-badge" required minLength={3} className="field" placeholder="Chog Influencer" value={f.badge} onChange={set("badge")} />
        </Field>
        <fieldset>
          <legend className="font-extrabold">Badge icon</legend>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {ICONS.map((ic) => {
              const Icon = BADGE_ICON[ic.id];
              const on = f.icon === ic.id;
              return (
                <label key={ic.id} className={`inline-flex min-h-[44px] cursor-pointer items-center gap-2 rounded-full border-3 border-ink px-4 font-bold ${on ? "bg-ink text-sun" : "bg-white"}`}>
                  <input type="radio" name="icon" value={ic.id} checked={on} onChange={set("icon")} className="sr-only" />
                  <Icon />
                  {ic.label}
                </label>
              );
            })}
          </div>
        </fieldset>
        {f.badge && (
          <p className="font-semibold">
            Preview:{" "}
            <span className="inline-flex -rotate-2 items-center gap-2 rounded-full border-3 border-ink bg-sun px-4 py-1.5 font-extrabold shadow-hard">
              {(() => {
                const Icon = BADGE_ICON[f.icon];
                return <Icon />;
              })()}
              {f.badge}
            </span>
          </p>
        )}
        <button className="btn-primary" disabled={busy}>{busy ? "Creating" : "Create quest"}</button>
      </form>
    </section>
  );
}

const EMPTY_EVENT = { title: "", description: "", starts_at: "", visibility: "holder", prize_text: "" };

function CreateEvent({ token, onDone, onError }: { token: string; onDone: (m: string) => void; onError: (e: unknown) => void }) {
  const [f, setF] = useState(EMPTY_EVENT);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF((cur) => ({ ...cur, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/admin/events", {
        token,
        body: { ...f, slug: slugify(f.title), starts_at: new Date(f.starts_at).toISOString(), prize_text: f.prize_text || null },
      });
      onDone(`Created the event "${f.title}".`);
      setF(EMPTY_EVENT);
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="ce-h">
      <h2 id="ce-h" className="text-[40px]">Create an event</h2>
      <form onSubmit={submit} className="card mt-5 space-y-4 p-6">
        <Field id="e-title" label="Event name">
          <input id="e-title" required minLength={3} className="field" placeholder="Chog Art Jam" value={f.title} onChange={set("title")} />
        </Field>
        <Field id="e-desc" label="What happens">
          <textarea id="e-desc" rows={3} className="field" value={f.description} onChange={set("description")} />
        </Field>
        <Field id="e-start" label="Starts">
          <input id="e-start" required type="datetime-local" className="field" value={f.starts_at} onChange={set("starts_at")} />
        </Field>
        <Field id="e-who" label="Who can join">
          <select id="e-who" className="field" value={f.visibility} onChange={set("visibility")}>
            <option value="holder">Chog holders only</option>
            <option value="public">Everyone</option>
          </select>
        </Field>
        <Field id="e-prize" label="Prize (optional)">
          <input id="e-prize" className="field" placeholder="10,000 CHOG" value={f.prize_text} onChange={set("prize_text")} />
        </Field>
        <button className="btn-primary" disabled={busy}>{busy ? "Creating" : "Create event"}</button>
      </form>
    </section>
  );
}

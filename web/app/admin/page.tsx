"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Sub = { id: number; quest: string; token_id: number; wallet: string; proof_text: string | null; proof_url: string | null };

export default function Admin() {
  const { token, isAdmin } = useSession();
  const [subs, setSubs] = useState<Sub[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    if (token && isAdmin) api<{ submissions: Sub[] }>("/admin/submissions", { token }).then((r) => setSubs(r.submissions)).catch((e) => setMsg(e.message));
  }, [token, isAdmin]);
  useEffect(load, [load]);

  if (!token || !isAdmin) return <p className="card mt-8 max-w-xl p-6 font-semibold">Sign in with an admin wallet to review quests and create events.</p>;

  async function review(id: number, approve: boolean) {
    try {
      const r = await api<{ status: string; onchain_tx: string | null }>(`/admin/submissions/${id}/review`, { token, body: { approve } });
      setMsg(approve ? `Approved. ${r.onchain_tx ? "Badge recorded on Monad." : "Saved off-chain (no attester key set)."}` : "Rejected.");
      load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Review failed");
    }
  }

  return (
    <div className="grid gap-12 py-6 lg:grid-cols-[1fr_1fr]">
      <section>
        <h1 className="text-[56px]">Review proofs</h1>
        {msg && <p className="mt-4 rounded-2xl border-3 border-ink bg-mint px-4 py-2 font-bold" role="status">{msg}</p>}
        {subs.length === 0 ? (
          <p className="card mt-5 p-6 font-semibold">Nothing waiting for review.</p>
        ) : (
          <ul className="mt-5 space-y-4">
            {subs.map((s) => (
              <li key={s.id} className="card p-5">
                <p className="text-[20px] font-extrabold">{s.quest}, Chog #{s.token_id}</p>
                {s.proof_url && <a className="break-all font-semibold underline" href={s.proof_url} target="_blank" rel="noreferrer">{s.proof_url}</a>}
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
      <CreateEvent token={token} onDone={(m) => setMsg(m)} />
    </div>
  );
}

function CreateEvent({ token, onDone }: { token: string; onDone: (m: string) => void }) {
  const [f, setF] = useState({ title: "", slug: "", description: "", starts_at: "", visibility: "holder", prize_text: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/admin/events", { token, body: { ...f, starts_at: new Date(f.starts_at).toISOString(), prize_text: f.prize_text || null } });
      onDone(`Created ${f.title}.`);
      setF({ title: "", slug: "", description: "", starts_at: "", visibility: "holder", prize_text: "" });
    } catch (err) {
      onDone(err instanceof Error ? err.message : "Couldn't create the event");
    }
  }

  return (
    <section>
      <h2 className="text-[56px]">Create an event</h2>
      <form onSubmit={submit} className="card mt-5 space-y-3 p-6">
        <input required className="field" placeholder="Title" value={f.title} onChange={set("title")} aria-label="Title" />
        <input required pattern="[a-z0-9-]{3,80}" className="field" placeholder="url-slug" value={f.slug} onChange={set("slug")} aria-label="URL slug" />
        <textarea className="field" rows={3} placeholder="What happens at this event" value={f.description} onChange={set("description")} aria-label="Description" />
        <input required type="datetime-local" className="field" value={f.starts_at} onChange={set("starts_at")} aria-label="Starts at" />
        <select className="field" value={f.visibility} onChange={set("visibility")} aria-label="Who can join">
          <option value="holder">Chog holders only</option>
          <option value="public">Everyone</option>
        </select>
        <input className="field" placeholder="Prize (optional)" value={f.prize_text} onChange={set("prize_text")} aria-label="Prize" />
        <button className="btn-primary">Create event</button>
      </form>
    </section>
  );
}

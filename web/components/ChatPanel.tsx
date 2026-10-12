"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ActionCard, ChatMsg } from "@/lib/types";
import { ConfirmTxCard } from "./ConfirmTxCard";

const SUGGESTIONS = ["What can I do today?", "Which quests are open?", "How much CHOG do I own?", "Buy me 10 CHOG"];

export function ChatPanel({ tokenId, onChange }: { tokenId: number; onChange?: () => void }) {
  const { token } = useSession();
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    setMsgs([]);
    api<{ message: string }>(`/agent/greeting?token_id=${tokenId}`, { token })
      .then((g) => setMsgs([{ role: "assistant", content: g.message }]))
      .catch((e) => setMsgs([{ role: "assistant", content: e.message }]));
  }, [tokenId, token]);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

  async function send(text: string) {
    const t = text.trim();
    if (!t || busy) return;
    const next: ChatMsg[] = [...msgs, { role: "user", content: t }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api<{ reply: string; actions: ActionCard[]; tools_used: string[] }>("/agent/chat", {
        token,
        body: { token_id: tokenId, messages: next.slice(-20).map(({ role, content }) => ({ role, content })) },
      });
      setMsgs([...next, { role: "assistant", content: r.reply, actions: r.actions }]);
      if (r.tools_used.some((n) => !n.startsWith("get_") && !n.startsWith("list_"))) onChange?.();
    } catch (e) {
      setMsgs([...next, { role: "assistant", content: e instanceof Error ? e.message : "I couldn't reach the hub." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label={`Chat with Chog #${tokenId}`} className="flex h-full flex-col">
      <h2 className="mb-3 mt-2 text-[32px]">Chog says</h2>

      <div ref={scroller} className="-mx-2 flex max-h-[min(62vh,620px)] flex-col gap-3.5 overflow-y-auto px-2 pb-3 pt-7 [mask-image:linear-gradient(to_bottom,transparent,black_28px)]" aria-live="polite">
        {msgs.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="max-w-[88%] self-end rounded-[22px] rounded-br-[4px] border-3 border-ink bg-grape px-4 py-3 font-semibold text-white">
              {m.content}
            </div>
          ) : (
            <div key={i} className="flex max-w-full flex-col gap-3 self-start">
              <div className="max-w-[88%] whitespace-pre-line rounded-[22px] rounded-bl-[4px] border-3 border-ink bg-white px-4 py-3 font-semibold shadow-hard">
                {rich(m.content)}
              </div>
              {m.actions?.map((a) => <ConfirmTxCard key={a.id} action={a} onDone={() => onChange?.()} />)}
            </div>
          ),
        )}
        {busy && (
          <div className="self-start rounded-[22px] rounded-bl-[4px] border-3 border-ink bg-white px-4 py-3 font-semibold text-ink-soft">
            Chog is thinking…
          </div>
        )}
      </div>

      {msgs.length <= 1 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="rounded-full border-3 border-ink bg-white px-3.5 py-1.5 text-[15px] font-bold hover:bg-bubble-light"
              onClick={() => send(s)}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          Message your Chog
        </label>
        <input
          id="chat-input"
          className="field rounded-full"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell your Chog what to do"
          autoComplete="off"
        />
        <button className="btn bg-hot px-5 text-ink" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}

// Claude replies use light Markdown: **bold** and *actions*. Render those instead of showing the asterisks.
function rich(text: string) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return <strong key={i} className="font-extrabold">{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}

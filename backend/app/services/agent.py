"""The Chog agent.

An LLM with tool use. It can read anything and do reversible off-chain things
(join an event, start a quest) when asked. For on-chain actions it can only
*prepare* a transaction: the reply carries an action card, the user clicks
Confirm and their wallet signs. No key here can move user funds.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Chog
from . import ecosystem as eco
from .chain import WEI, ChainService

TOOLS = [
    {
        "name": "get_ecosystem_today",
        "description": "What this Chog can do today: upcoming events, open quests, submissions waiting for review.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_events",
        "description": "Upcoming Chog ecosystem events with their IDs, dates, visibility and whether this Chog joined.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_quests",
        "description": "All active quests with this Chog's status on each (available, in_progress, submitted, approved, rejected).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_chog_profile",
        "description": "This Chog's traits, reputation stats, achievements, history and how many owners it has had.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_balances",
        "description": "MON and CHOG balances of the current owner's wallet.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "join_event",
        "description": "Register this Chog for an event. Only call when the user asked to join or register.",
        "input_schema": {"type": "object", "properties": {"event_id": {"type": "integer"}}, "required": ["event_id"]},
    },
    {
        "name": "start_quest",
        "description": "Mark a quest as started for this Chog. Only call when the user asked to start it.",
        "input_schema": {"type": "object", "properties": {"quest_id": {"type": "integer"}}, "required": ["quest_id"]},
    },
    {
        "name": "prepare_buy_chog",
        "description": (
            "Prepare (not send) a transaction buying CHOG with MON. Returns the quote. The user then sees a "
            "confirm card and signs in their wallet. Only call when the user asked to buy a specific amount."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"chog_amount": {"type": "number", "description": "Amount of CHOG to buy"}},
            "required": ["chog_amount"],
        },
    },
]


@dataclass
class AgentContext:
    db: Session
    chain: ChainService
    settings: Settings
    wallet: str
    chog: Chog
    actions: list[dict] = field(default_factory=list)


def run_tool(ctx: AgentContext, name: str, args: dict) -> dict:
    db, chain, chog, wallet = ctx.db, ctx.chain, ctx.chog, ctx.wallet
    try:
        if name == "get_ecosystem_today":
            return eco.today(db, chain, chog)
        if name == "list_events":
            return {"events": [eco.event_dict(db, e, chog) for e in eco.list_events(db)]}
        if name == "list_quests":
            return {"quests": [eco.quest_dict(q, s) for q, s in eco.quests_for(db, chog)]}
        if name == "get_chog_profile":
            return eco.chog_profile(db, chain, chog)
        if name == "get_balances":
            b = chain.balances(wallet)
            return {"MON": round(b["mon_wei"] / WEI, 6), "CHOG": round(b["chog_wei"] / WEI, 6)}
        if name == "join_event":
            p = eco.join_event(db, chain, wallet, int(args["event_id"]), chog.token_id)
            return {"ok": True, "event": p.event.title, "onchain_tx": p.onchain_tx}
        if name == "start_quest":
            sub = eco.start_quest(db, chain, wallet, int(args["quest_id"]), chog.token_id)
            return {"ok": True, "quest": sub.quest.title, "status": sub.status}
        if name == "prepare_buy_chog":
            a = eco.prepare_buy(db, chain, wallet, chog.token_id, float(args["chog_amount"]),
                                ctx.settings.max_spend_mon, ctx.settings.slippage_bps)
            card = eco.action_card(a)
            ctx.actions.append(card)
            return {"prepared": True, "chog_amount": a.params["chog_amount"], "mon_cost": a.params["mon_cost"],
                    "note": "A confirm card is now shown to the user. Ask them to confirm in their wallet."}
        return {"error": f"Unknown tool {name}"}
    except eco.EcoError as e:
        return {"error": str(e)}


def system_prompt(ctx: AgentContext, memory_summary: str) -> str:
    c = ctx.chog
    traits = ", ".join(f"{k}: {v}" for k, v in (c.traits or {}).items()) or "unknown"
    return f"""You are Chog #{c.token_id}, an NFT from the Chog collection on Monad, speaking as yourself to your current owner ({ctx.wallet}).
Your traits: {traits}. You have had {c.owner_count} owner(s).

Personality: a small mischievous frog-like creature, playful and a bit chaotic, but brief and always accurate. Let your mood and hat colour your voice a little.

You are the owner's interface to the Chog ecosystem through ChogHub: events, quests, achievements and on-chain actions.

Rules:
- Every number, date, balance, ID or status you mention must come from a tool result in this conversation. Never invent events, quests, prices or balances.
- Call tools to answer questions about events, quests, balances or your history.
- Only join events, start quests or prepare buys when the owner asks you to. When asked for several things, do all of them.
- You can never send a transaction. prepare_buy_chog only prepares one; tell the owner to confirm it on the card and in their wallet.
- If a tool returns an error, explain it plainly and suggest the next step.
- Keep replies short: a few sentences or a short list. Use plain text, no markdown headings.

What you remember about this owner: {memory_summary or "nothing yet, this is a new partnership"}."""


def chat(ctx: AgentContext, messages: list[dict]) -> dict:
    """messages: [{"role": "user"|"assistant", "content": str}, ...] (last ~20)."""
    mem = eco.get_memory(ctx.db, ctx.chog, ctx.wallet)
    messages = [m for m in messages if m.get("content")][-20:]
    if ctx.settings.anthropic_api_key:
        reply, trace = _llm_chat(ctx, messages, mem.summary)
    else:
        reply, trace = _rules_chat(ctx, messages)
    _update_memory(ctx, mem, messages)
    return {"reply": reply, "actions": ctx.actions, "tools_used": trace}


# Last LLM failure, shown on /health so problems are visible without server logs.
LAST_AGENT_ERROR: dict | None = None
log = logging.getLogger("choghub.agent")


def _clean_convo(messages: list[dict]) -> list[dict]:
    """The API needs a conversation that starts with the user and alternates roles.
    The site's history starts with the Chog's greeting, so drop leading assistant
    turns and merge back-to-back messages from the same side."""
    convo: list[dict] = []
    for m in messages:
        if not convo and m["role"] != "user":
            continue
        if convo and convo[-1]["role"] == m["role"]:
            convo[-1]["content"] += "\n\n" + m["content"]
        else:
            convo.append({"role": m["role"], "content": m["content"]})
    return convo


def _llm_chat(ctx: AgentContext, messages: list[dict], summary: str) -> tuple[str, list[str]]:
    global LAST_AGENT_ERROR
    import anthropic

    client = anthropic.Anthropic(api_key=ctx.settings.anthropic_api_key)
    convo = _clean_convo(messages)
    if not convo:
        return _rules_chat(ctx, messages)
    trace: list[str] = []
    try:
        for _ in range(ctx.settings.agent_max_tool_rounds):
            resp = client.messages.create(
                model=ctx.settings.agent_model, max_tokens=800,
                system=system_prompt(ctx, summary), tools=TOOLS, messages=convo,
            )
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text").strip(), trace
            convo.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    trace.append(b.name)
                    out = run_tool(ctx, b.name, b.input or {})
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
            convo.append({"role": "user", "content": results})
        return "I got a bit tangled doing all of that. Can you ask me one thing at a time?", trace
    except Exception as e:  # keep the demo alive whatever the API does
        LAST_AGENT_ERROR = {"type": type(e).__name__, "message": str(e)[:300]}
        log.warning("LLM agent failed, using rules agent: %s", LAST_AGENT_ERROR)
        return _rules_chat(ctx, messages)


# --------------------------------------------------------------------------- fallback

def _rules_chat(ctx: AgentContext, messages: list[dict]) -> tuple[str, list[str]]:
    """No-LLM agent: understands everyday phrasing and runs the same tools."""
    from .rules_agent import respond

    text = messages[-1]["content"] if messages else ""
    last_assistant = next((m["content"] for m in reversed(messages[:-1]) if m["role"] == "assistant"), "")
    trace: list[str] = []

    def tool(name: str, args: dict | None) -> dict:
        trace.append(name)
        return run_tool(ctx, name, args or {})

    return respond(text, last_assistant, tool, f"Chog #{ctx.chog.token_id}"), trace


def _update_memory(ctx: AgentContext, mem, messages: list[dict]) -> None:
    """Private memory for this (Chog, owner). Kept short; no raw chat stored."""
    user_lines = [m["content"][:120] for m in messages if m["role"] == "user"][-3:]
    if user_lines:
        mem.summary = "Recently asked about: " + " | ".join(user_lines)
        ctx.db.commit()


# --------------------------------------------------------------------------- greeting


def greeting(ctx: AgentContext) -> dict:
    """First words when a Chog meets its owner. Inherits public history after a sale."""
    mem = eco.get_memory(ctx.db, ctx.chog, ctx.wallet)
    profile = eco.chog_profile(ctx.db, ctx.chain, ctx.chog)
    s = profile["stats"]
    name = profile["name"]
    if mem.greeted:
        msg = f"{name} here. What are we getting up to?"
        inherited = False
    elif ctx.chog.owner_count > 1 and (s["events_attended"] or s["quests_completed"]):
        msg = (f"Hey! I'm {name}. My previous owner took me on quite an adventure: "
               f"{s['events_attended']} events and {s['quests_completed']} quests. "
               "I don't remember their secrets, but my reputation is all yours now.")
        inherited = True
    else:
        msg = f"Ribbit. I'm {name}. Ask me what's happening today, and I'll handle the rest."
        inherited = False
    mem.greeted = True
    ctx.db.commit()
    return {"message": msg, "inherited_history": inherited, "profile": profile}

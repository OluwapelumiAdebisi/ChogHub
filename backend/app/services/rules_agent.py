"""The no-LLM Chog: understands everyday phrasing well enough to run the whole demo.

Used when ANTHROPIC_API_KEY is unset or the API fails. It reads the message,
splits it into clauses ("register me for the call and start the meme quest"),
works out what each clause asks for, runs the same tools the LLM agent uses,
and answers in a Chog voice. Every number it says comes from a tool result.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

WORD_NUMS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "fifty": 50, "hundred": 100, "a hundred": 100,
    "thousand": 1000, "a thousand": 1000,
}
STOP = {
    "the", "a", "an", "me", "my", "for", "to", "of", "in", "on", "and", "please", "can", "you", "i", "want",
    "join", "register", "sign", "up", "start", "begin", "do", "event", "events", "quest", "quests", "into",
    "with", "chog", "is", "it", "this", "that", "next", "would", "like", "could", "let", "lets", "us", "go",
}


def _num(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k)?\b", text)
    if m:
        n = float(m.group(1))
        return n * 1000 if m.group(2) else n
    for w in sorted(WORD_NUMS, key=len, reverse=True):
        if re.search(rf"\b{w}\b", text) and w not in ("a", "an"):
            return float(WORD_NUMS[w])
    return None


def _when(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%a %-d %b, %H:%M UTC")
    except ValueError:
        return iso


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t) > 1}


def _best(items: list[dict], clause: str, fields: tuple[str, ...]) -> dict | None:
    """Pick the item whose title/slug shares the most words with the clause, or by #id."""
    m = re.search(r"#\s*(\d+)|\b(?:event|quest)\s+(\d+)\b", clause)
    if m:
        wanted = int(m.group(1) or m.group(2))
        for it in items:
            if it["id"] == wanted:
                return it
    words = _tokens(clause)
    # common nicknames
    if "call" in words or "spaces" in words:
        words |= {"community", "call"}
    if "pirate" in words or "treasure" in words:
        words |= {"pirate", "treasure", "hunt"}
    scored = []
    for it in items:
        name = " ".join(str(it.get(f, "")) for f in fields).replace("-", " ")
        score = len(words & _tokens(name))
        if score:
            scored.append((score, it))
    if not scored:
        return None
    scored.sort(key=lambda s: -s[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None  # ambiguous
    return scored[0][1]


INTENTS: list[tuple[str, re.Pattern]] = [
    ("buy", re.compile(r"\b(buy|purchase|get me|grab|swap .* for|acquire)\b")),
    ("join", re.compile(r"\b(join|register|sign me up|sign up|rsvp|attend|enter|count me in)\b")),
    ("start", re.compile(r"\b(start|begin|take on|accept|do the|try the)\b.*\bquest\b|\b(start|begin)\b")),
    ("balance", re.compile(r"\b(balance|how much .*(own|have|hold)|wallet|my (chog|mon) tokens?|how many chog)\b")),
    ("badges", re.compile(r"\b(badge|badges|achievement|achievements|sticker|reputation|stats|history|story)\b")),
    ("whoami", re.compile(r"\b(who are you|about you|your name|your traits|tell me about yourself|what are you|traits)\b")),
    ("help", re.compile(r"\b(help|what can you do|how does this work|commands|what do you do)\b")),
    ("today", re.compile(r"\b(today|happening|what can i do|what'?s on|what'?s new|anything to do|up to)\b")),
    ("events", re.compile(r"\b(events?|schedule|calendar|when is|meetup|spaces|competition)\b")),
    ("quests", re.compile(r"\b(quests?|missions?|tasks?|challenges?)\b")),
    ("greet", re.compile(r"^\s*(hi|hey|hello|yo|gm|good (morning|afternoon|evening)|sup|wassup|ribbit)\b")),
    ("thanks", re.compile(r"\b(thanks|thank you|ty|cheers|nice|great|awesome|cool)\b")),
]


def detect(clause: str) -> list[str]:
    found = [name for name, rx in INTENTS if rx.search(clause)]
    # "start the buy quest" is about a quest, not a purchase.
    if "start" in found and re.search(r"\bquest\b", clause):
        return ["start"]
    # "buy" beats a stray "quest"/"events" in the same clause; "join" beats "events".
    if "buy" in found:
        return ["buy"]
    if "join" in found:
        return ["join"]
    if "start" in found and "quests" in found:
        return ["start"]
    if "start" in found and not re.search(r"\bquest|meme|pirate|hunt|treasure\b", clause):
        found.remove("start")
    return found


def split_clauses(text: str) -> list[str]:
    parts = re.split(r"\s*(?:,|;|\band then\b|\bthen\b|\band also\b|\balso\b|\band\b)\s*", text)
    return [p for p in (s.strip() for s in parts) if p]


def respond(text: str, last_assistant: str, tool: Callable[[str, dict | None], dict], chog_name: str) -> str:
    t = text.lower().strip()

    # Follow-up to "How much CHOG should I buy?"
    if "how much chog" in last_assistant.lower() and _num(t) is not None and not re.search(r"[a-z]{4,}", re.sub(r"chog|mon|tokens?|please|buy", "", t)):
        return _buy(_num(t), tool)

    clauses = split_clauses(t) if len(t) > 25 else [t]
    replies: list[str] = []
    done: set[str] = set()
    for clause in clauses:
        for intent in detect(clause):
            key = intent if intent in ("join", "start", "buy") else intent  # actions may repeat per clause
            if intent not in ("join", "start", "buy") and key in done:
                continue
            done.add(key)
            replies.append(HANDLERS[intent](clause, tool, chog_name))
    if not replies:
        # single-clause fallback: maybe the whole thing names an event or quest
        return (
            f"Ribbit? I didn't quite get that. Try things like:\n"
            "- What's happening today?\n- Register me for Chog Meme Wars\n- Start the meme quest\n"
            "- Buy me 10 CHOG\n- How much CHOG do I own?\n- Show my badges"
        )
    return "\n\n".join(r for r in replies if r)


# --------------------------------------------------------------------------- handlers


def _buy(amount: float | None, tool) -> str:
    if amount is None or amount <= 0:
        return "Happy to grab you some CHOG. How much CHOG should I buy? Say a number, like 10 or 250."
    out = tool("prepare_buy_chog", {"chog_amount": amount})
    if "error" in out:
        return f"Can't do that one: {out['error']}"
    return (f"Ready! {out['chog_amount']:g} CHOG will cost about {out['mon_cost']:.4f} MON. "
            "Hit Confirm on the card and sign in your wallet. I never send anything without you.")


def h_buy(clause, tool, _):
    return _buy(_num(clause), tool)


def h_join(clause, tool, _):
    events = tool("list_events", None)["events"]
    if not events:
        return "There are no upcoming events to join right now."
    ev = _best(events, clause, ("title", "slug"))
    if ev is None:
        names = "\n".join(f"- {e['title']} ({_when(e['starts_at'])})" for e in events)
        return f"Which one? Here's what's coming up:\n{names}"
    if ev.get("joined"):
        return f"You're already in {ev['title']}. See you there!"
    out = tool("join_event", {"event_id": ev["id"]})
    if "error" in out:
        return f"Couldn't join {ev['title']}: {out['error']}"
    extra = " Attendance is recorded on Monad against me." if out.get("onchain_tx") else ""
    return f"Done, you're in {out['event']} ({_when(ev['starts_at'])}).{extra}"


def h_start(clause, tool, _):
    quests = tool("list_quests", None)["quests"]
    q = _best(quests, clause, ("title", "slug"))
    if q is None:
        open_q = [x for x in quests if x["status"] in ("available", "in_progress", "rejected")]
        if not open_q:
            return "You've finished every quest. New ones land here first."
        return "Which quest? Open ones:\n" + "\n".join(f"- {x['title']}" for x in open_q)
    if q["status"] == "approved":
        return f"Already done: {q['title']}. That badge is stuck to me for good."
    if q["status"] == "submitted":
        return f"{q['title']} is in review. The badge lands as soon as it's approved."
    if q["verify_type"] == "auto_buy":
        return f"{q['title']} completes the moment you buy CHOG. Just say \"buy me 10 CHOG\"."
    if q["verify_type"] == "auto_event":
        return f"{q['title']} completes when you join its event. Say \"register me for the community call\"."
    out = tool("start_quest", {"quest_id": q["id"]})
    if "error" in out:
        return f"Couldn't start {q['title']}: {out['error']}"
    return f"Quest started: {q['title']}. When you're done, drop your proof link on the Quests page."


def h_balance(_c, tool, _):
    b = tool("get_balances", None)
    return f"Your wallet holds {b['MON']:g} MON and {b['CHOG']:g} CHOG."


def h_badges(_c, tool, name):
    p = tool("get_chog_profile", None)
    s = p["stats"]
    badges = ", ".join(a["name"] for a in p["achievements"]) or "none yet"
    owners = f" I've had {p['owner_count']} owners." if p["owner_count"] > 1 else ""
    def n(x, word):
        return f"{x} {word}" + ("" if x == 1 else "s")
    return (f"{name}'s record: {n(s['quests_completed'], 'quest')}, {n(s['events_attended'], 'event')}. "
            f"Badges: {badges}.{owners}")


def h_whoami(_c, tool, name):
    p = tool("get_chog_profile", None)
    traits = ", ".join(f"{k} {v}" for k, v in p["traits"].items())
    return (f"I'm {name}, your Chog on Monad ({traits}). I find events, run quests and prepare CHOG buys "
            "for you to sign. Everything I earn sticks to me, even if I change hands.")


def h_help(_c, _t, _n):
    return ("I can:\n- Tell you what's happening today\n- List events and register you\n"
            "- Start quests and track badges\n- Check your MON and CHOG balance\n"
            "- Prepare a CHOG buy for you to confirm\nTry \"register me for Meme Wars and start the meme quest\".")


def h_today(_c, tool, _):
    d = tool("get_ecosystem_today", None)
    lines = [f"- Event: {e['title']}, {_when(e['starts_at'])}" + (" (you're in)" if e["joined"] else "")
             for e in d["events"][:3]]
    lines += [f"- Quest: {q['title']}" for q in d["open_quests"][:3]]
    if d["waiting_review"]:
        lines.append(f"- In review: {', '.join(q['title'] for q in d['waiting_review'])}")
    if not lines:
        return "Quiet day in Chog land. Nothing open right now."
    return "Here's what's on:\n" + "\n".join(lines)


def h_events(_c, tool, _):
    es = tool("list_events", None)["events"]
    if not es:
        return "No upcoming events right now."
    return "Upcoming events:\n" + "\n".join(
        f"- {e['title']}, {_when(e['starts_at'])}" + (" (holders only)" if e["visibility"] == "holder" else "")
        + (" (you're in)" if e["joined"] else "") for e in es)


def h_quests(_c, tool, _):
    qs = tool("list_quests", None)["quests"]
    label = {"available": "open", "in_progress": "started", "submitted": "in review", "approved": "done", "rejected": "try again"}
    return "Quests:\n" + "\n".join(f"- {q['title']} ({label[q['status']]}), earns {q['achievement']['name']}" for q in qs)


def h_greet(_c, _t, name):
    return f"Gm! {name} reporting for duty. Ask what's happening today, or tell me to do something."


def h_thanks(_c, _t, _n):
    return "Anytime. Ribbit."


HANDLERS = {
    "buy": h_buy, "join": h_join, "start": h_start, "balance": h_balance, "badges": h_badges,
    "whoami": h_whoami, "help": h_help, "today": h_today, "events": h_events, "quests": h_quests,
    "greet": h_greet, "thanks": h_thanks,
}

"""Chogs, events, quests and achievements. Used by both the HTTP routers and the
agent's tools, so a Join button and "register me for the call" run the same checks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AgentMemory,
    Chog,
    Event,
    EventParticipation,
    PendingAction,
    Quest,
    QuestSubmission,
    utcnow,
)
from .chain import WEI, ChainService


class EcoError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------- chogs


def sync_chog(db: Session, chain: ChainService, token_id: int) -> Chog:
    """Upsert a Chog from chain state. Detects owner changes (a sale)."""
    chog = db.scalar(select(Chog).where(Chog.collection == chain.collection.lower(), Chog.token_id == token_id))
    owner = chain.owner_of(token_id)
    if owner is None:
        raise EcoError(f"Chog #{token_id} does not exist", 404)
    if chog is None:
        chog = Chog(collection=chain.collection.lower(), token_id=token_id, current_owner=owner, owner_count=1,
                    traits=chain.traits_of(token_id))
        db.add(chog)
    elif chog.current_owner != owner:
        chog.current_owner = owner
        chog.owner_count += 1
    chog.last_synced = utcnow()
    db.commit()
    return chog


def require_holder(db: Session, chain: ChainService, wallet: str, token_id: int) -> Chog:
    chog = sync_chog(db, chain, token_id)
    if chog.current_owner != wallet.lower():
        raise EcoError(f"Your wallet does not hold Chog #{token_id}", 403)
    return chog


def chog_profile(db: Session, chain: ChainService, chog: Chog) -> dict:
    events = db.scalars(
        select(EventParticipation).where(EventParticipation.chog_id == chog.id).order_by(EventParticipation.joined_at)
    ).all()
    subs = db.scalars(
        select(QuestSubmission).where(QuestSubmission.chog_id == chog.id, QuestSubmission.status == "approved")
    ).all()
    achievements = [
        {"slug": s.quest.achievement.slug, "name": s.quest.achievement.name, "icon": s.quest.achievement.icon,
         "earned_at": s.updated_at.isoformat(), "tx": s.onchain_tx}
        for s in subs
    ]
    history = [{"type": "event", "title": p.event.title, "at": p.joined_at.isoformat()} for p in events] + [
        {"type": "achievement", "title": a["name"], "at": a["earned_at"]} for a in achievements
    ]
    history.sort(key=lambda h: h["at"], reverse=True)
    return {
        "token_id": chog.token_id,
        "collection": chog.collection,
        "name": f"Chog #{chog.token_id}",
        "owner": chog.current_owner,
        "owner_count": chog.owner_count,
        "traits": chog.traits,
        "image": chain.image_of(chog.token_id),
        "stats": {
            "quests_completed": len(subs),
            "events_attended": len(events),
            "achievements": len(achievements),
            "onchain": _safe(lambda: chain.registry_stats(chog.token_id), {}),
        },
        "achievements": achievements,
        "history": history[:30],
    }


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


# --------------------------------------------------------------------------- events


def event_dict(db: Session, e: Event, chog: Chog | None = None) -> dict:
    count = db.scalar(select(func.count()).select_from(EventParticipation).where(EventParticipation.event_id == e.id))
    joined = bool(chog) and db.scalar(
        select(EventParticipation.id).where(EventParticipation.event_id == e.id, EventParticipation.chog_id == chog.id)
    ) is not None
    return {
        "id": e.id, "slug": e.slug, "title": e.title, "description": e.description,
        "starts_at": e.starts_at.isoformat(), "ends_at": e.ends_at.isoformat() if e.ends_at else None,
        "kind": e.kind, "visibility": e.visibility, "official": e.official, "capacity": e.capacity,
        "participants": count, "prize": e.prize_text, "link": e.link, "joined": joined,
    }


def list_events(db: Session, upcoming_only: bool = True) -> list[Event]:
    q = select(Event).order_by(Event.starts_at)
    if upcoming_only:
        cutoff = utcnow() - timedelta(hours=6)
        q = q.where((Event.ends_at.is_(None) & (Event.starts_at >= cutoff)) | (Event.ends_at >= utcnow()))
    return list(db.scalars(q))


def join_event(db: Session, chain: ChainService, wallet: str, event_id: int, token_id: int) -> EventParticipation:
    chog = require_holder(db, chain, wallet, token_id)
    e = db.get(Event, event_id)
    if not e:
        raise EcoError("Event not found", 404)
    existing = db.scalar(
        select(EventParticipation).where(EventParticipation.event_id == e.id, EventParticipation.chog_id == chog.id)
    )
    if existing:
        return existing
    if e.capacity:
        n = db.scalar(select(func.count()).select_from(EventParticipation).where(EventParticipation.event_id == e.id))
        if n >= e.capacity:
            raise EcoError("This event is full", 409)
    p = EventParticipation(event_id=e.id, chog_id=chog.id, wallet=wallet.lower())
    db.add(p)
    db.commit()
    # Attendance goes on-chain against the token.
    p.onchain_tx = _safe(lambda: chain.record_event(token_id, f"event:{e.slug}", p.id), None)
    db.commit()
    _auto_complete(db, chain, chog, wallet, verify_type="auto_event", event_id=e.id)
    return p


# --------------------------------------------------------------------------- quests


def quest_dict(q: Quest, sub: QuestSubmission | None = None) -> dict:
    return {
        "id": q.id, "slug": q.slug, "title": q.title, "description": q.description,
        "verify_type": q.verify_type, "event_id": q.event_id, "trait_requirement": q.trait_requirement,
        "achievement": {"slug": q.achievement.slug, "name": q.achievement.name, "icon": q.achievement.icon},
        "status": sub.status if sub else "available",
    }


def quests_for(db: Session, chog: Chog | None) -> list[tuple[Quest, QuestSubmission | None]]:
    quests = db.scalars(select(Quest).where(Quest.active.is_(True)).order_by(Quest.id)).all()
    subs = {}
    if chog:
        subs = {s.quest_id: s for s in db.scalars(select(QuestSubmission).where(QuestSubmission.chog_id == chog.id))}
    return [(q, subs.get(q.id)) for q in quests]


def _check_traits(q: Quest, chog: Chog) -> None:
    for k, v in (q.trait_requirement or {}).items():
        if (chog.traits or {}).get(k) != v:
            raise EcoError(f"This quest needs a Chog with {k}: {v}", 403)


def _get_or_create_sub(db: Session, q: Quest, chog: Chog, wallet: str) -> QuestSubmission:
    sub = db.scalar(select(QuestSubmission).where(QuestSubmission.quest_id == q.id, QuestSubmission.chog_id == chog.id))
    if not sub:
        sub = QuestSubmission(quest_id=q.id, chog_id=chog.id, wallet=wallet.lower())
        db.add(sub)
    return sub


def start_quest(db: Session, chain: ChainService, wallet: str, quest_id: int, token_id: int) -> QuestSubmission:
    chog = require_holder(db, chain, wallet, token_id)
    q = db.get(Quest, quest_id)
    if not q or not q.active:
        raise EcoError("Quest not found", 404)
    _check_traits(q, chog)
    sub = _get_or_create_sub(db, q, chog, wallet)
    db.commit()
    return sub


def submit_quest(db: Session, chain: ChainService, wallet: str, quest_id: int, token_id: int,
                 proof_text: str | None, proof_url: str | None) -> QuestSubmission:
    chog = require_holder(db, chain, wallet, token_id)
    q = db.get(Quest, quest_id)
    if not q or not q.active:
        raise EcoError("Quest not found", 404)
    _check_traits(q, chog)
    if q.verify_type != "manual":
        raise EcoError("This quest completes automatically when you do it")
    sub = _get_or_create_sub(db, q, chog, wallet)
    if sub.status == "approved":
        raise EcoError("Already completed", 409)
    if not (proof_text or proof_url):
        raise EcoError("Add a link or a description as proof")
    sub.proof_text, sub.proof_url, sub.status = proof_text, proof_url, "submitted"
    db.commit()
    return sub


def approve(db: Session, chain: ChainService, sub: QuestSubmission, reviewer: str | None) -> QuestSubmission:
    if sub.status == "approved":
        return sub
    sub.status = "approved"
    sub.reviewed_by = reviewer
    db.commit()
    chog = db.get(Chog, sub.chog_id)
    a = sub.quest.achievement
    sub.onchain_tx = _safe(lambda: chain.record_achievement(chog.token_id, a.slug, a.kind, sub.id), None)
    db.commit()
    return sub


def reject(db: Session, sub: QuestSubmission, reviewer: str) -> QuestSubmission:
    sub.status = "rejected"
    sub.reviewed_by = reviewer
    db.commit()
    return sub


def _auto_complete(db: Session, chain: ChainService, chog: Chog, wallet: str, verify_type: str,
                   event_id: int | None = None) -> list[QuestSubmission]:
    q = select(Quest).where(Quest.active.is_(True), Quest.verify_type == verify_type)
    if event_id is not None:
        q = q.where(Quest.event_id == event_id)
    done = []
    for quest in db.scalars(q):
        try:
            _check_traits(quest, chog)
        except EcoError:
            continue
        sub = _get_or_create_sub(db, quest, chog, wallet)
        db.commit()
        done.append(approve(db, chain, sub, reviewer="auto"))
    return done


# --------------------------------------------------------------------------- buy CHOG


def prepare_buy(db: Session, chain: ChainService, wallet: str, token_id: int, chog_amount: float,
                max_spend_mon: float, slippage_bps: int) -> PendingAction:
    chog = require_holder(db, chain, wallet, token_id)
    if chog_amount <= 0:
        raise EcoError("Amount must be positive")
    chog_wei = int(chog_amount * WEI)
    cost = chain.quote_mon_for_chog(chog_wei)
    if cost > int(max_spend_mon * WEI):
        raise EcoError(f"That would cost {cost / WEI:.4f} MON, above the {max_spend_mon} MON limit per action")
    min_out = chog_wei * (10_000 - slippage_bps) // 10_000
    tx = chain.build_buy_tx(wallet, chog_wei, min_out, cost)
    action = PendingAction(
        chog_id=chog.id, wallet=wallet.lower(), kind="buy_chog",
        params={"chog_amount": chog_amount, "mon_cost": cost / WEI, "min_out": min_out / WEI},
        unsigned_tx=tx, expires_at=utcnow() + timedelta(minutes=10),
    )
    db.add(action)
    db.commit()
    return action


def action_card(a: PendingAction) -> dict:
    return {"id": a.id, "kind": a.kind, "status": a.status, "params": a.params, "tx": a.unsigned_tx,
            "tx_hash": a.tx_hash, "result": a.result, "expires_at": a.expires_at.isoformat()}


def confirm_action(db: Session, chain: ChainService, wallet: str, action_id: int, tx_hash: str) -> PendingAction:
    a = db.get(PendingAction, action_id)
    if not a or a.wallet != wallet.lower():
        raise EcoError("Action not found", 404)
    if a.status == "confirmed":
        return a
    if a.status != "prepared":
        raise EcoError(f"Action is {a.status}", 409)
    if datetime.now(timezone.utc).replace(tzinfo=None) > a.expires_at:
        a.status = "expired"
        db.commit()
        raise EcoError("This action expired; ask your Chog to prepare it again", 410)
    a.tx_hash, a.status = tx_hash, "sent"
    db.commit()
    res = chain.verify_buy(tx_hash, wallet)
    if not res:
        a.status = "failed"
        db.commit()
        raise EcoError("Could not verify that transaction as a CHOG buy from your wallet", 422)
    a.status = "confirmed"
    a.result = {"chog_received": res.chog_out_wei / WEI, "mon_spent": res.mon_in_wei / WEI}
    db.commit()
    chog = db.get(Chog, a.chog_id)
    _auto_complete(db, chain, chog, wallet, verify_type="auto_buy")
    return a


# --------------------------------------------------------------------------- today


def today(db: Session, chain: ChainService, chog: Chog | None) -> dict:
    events = [event_dict(db, e, chog) for e in list_events(db)[:5]]
    quests = [quest_dict(q, s) for q, s in quests_for(db, chog)]
    open_quests = [q for q in quests if q["status"] in ("available", "in_progress")]
    return {"events": events, "open_quests": open_quests,
            "waiting_review": [q for q in quests if q["status"] == "submitted"]}


def get_memory(db: Session, chog: Chog, wallet: str) -> AgentMemory:
    mem = db.scalar(select(AgentMemory).where(AgentMemory.chog_id == chog.id, AgentMemory.owner_wallet == wallet.lower()))
    if not mem:
        mem = AgentMemory(chog_id=chog.id, owner_wallet=wallet.lower())
        db.add(mem)
        db.commit()
    return mem

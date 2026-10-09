"""Chogs, events, quests, agent and actions."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import chain_dep, current_wallet, optional_wallet
from ..models import Event, Quest
from ..schemas import ChatIn, ConfirmIn, JoinIn, SubmitIn
from ..services import agent
from ..services import ecosystem as eco
from ..services.chain import ChainService

router = APIRouter(tags=["hub"])


def _http(e: eco.EcoError):
    return HTTPException(e.status, str(e))


@router.get("/config")
def public_config(s: Settings = Depends(get_settings)):
    return {
        "network": s.network, "chain_id": s.chain_id, "explorer": s.explorer, "chain_mode": s.chain_mode,
        "contracts": {"nft": s.chog_nft_address, "token": s.chog_token_address,
                      "vendor": s.chog_vendor_address, "registry": s.chog_registry_address},
    }


# --------------------------------------------------------------------------- chogs


@router.get("/me/chogs")
def my_chogs(token_ids: str | None = Query(default=None, description="Comma-separated IDs, for non-enumerable collections"),
             wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
             chain: ChainService = Depends(chain_dep)):
    ids = chain.tokens_of_owner(wallet)
    if token_ids:
        ids = sorted(set(ids) | {int(t) for t in token_ids.split(",") if t.strip().isdigit()})
    out = []
    for tid in ids:
        try:
            chog = eco.require_holder(db, chain, wallet, tid)
        except eco.EcoError:
            continue
        out.append({"token_id": chog.token_id, "name": f"Chog #{chog.token_id}", "traits": chog.traits,
                    "image": chain.image_of(chog.token_id)})
    return {"wallet": wallet, "chogs": out}


@router.get("/chogs/{token_id}")
def chog(token_id: int, db: Session = Depends(get_db), chain: ChainService = Depends(chain_dep)):
    try:
        c = eco.sync_chog(db, chain, token_id)
    except eco.EcoError as e:
        raise _http(e) from e
    return eco.chog_profile(db, chain, c)


# --------------------------------------------------------------------------- events


@router.get("/events")
def events(token_id: int | None = None, include_past: bool = False, db: Session = Depends(get_db),
           chain: ChainService = Depends(chain_dep)):
    c = _maybe_chog(db, chain, token_id)
    return {"events": [eco.event_dict(db, e, c) for e in eco.list_events(db, upcoming_only=not include_past)]}


@router.get("/events/{event_id}")
def event(event_id: int, token_id: int | None = None, db: Session = Depends(get_db),
          chain: ChainService = Depends(chain_dep)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(404, "Event not found")
    c = _maybe_chog(db, chain, token_id)
    quests = [eco.quest_dict(q, s) for q, s in eco.quests_for(db, c) if q.event_id == e.id]
    return {**eco.event_dict(db, e, c), "quests": quests}


@router.post("/events/{event_id}/join")
def join(event_id: int, body: JoinIn, wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
         chain: ChainService = Depends(chain_dep)):
    try:
        p = eco.join_event(db, chain, wallet, event_id, body.token_id)
    except eco.EcoError as e:
        raise _http(e) from e
    return {"joined": True, "event_id": p.event_id, "onchain_tx": p.onchain_tx}


# --------------------------------------------------------------------------- quests


@router.get("/quests")
def quests(token_id: int | None = None, db: Session = Depends(get_db), chain: ChainService = Depends(chain_dep)):
    c = _maybe_chog(db, chain, token_id)
    return {"quests": [eco.quest_dict(q, s) for q, s in eco.quests_for(db, c)]}


@router.get("/quests/{quest_id}")
def quest(quest_id: int, token_id: int | None = None, db: Session = Depends(get_db),
          chain: ChainService = Depends(chain_dep)):
    q = db.get(Quest, quest_id)
    if not q:
        raise HTTPException(404, "Quest not found")
    c = _maybe_chog(db, chain, token_id)
    sub = dict(eco.quests_for(db, c)).get(q) if c else None
    return eco.quest_dict(q, sub)


@router.post("/quests/{quest_id}/submit")
def submit(quest_id: int, body: SubmitIn, wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
           chain: ChainService = Depends(chain_dep)):
    try:
        sub = eco.submit_quest(db, chain, wallet, quest_id, body.token_id, body.proof_text, body.proof_url)
    except eco.EcoError as e:
        raise _http(e) from e
    return {"status": sub.status, "submission_id": sub.id}


# --------------------------------------------------------------------------- agent


def _ctx(db, chain, s, wallet, token_id) -> agent.AgentContext:
    try:
        c = eco.require_holder(db, chain, wallet, token_id)
    except eco.EcoError as e:
        raise _http(e) from e
    return agent.AgentContext(db=db, chain=chain, settings=s, wallet=wallet, chog=c)


@router.get("/agent/greeting")
def greet(token_id: int, wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
          chain: ChainService = Depends(chain_dep), s: Settings = Depends(get_settings)):
    return agent.greeting(_ctx(db, chain, s, wallet, token_id))


@router.post("/agent/chat")
def chat(body: ChatIn, wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
         chain: ChainService = Depends(chain_dep), s: Settings = Depends(get_settings)):
    ctx = _ctx(db, chain, s, wallet, body.token_id)
    return agent.chat(ctx, [m.model_dump() for m in body.messages])


# --------------------------------------------------------------------------- actions


@router.post("/actions/{action_id}/confirm")
def confirm(action_id: int, body: ConfirmIn, wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
            chain: ChainService = Depends(chain_dep)):
    try:
        a = eco.confirm_action(db, chain, wallet, action_id, body.tx_hash)
    except eco.EcoError as e:
        raise _http(e) from e
    return eco.action_card(a)


def _maybe_chog(db, chain, token_id):
    if token_id is None:
        return None
    try:
        return eco.sync_chog(db, chain, token_id)
    except eco.EcoError:
        return None

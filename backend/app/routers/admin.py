from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_wallet, chain_dep
from ..models import Achievement, Chog, Event, Quest, QuestSubmission
from ..schemas import EventIn, QuestIn, ReviewIn
from ..services import ecosystem as eco
from ..services.chain import ChainService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/events")
def create_event(body: EventIn, admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    if db.scalar(select(Event).where(Event.slug == body.slug)):
        raise HTTPException(409, "Slug already used")
    e = Event(**body.model_dump(), created_by=admin)
    db.add(e)
    db.commit()
    return eco.event_dict(db, e)


@router.post("/quests")
def create_quest(body: QuestIn, admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    if db.scalar(select(Quest).where(Quest.slug == body.slug)):
        raise HTTPException(409, "Slug already used")
    a = db.scalar(select(Achievement).where(Achievement.slug == body.achievement_slug))
    if not a:
        a = Achievement(slug=body.achievement_slug, name=body.achievement_name, icon=body.achievement_icon,
                        kind=body.achievement_kind)
        db.add(a)
        db.flush()
    q = Quest(slug=body.slug, title=body.title, description=body.description, verify_type=body.verify_type,
              event_id=body.event_id, trait_requirement=body.trait_requirement, achievement_id=a.id)
    db.add(q)
    db.commit()
    return eco.quest_dict(q)


@router.get("/submissions")
def submissions(status: str = "submitted", admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    rows = db.scalars(select(QuestSubmission).where(QuestSubmission.status == status).order_by(QuestSubmission.id)).all()
    out = []
    for s in rows:
        c = db.get(Chog, s.chog_id)
        out.append({"id": s.id, "quest": s.quest.title, "token_id": c.token_id, "wallet": s.wallet,
                    "proof_text": s.proof_text, "proof_url": s.proof_url, "status": s.status})
    return {"submissions": out}


@router.post("/submissions/{sub_id}/review")
def review(sub_id: int, body: ReviewIn, admin: str = Depends(admin_wallet), db: Session = Depends(get_db),
           chain: ChainService = Depends(chain_dep)):
    sub = db.get(QuestSubmission, sub_id)
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.status != "submitted":
        raise HTTPException(409, f"Submission is {sub.status}")
    sub = eco.approve(db, chain, sub, admin) if body.approve else eco.reject(db, sub, admin)
    return {"id": sub.id, "status": sub.status, "onchain_tx": sub.onchain_tx}

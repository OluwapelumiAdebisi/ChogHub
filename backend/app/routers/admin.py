from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_wallet, chain_dep
from ..models import Achievement, Chog, Event, Quest, QuestSubmission
from ..schemas import TRAIT_VALUES, EventIn, QuestActiveIn, QuestIn, ReviewIn
from ..services import ecosystem as eco
from ..services.chain import ChainService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/events")
def create_event(body: EventIn, admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    if db.scalar(select(Event).where(Event.slug == body.slug)):
        raise HTTPException(409, "An event with this name already exists. Pick a different title.")
    e = Event(**body.model_dump(), created_by=admin)
    db.add(e)
    db.commit()
    return eco.event_dict(db, e)


@router.get("/quests")
def all_quests(admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    """Every quest, paused ones included, with how many Chogs completed each."""
    out = []
    for q in db.scalars(select(Quest).order_by(Quest.id)):
        done = db.scalar(select(func.count()).select_from(QuestSubmission).where(
            QuestSubmission.quest_id == q.id, QuestSubmission.status == "approved"))
        out.append({**eco.quest_dict(q), "active": q.active, "completed": done,
                    "event_title": q.event.title if q.event_id else None})
    return {"quests": out}


@router.post("/quests")
def create_quest(body: QuestIn, admin: str = Depends(admin_wallet), db: Session = Depends(get_db)):
    if db.scalar(select(Quest).where(Quest.slug == body.slug)):
        raise HTTPException(409, "A quest with this name already exists. Pick a different title.")
    if body.verify_type == "auto_event" and not body.event_id:
        raise HTTPException(422, "Pick the event this quest completes with.")
    if body.event_id is not None and not db.get(Event, body.event_id):
        raise HTTPException(422, "That event doesn't exist.")
    for k, v in (body.trait_requirement or {}).items():
        if k not in TRAIT_VALUES or v not in TRAIT_VALUES[k]:
            raise HTTPException(422, f"Unknown trait: {k} {v}")
    a = db.scalar(select(Achievement).where(Achievement.slug == body.achievement_slug))
    if a and db.scalar(select(Quest).where(Quest.achievement_id == a.id)):
        # One badge per quest: the registry records each badge once per Chog, so a
        # shared badge would let one quest silently block the other.
        raise HTTPException(409, f"The badge \"{a.name}\" already belongs to another quest. Name the badge differently.")
    if not a:
        a = Achievement(slug=body.achievement_slug, name=body.achievement_name, icon=body.achievement_icon,
                        kind=body.achievement_kind)
        db.add(a)
        db.flush()
    q = Quest(slug=body.slug, title=body.title, description=body.description, verify_type=body.verify_type,
              event_id=body.event_id, trait_requirement=body.trait_requirement or None, achievement_id=a.id)
    db.add(q)
    db.commit()
    return eco.quest_dict(q)


@router.patch("/quests/{quest_id}")
def set_quest_active(quest_id: int, body: QuestActiveIn, admin: str = Depends(admin_wallet),
                     db: Session = Depends(get_db)):
    """Pause or resume a quest. Paused quests disappear for holders; earned badges stay."""
    q = db.get(Quest, quest_id)
    if not q:
        raise HTTPException(404, "Quest not found")
    q.active = body.active
    db.commit()
    return {"id": q.id, "active": q.active}


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
